"""Anonymous, write-only intake for a physically supervised Barangay kiosk."""

import logging
import re
from collections.abc import Mapping

from django.contrib.auth import authenticate
from django.db import transaction
from django.utils import timezone
from rest_framework import permissions, serializers, status
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from gridy_audit.models import AuditLog
from gridy_audit.services import log_action
from gridy_auth.models import Barangay, User
from gridy_auth.throttling import SharedDatabaseScopedRateThrottle
from gridy_communications.admin_notifications import notify_barangay_admins
from gridy_communications.models import AdminNotification
from gridy_reports.models import IssueReport
from gridy_services.models import (
    DocumentRequest,
    EquipmentBorrowRequest,
    MANILA_TIME_ZONE,
    QueueTicket,
)
from gridy_services.websocket_events import broadcast_queue_update


logger = logging.getLogger(__name__)

KIOSK_PRIVACY_NOTICE_VERSION = "kiosk-v1"
BORROWER_ID_TYPES = (
    "Barangay ID",
    "PhilSys National ID",
    "Voter's ID",
    "Driver's License",
    "Passport",
    "Senior Citizen / PWD ID",
    "Postal ID",
    "Other Government-Issued ID",
)
QUEUE_SERVICE_TYPES = (
    "Document Processing & Clearances",
    "Barangay ID Application",
    "Certificate of Indigency",
    "Equipment & Facility Borrowing",
    "General Inquiries & Complaints",
)


class KioskSubmissionSerializer(serializers.Serializer):
    barangay_id = serializers.IntegerField(min_value=1)
    privacy_acknowledged = serializers.BooleanField(write_only=True)

    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            unexpected = set(data) - set(self.fields)
            if unexpected:
                raise serializers.ValidationError({
                    "detail": "Unsupported fields: " + ", ".join(sorted(unexpected))
                })
        return super().to_internal_value(data)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if attrs.pop("privacy_acknowledged", False) is not True:
            raise serializers.ValidationError({
                "privacy_acknowledged": "Please read and acknowledge the privacy notice before submitting."
            })

        barangay_id = attrs.pop("barangay_id")
        barangay = Barangay.get_eligible_for_registration().filter(pk=barangay_id).first()
        if barangay is None or not barangay.is_approved_and_active():
            raise serializers.ValidationError({
                "barangay_id": "Select an approved and active Barangay."
            })
        attrs["barangay"] = barangay
        return attrs


class KioskQueueTicketSerializer(KioskSubmissionSerializer):
    walkin_name = serializers.CharField(min_length=2, max_length=255, trim_whitespace=True)
    service_type = serializers.ChoiceField(choices=QUEUE_SERVICE_TYPES)


class KioskDocumentRequestSerializer(KioskSubmissionSerializer):
    walkin_name = serializers.CharField(min_length=2, max_length=255, trim_whitespace=True)
    walkin_purok = serializers.CharField(max_length=100, allow_blank=True, required=False, trim_whitespace=True)
    document_type = serializers.ChoiceField(choices=(
        "Barangay Clearance",
        "Certificate of Indigency",
        "Certificate of Residency",
        "Barangay Business Clearance",
    ))
    purpose = serializers.CharField(min_length=2, max_length=500, trim_whitespace=True)


class KioskIssueReportSerializer(KioskSubmissionSerializer):
    walkin_name = serializers.CharField(max_length=255, allow_blank=True, required=False, trim_whitespace=True)
    category = serializers.ChoiceField(choices=IssueReport.Category.choices)
    title = serializers.CharField(min_length=3, max_length=255, trim_whitespace=True)
    description = serializers.CharField(min_length=10, max_length=5000, trim_whitespace=True)
    location = serializers.CharField(min_length=2, max_length=255, trim_whitespace=True)


def _authenticate_kiosk_resident(identifier: str, password: str, barangay: Barangay) -> User | None:
    """Verify resident credentials ephemerally for kiosk equipment borrowing without starting a session."""
    cleaned_id = (identifier or "").strip()
    if not cleaned_id or not password:
        return None

    username_to_auth = cleaned_id
    email_matches = list(User.objects.filter(email__iexact=cleaned_id).order_by("pk")[:2])
    if len(email_matches) == 1:
        username_to_auth = email_matches[0].username
    elif len(email_matches) > 1:
        username_matches = list(User.objects.filter(username__iexact=cleaned_id).order_by("pk")[:2])
        if len(username_matches) != 1:
            return None
        username_to_auth = username_matches[0].username
    else:
        username_matches = list(User.objects.filter(username__iexact=cleaned_id).order_by("pk")[:2])
        if len(username_matches) == 1:
            username_to_auth = username_matches[0].username

    user = authenticate(username=username_to_auth, password=password)
    if user is None or not user.is_active:
        return None
    if user.role != User.Role.RESIDENT or user.barangay_id != barangay.id:
        return None
    profile = getattr(user, "profile", None)
    if profile is None or not profile.is_verified:
        return None
    return user


