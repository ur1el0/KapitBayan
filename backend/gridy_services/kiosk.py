"""Anonymous, write-only intake for a physically supervised Barangay kiosk."""

from collections.abc import Mapping

from django.db import transaction
from django.utils import timezone
from rest_framework import permissions, serializers, status
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from gridy_auth.models import Barangay
from gridy_auth.throttling import SharedDatabaseScopedRateThrottle
from gridy_communications.admin_notifications import notify_barangay_admins
from gridy_communications.models import AdminNotification
from gridy_reports.models import IssueReport
from gridy_services.models import DocumentRequest, QueueTicket


KIOSK_PRIVACY_NOTICE_VERSION = "kiosk-v1"
QUEUE_SERVICE_TYPES = (
    "Document Processing & Clearances",
    "Barangay ID Application",
    "Certificate of Indigency",
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
        serializer = self.serializer_class(data=request.data)
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
        return QueueTicket.objects.create(
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