class KioskEquipmentBorrowSerializer(KioskSubmissionSerializer):
    auth_mode = serializers.ChoiceField(
        choices=("resident", "staff_pin"),
        write_only=True,
    )
    resident_username = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=True,
        write_only=True,
        trim_whitespace=True,
    )
    resident_password = serializers.CharField(
        max_length=128,
        required=False,
        allow_blank=True,
        write_only=True,
        trim_whitespace=False,
    )
    staff_kiosk_pin = serializers.CharField(
        max_length=12,
        required=False,
        allow_blank=True,
        write_only=True,
        trim_whitespace=True,
    )
    walkin_name = serializers.CharField(
        min_length=2,
        max_length=255,
        required=False,
        allow_blank=True,
        trim_whitespace=True,
    )
    walkin_contact = serializers.CharField(
        min_length=7,
        max_length=50,
        trim_whitespace=True,
    )
    walkin_purok = serializers.CharField(
        min_length=2,
        max_length=100,
        trim_whitespace=True,
    )
    borrower_id_type = serializers.ChoiceField(choices=BORROWER_ID_TYPES)
    item_type = serializers.ChoiceField(choices=EquipmentBorrowRequest.ItemType.choices)
    quantity = serializers.IntegerField(min_value=1, max_value=500, default=1)
    borrow_date = serializers.DateField()
    return_date = serializers.DateField()
    time_slot = serializers.CharField(max_length=100, allow_blank=True, required=False, trim_whitespace=True)
    purpose = serializers.CharField(min_length=10, max_length=2000, trim_whitespace=True)

    def validate_walkin_contact(self, value):
        digits = re.sub(r"\D", "", value or "")
        if len(digits) < 7 or len(digits) > 15:
            raise serializers.ValidationError(
                "Enter a valid contact phone number (7 to 15 digits)."
            )
        return value.strip()

    def validate(self, attrs):
        attrs = super().validate(attrs)
        barangay = attrs["barangay"]
        auth_mode = attrs.pop("auth_mode")
        resident_username = attrs.pop("resident_username", "")
        resident_password = attrs.pop("resident_password", "")
        staff_kiosk_pin = attrs.pop("staff_kiosk_pin", "")

        if auth_mode == "resident":
            verified_user = _authenticate_kiosk_resident(
                resident_username,
                resident_password,
                barangay,
            )
            if verified_user is None:
                request_obj = self.context.get("request")
                log_action(
                    user=None,
                    action_type=AuditLog.ActionType.USER_ACTION,
                    description=(
                        f"Failed kiosk resident authentication attempt for username '{resident_username}' "
                        f"(Barangay {barangay.name})."
                    ),
                    request=request_obj,
                )
                logger.warning(
                    "Failed kiosk resident authentication attempt for username '%s' in Barangay %s",
                    resident_username,
                    barangay.id,
                )
                raise serializers.ValidationError({
                    "detail": (
                        "Invalid resident credentials, or your account is not yet verified "
                        "for this Barangay."
                    )
                })
            profile = verified_user.profile
            attrs["resident"] = verified_user
            attrs["is_walkin"] = False
            attrs["kiosk_auth_method"] = "RESIDENT_VERIFIED"
            attrs["walkin_name"] = (profile.full_name or verified_user.username).strip()
        else:
            if not barangay.kiosk_staff_pin_hash or not staff_kiosk_pin or not barangay.check_kiosk_staff_pin(staff_kiosk_pin):
                request_obj = self.context.get("request")
                log_action(
                    user=None,
                    action_type=AuditLog.ActionType.USER_ACTION,
                    description=(
                        f"Failed kiosk staff PIN attempt for Barangay {barangay.name}."
                    ),
                    request=request_obj,
                )
                logger.warning(
                    "Failed kiosk staff PIN attempt for Barangay %s (has_hash=%s)",
                    barangay.id,
                    bool(barangay.kiosk_staff_pin_hash),
                )
                raise serializers.ValidationError({
                    "staff_kiosk_pin": "Invalid or unconfigured Barangay Staff Kiosk PIN."
                })
            walkin_name = (attrs.get("walkin_name") or "").strip()
            if len(walkin_name) < 2:
                raise serializers.ValidationError({
                    "walkin_name": "Borrower full name is required for walk-in equipment borrowing."
                })
            attrs["resident"] = None
            attrs["is_walkin"] = True
            attrs["kiosk_auth_method"] = "STAFF_PIN"
            attrs["walkin_name"] = walkin_name

        borrow_date = attrs.get("borrow_date")
        return_date = attrs.get("return_date")
        today_manila = timezone.localtime(timezone.now(), MANILA_TIME_ZONE).date()
        if borrow_date and borrow_date < today_manila:
            raise serializers.ValidationError({
                "borrow_date": "Borrow date cannot be in the past."
            })
        if borrow_date and return_date and return_date < borrow_date:
            raise serializers.ValidationError({
                "return_date": "Return date cannot be earlier than borrow date."
            })
        return attrs


class KioskSubmissionView(APIView):
    """Common anonymous write-only endpoint policy; subclasses create one record."""

    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [SharedDatabaseScopedRateThrottle]
    throttle_scope = "kiosk_intake"
    parser_classes = [JSONParser]
    serializer_class = KioskSubmissionSerializer
    notification_type = None

    def post(self, request):
        self._current_request = request
        serializer = self.serializer_class(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            record = self.create_record(serializer.validated_data)
            notify_barangay_admins(
                barangay_id=record.barangay_id,
                notification_type=self.notification_type,
                source="kiosk",
            )
        return Response(self.response_data(record), status=status.HTTP_201_CREATED)

    def create_record(self, data):
        raise NotImplementedError

    def response_data(self, record):
        raise NotImplementedError


class KioskQueueTicketView(KioskSubmissionView):
    serializer_class = KioskQueueTicketSerializer
    notification_type = AdminNotification.Type.QUEUE

    def create_record(self, data):
        ticket = QueueTicket.objects.create(
            user=None,
            barangay=data["barangay"],
            walkin_name=data["walkin_name"],
            service_type=data["service_type"],
            priority_status=QueueTicket.Priority.REGULAR,
            is_priority=False,
            status=QueueTicket.Status.WAITING,
            privacy_notice_version=KIOSK_PRIVACY_NOTICE_VERSION,
            privacy_acknowledged_at=timezone.now(),
        )
        broadcast_queue_update(
            barangay_id=ticket.barangay_id,
            ticket=ticket.ticket_number,
            action="kiosk_create",
        )
        return ticket

    def response_data(self, record):
        return {
            "reference": record.ticket_number,
            "status": QueueTicket.Status.WAITING,
        }


class KioskDocumentRequestView(KioskSubmissionView):
    serializer_class = KioskDocumentRequestSerializer
    notification_type = AdminNotification.Type.DOCUMENT

    def create_record(self, data):
        return DocumentRequest.objects.create(
            user=None,
            barangay=data["barangay"],
            is_walkin=True,
            walkin_name=data["walkin_name"],
            walkin_purok=data.get("walkin_purok", ""),
            document_type=data["document_type"],
            purpose=data["purpose"],
            urgency_tag=DocumentRequest.UrgencyTag.REGULAR,
            status=DocumentRequest.Status.PENDING,
            fee_assessment_status=DocumentRequest.FeeAssessmentStatus.AWAITING_ASSESSMENT,
            fee_amount=0,
            fee_assessed_by=None,
            fee_assessed_at=None,
            fee_waiver_reason="",
            admin_notes="",
            privacy_notice_version=KIOSK_PRIVACY_NOTICE_VERSION,
            privacy_acknowledged_at=timezone.now(),
        )

    def response_data(self, record):
        return {
            "reference": f"DR-{record.pk:06d}",
            "status": DocumentRequest.Status.PENDING,
        }


class KioskIssueReportView(KioskSubmissionView):
    serializer_class = KioskIssueReportSerializer
    notification_type = AdminNotification.Type.REPORT

    def create_record(self, data):
        return IssueReport.objects.create(
            reporter=None,
            barangay=data["barangay"],
            walkin_name=data.get("walkin_name") or None,
            category=data["category"],
            title=data["title"],
            description=data["description"],
            location=data["location"],
            status=IssueReport.Status.PENDING,
            urgency=IssueReport.Urgency.MINOR,
            privacy_notice_version=KIOSK_PRIVACY_NOTICE_VERSION,
            privacy_acknowledged_at=timezone.now(),
        )

    def response_data(self, record):
        return {
            "reference": f"IR-{record.pk:06d}",
            "status": IssueReport.Status.PENDING,
        }


class KioskEquipmentBorrowRequestView(KioskSubmissionView):
    serializer_class = KioskEquipmentBorrowSerializer
    notification_type = AdminNotification.Type.SYSTEM

    def post(self, request):
        self._current_request = request
        return super().post(request)

    def create_record(self, data):
        record = EquipmentBorrowRequest.objects.create(
            resident=data.get("resident"),
            barangay=data["barangay"],
            is_walkin=data.get("is_walkin", True),
            walkin_name=data["walkin_name"],
            walkin_contact=data["walkin_contact"],
            walkin_purok=data["walkin_purok"],
            borrower_id_type=data["borrower_id_type"],
            kiosk_auth_method=data["kiosk_auth_method"],
            item_type=data["item_type"],
            quantity=data.get("quantity", 1),
            borrow_date=data["borrow_date"],
            return_date=data["return_date"],
            time_slot=data.get("time_slot", ""),
            purpose=data["purpose"],
            status=EquipmentBorrowRequest.Status.PENDING,
        )
        log_action(
            user=record.resident,
            action_type=AuditLog.ActionType.USER_ACTION,
            description=(
                f"Kiosk equipment borrow request EQ-{record.pk:06d} created for "
                f"{record.walkin_name} via {record.kiosk_auth_method} "
                f"({record.item_type} x{record.quantity})."
            ),
            request=getattr(self, "_current_request", None),
        )
        return record

    def response_data(self, record):
        return {
            "reference": f"EQ-{record.pk:06d}",
            "status": EquipmentBorrowRequest.Status.PENDING,
        }
