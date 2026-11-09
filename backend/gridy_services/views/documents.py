import json
import logging
import re
import uuid

from django.conf import settings
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef, Q
from django.db.models.functions import Lower, Trim
from django.template.loader import get_template
from django.http import FileResponse, Http404, HttpResponse
from PIL import Image, UnidentifiedImageError
from django.utils import timezone
from django.utils.crypto import salted_hmac
from xhtml2pdf import pisa
from gridy_auth.models import Barangay, User
from gridy_auth.permissions import (
    IsBarangayOfficial,
    IsBarangayOfficialOrField,
    IsResident,
    IsResidentOrBarangayOfficial,
)
from gridy_services.models import (
    DocumentCertificateVerification,
    DocumentRequest,
    DocumentServiceOffering,
    PaymentRecipient,
    QueueTicket,
    manila_day_bounds,
)
from gridy_services.official_receipts import assign_official_receipt_number
from gridy_services.signals import safe_delete_storage_file
from gridy_services.serializers import (
    DocumentRequestSerializer,
    DocumentRequestReviewSerializer,
    OfficialReceiptNumberSerializer,
    PaymentChoiceSerializer,
    PaymentReferenceSerializer,
    PaymentReviewSerializer,
    WalkInCashPaymentConfirmationSerializer,
)
from gridy_communications.tasks import send_notification_to_user_task
from gridy_communications.admin_notifications import notify_barangay_admins
from gridy_communications.models import ResidentNotification
from decimal import Decimal
from gridy_audit.services import log_action
from gridy_audit.models import AuditLog
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError
from drf_spectacular.utils import extend_schema
from ..fee_policy import FEE_EXEMPT_DOCUMENT_TYPES, check_ra11261_eligibility
from ..release_rules import validate_document_release_requirements

logger = logging.getLogger(__name__)


class DocumentSubmissionConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "This submission key was already used for different request details."
    default_code = "idempotency_conflict"

FINANCIAL_REVIEW_FIELDS = {
    "or_number",
    "fee_amount",
    "fee_waiver_reason",
    "fee_assessment_status",
    "statutory_exempt",
    "is_statutory_exempt",
}


def _document_request_id_from_tracking_identifier(identifier):
    """Parse supported printed tracking identifiers without treating OR digits as IDs."""
    match = re.fullmatch(r"(?:REQ[-\s#:]*)(\d+)", identifier, flags=re.IGNORECASE)
    if match is None:
        match = re.fullmatch(r"(\d+)", identifier)
    if match is None:
        match = re.fullmatch(r"KB-DOC-(\d+)", identifier, flags=re.IGNORECASE)
    if match is None:
        match = re.fullmatch(
            r"(?:ID:\s*)?#?(?:BC|CI|RC|BP|DOC)-\d{4}-(\d+)",
            identifier,
            flags=re.IGNORECASE,
        )
    return int(match.group(1)) if match else None

CANONICAL_DOCUMENT_SNAPSHOTS = {
    "barangay clearance": {
        "requirements": [
            "Government ID or proof of residency",
            "Community Tax Certificate (Cedula)",
        ],
        "published_fee_amount": Decimal("50.00"),
        "details": "Standard clearance for employment, identification, and official transactions.",
    },
    "certificate of indigency": {
        "requirements": [
            "Government ID or proof of residency",
            "Proof of indigent status or declaration of low income",
        ],
        "published_fee_amount": Decimal("0.00"),
        "details": "Statutory fee-exempt certificate for social welfare, medical, and legal assistance.",
    },
    "certificate of residency": {
        "requirements": [
            "Government ID",
            "Proof of address (utility bill, lease contract, or voter certification)",
        ],
        "published_fee_amount": Decimal("50.00"),
        "details": "Official certification verifying residency address within the Barangay.",
    },
    "residency certificate": {
        "requirements": [
            "Government ID",
            "Proof of address (utility bill, lease contract, or voter certification)",
        ],
        "published_fee_amount": Decimal("50.00"),
        "details": "Official certification verifying residency address within the Barangay.",
    },
    "barangay business clearance": {
        "requirements": [
            "Government ID of owner or representative",
            "DTI or SEC Certificate of Registration",
            "Contract of lease or proof of property ownership",
        ],
        "published_fee_amount": Decimal("200.00"),
        "details": "Clearance required for new business registration or annual business permit renewal.",
    },
    "business permit": {
        "requirements": [
            "Government ID of owner or representative",
            "DTI or SEC Certificate of Registration",
            "Contract of lease or proof of property ownership",
        ],
        "published_fee_amount": Decimal("200.00"),
        "details": "Clearance required for new business registration or annual business permit renewal.",
    },
}


def _resolve_active_pickup_tickets(document_request, *, actor, request):
    """Close queue work once the linked document has been physically released.

    A still-waiting pickup ticket is cancelled because it is no longer needed;
    a serving ticket is completed because the resident was already at the desk.
    """
    tickets = QueueTicket.objects.select_for_update().filter(
        document_request=document_request,
        status__in=(QueueTicket.Status.WAITING, QueueTicket.Status.SERVING),
    )
    for ticket in tickets:
        previous_status = ticket.status
        ticket.status = (
            QueueTicket.Status.COMPLETED
            if previous_status == QueueTicket.Status.SERVING
            else QueueTicket.Status.CANCELLED
        )
        ticket.save(update_fields=["status", "updated_at"])
        log_action(
            user=actor,
            action_type=AuditLog.ActionType.QUEUE_ACTION,
            description=(
                f"Closed pickup ticket {ticket.ticket_number} (ID: {ticket.pk}) "
                f"when linked document request #{document_request.pk} was released "
                f"({previous_status} to {ticket.status})."
            ),
            request=request,
        )


def _document_barangay_id(document_request):
    return document_request.barangay_id or (
        document_request.user.barangay_id if document_request.user_id else None
    )


def _ensure_unique_barangay_or_number(document_request, or_number):
    """Reject normalized duplicate O.R.s; write callers lock the Barangay row."""
    normalized = (or_number or "").strip().lower()
    if not normalized:
        return

    barangay_id = _document_barangay_id(document_request)
    duplicate_requests = DocumentRequest.objects.annotate(
        normalized_or_number=Lower(Trim("or_number")),
    ).filter(
        normalized_or_number=normalized,
    ).exclude(pk=document_request.pk)
    if barangay_id is not None:
        duplicate_requests = duplicate_requests.filter(
            Q(barangay_id=barangay_id)
            | Q(
                barangay__isnull=True,
                is_walkin=False,
                user__barangay_id=barangay_id,
            )
        )
    else:
        duplicate_requests = duplicate_requests.filter(
            barangay__isnull=True,
            user__isnull=True,
        )

    if duplicate_requests.exists():
        raise ValidationError({
            "or_number": (
                "This O.R. number is already recorded for another request in "
                "this Barangay."
            )
        })


class DocumentRequestViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentRequestSerializer

    @staticmethod
    def _submission_fingerprint(validated_data):
        offering = validated_data.get("offering")
        value = {
            "document_type": " ".join(
                (validated_data.get("document_type") or "").split()
            ).casefold(),
            "offering_id": offering.pk if offering else None,
            "purpose": (validated_data.get("purpose") or "").strip(),
            "urgency_tag": validated_data.get("urgency_tag") or "REGULAR",
            "walkin_name": (validated_data.get("walkin_name") or "").strip(),
            "walkin_purok": (validated_data.get("walkin_purok") or "").strip(),
        }
        canonical = json.dumps(value, sort_keys=True, separators=(",", ":"))
        return salted_hmac(
            "gridy.document_request.idempotency",
            canonical,
            algorithm="sha256",
        ).hexdigest()

    def create(self, request, *args, **kwargs):
        raw_key = request.headers.get("Idempotency-Key", "").strip()
        if raw_key:
            try:
                request._document_submission_key = uuid.UUID(raw_key)
            except (ValueError, AttributeError):
                raise ValidationError({
                    "Idempotency-Key": "Use a valid UUID submission key."
                })
        else:
            request._document_submission_key = None

        try:
            response = super().create(request, *args, **kwargs)
        except IntegrityError:
            key = request._document_submission_key
            if key is None:
                raise
            existing = DocumentRequest.objects.filter(
                submitted_by=request.user,
                submission_key=key,
            ).first()
            if existing is None:
                raise
            retry_serializer = self.get_serializer(data=request.data)
            retry_serializer.is_valid(raise_exception=True)
            fingerprint = self._submission_fingerprint(
                retry_serializer.validated_data
            )
            if existing.submission_fingerprint != fingerprint:
                raise DocumentSubmissionConflict({
                    "Idempotency-Key": (
                        "This submission key was already used for different request details."
                    )
                })
            return Response(
                self.get_serializer(existing).data,
                status=status.HTTP_200_OK,
            )

        if getattr(request, "_document_submission_replayed", False):
            response.status_code = status.HTTP_200_OK
        return response
    
    def get_permissions(self):
        # Authenticated users can list, view, and download their own approved PDFs or payment proof
        if self.action in ['list', 'retrieve', 'generate_pdf', 'payment_proof']:
            return [permissions.IsAuthenticated()]

        if self.action in {"choose_payment_method", "submit_payment_reference"}:
            return [permissions.IsAuthenticated(), IsResident()]

        if self.action == "create":
            return [
                permissions.IsAuthenticated(),
                IsResidentOrBarangayOfficial(),
            ]
        
        # Allow authenticated users to access destroy (role and status checks enforced in perform_destroy)
        if self.action == 'destroy':
            return [permissions.IsAuthenticated()]

        if self.action == "review_payment":
            return [permissions.IsAuthenticated(), IsBarangayOfficial()]

        if self.action in ["validate", "verify"]:
            return [permissions.IsAuthenticated(), IsBarangayOfficialOrField()]

        return [IsBarangayOfficial()]

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return DocumentRequest.objects.none()

        queue_day_start, queue_next_day_start = manila_day_bounds()
        active_queue_ticket = QueueTicket.objects.filter(
            document_request_id=OuterRef("pk"),
            status__in=(QueueTicket.Status.WAITING, QueueTicket.Status.SERVING),
            created_at__gte=queue_day_start,
            created_at__lt=queue_next_day_start,
        )
        
        # The request's barangay is authoritative; only legacy null-barangay
        # digital requests fall back to the resident's current barangay.
        if user.role in [User.Role.ADMIN, User.Role.FIELD_OFFICIAL]:
            if user.barangay_id is None:
                return DocumentRequest.objects.none()
            queryset = DocumentRequest.objects.filter(
                Q(barangay_id=user.barangay_id)
                | Q(
                    barangay_id__isnull=True,
                    is_walkin=False,
                    user__barangay_id=user.barangay_id,
                )
            ).select_related("offering")
            return queryset.annotate(
                has_active_queue_ticket=Exists(active_queue_ticket)
            ).order_by('-created_at')

        # Residents see only their own requests
        return DocumentRequest.objects.filter(user=user).select_related(
            "offering"
        ).annotate(
            has_active_queue_ticket=Exists(active_queue_ticket)
        ).order_by('-created_at')

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[IsBarangayOfficialOrField],
        url_path="verify",
        url_name="verify",
    )
    def verify(self, request):
        """Find a same-Barangay document by exact O.R. number or printed tracking ID."""
        identifier = (request.query_params.get("identifier") or "").strip()
        if not identifier:
            raise ValidationError({"identifier": "Enter a tracking ID or O.R. number."})
        if len(identifier) > 100:
            raise ValidationError({"identifier": "The value is too long."})

        requests = self.get_queryset().select_related("user", "barangay")
        receipt_matches = requests.annotate(
            normalized_or_number=Lower(Trim("or_number")),
        ).filter(
            normalized_or_number=identifier.strip().lower(),
        )
        match_count = receipt_matches.count()
        if match_count > 1:
            return Response(
                {"detail": "This O.R. number matches multiple records. Ask the Barangay Admin to review it."},
                status=status.HTTP_409_CONFLICT,
            )

        document_request = receipt_matches.first()
        if document_request is None:
            tracking_id = _document_request_id_from_tracking_identifier(identifier)
            if tracking_id is not None:
                document_request = requests.filter(pk=tracking_id).first()

        if document_request is None:
            raise Http404("No document or O.R. record was found in this Barangay.")

        return Response(
            DocumentRequestSerializer(
                document_request,
                context={"request": request},
            ).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        request=PaymentChoiceSerializer,
        responses=DocumentRequestSerializer,
    )
    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsResident],
        url_path="payment-choice",
        url_name="payment-choice",
    )
    def choose_payment_method(self, request, pk=None):
        """Save a resident's choice of cash or an active same-Barangay e-payment recipient."""
        document_request = self.get_object()
        serializer = PaymentChoiceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        old_proof_name = None
        old_storage = None
        with transaction.atomic():
            document_request = DocumentRequest.objects.select_for_update().get(
                pk=document_request.pk,
                user_id=request.user.id,
            )
            if document_request.status != DocumentRequest.Status.READY_FOR_PICKUP:
                raise ValidationError({
                    "detail": "Choose a payment method after the document is ready for pickup."
                })
            if document_request.fee_amount <= 0:
                raise ValidationError({
                    "detail": "This request does not require a payment."
                })
            if document_request.payment_status not in {
                DocumentRequest.PaymentStatus.UNPAID,
                DocumentRequest.PaymentStatus.REJECTED,
            }:
                raise ValidationError({
                    "detail": "Payment method cannot be changed while payment is under review or verified."
                })

            selected = serializer.validated_data
            if selected.get("payment_method") == DocumentRequest.PaymentMethod.CASH:
                recipient = None
                payment_method = DocumentRequest.PaymentMethod.CASH
            else:
                recipient = PaymentRecipient.objects.filter(
                    pk=selected["payment_recipient_id"],
                    barangay_id=document_request.barangay_id,
                    is_active=True,
                ).first()
                if recipient is None:
                    raise ValidationError({
                        "payment_recipient_id": "Select an active payment recipient configured by your barangay."
                    })

                payment_method = recipient.provider

            choice_is_unchanged = (
                document_request.payment_method == payment_method
                and document_request.payment_recipient_id
                == (recipient.pk if recipient else None)
            )
            was_rejected = (
                document_request.payment_status
                == DocumentRequest.PaymentStatus.REJECTED
            )
            if choice_is_unchanged and not was_rejected:
                return Response(
                    DocumentRequestSerializer(
                        document_request,
                        context={"request": request},
                    ).data,
                    status=status.HTTP_200_OK,
                )

            if document_request.payment_proof_image and document_request.payment_proof_image.name:
                old_proof_name = document_request.payment_proof_image.name
                old_storage = document_request.payment_proof_image.storage

            document_request.payment_method = payment_method
            document_request.payment_recipient = recipient
            document_request.payment_recipient_name_snapshot = (
                recipient.recipient_name if recipient else ""
            )
            document_request.payment_recipient_identifier_snapshot = (
                recipient.recipient_identifier if recipient else ""
            )
            document_request.payment_instructions_snapshot = (
                recipient.instructions if recipient else ""
            )
            document_request.payment_reference = ""
            document_request.payment_transacted_at = None
            document_request.payment_proof_image = None
            document_request.payment_status = DocumentRequest.PaymentStatus.UNPAID
            document_request.payment_review_note = ""
            document_request.save(
                update_fields=[
                    "payment_method",
                    "payment_recipient",
                    "payment_recipient_name_snapshot",
                    "payment_recipient_identifier_snapshot",
                    "payment_instructions_snapshot",
                    "payment_reference",
                    "payment_transacted_at",
                    "payment_proof_image",
                    "payment_status",
                    "payment_review_note",
                    "updated_at",
                ]
            )
            if old_proof_name and old_storage:
                transaction.on_commit(
                    lambda s=old_storage, p=old_proof_name: safe_delete_storage_file(s, p)
                )

            log_action(
                user=request.user,
                action_type=AuditLog.ActionType.DOCUMENT_ACTION,
                description=(
                    f"Resident selected {document_request.get_payment_method_display()} "
                    f"for document request #{document_request.id}."
                ),
                request=request,
            )

        return Response(
            DocumentRequestSerializer(document_request, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["patch"],
        permission_classes=[IsBarangayOfficial],
        url_path="or-number",
        url_name="or-number",
    )
    def save_or_number(self, request, pk=None):
        """Keep the legacy endpoint read-only; receipt numbers come from the configured series."""
        document_request = self.get_object()
        serializer = OfficialReceiptNumberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        submitted_number = serializer.validated_data["or_number"]
        if submitted_number == (document_request.or_number or ""):
            return Response(
                DocumentRequestSerializer(
                    document_request,
                    context={"request": request},
                ).data,
                status=status.HTTP_200_OK,
            )
        raise ValidationError({
            "or_number": (
                "O.R. numbers are assigned automatically from the Barangay's approved series when staff confirms payment."
            )
        })

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsBarangayOfficial],
        url_path="record-cash-payment",
        url_name="record-cash-payment",
    )
    def record_cash_payment(self, request, pk=None):
        """Record cash received for a walk-in request that has no resident account."""
        confirmation = WalkInCashPaymentConfirmationSerializer(data=request.data)
        confirmation.is_valid(raise_exception=True)

        with transaction.atomic():
            document_request = DocumentRequest.objects.select_for_update().get(
                pk=self.get_object().pk,
                barangay_id=request.user.barangay_id,
            )
            if not document_request.is_walkin:
                raise ValidationError({
                    "detail": "This cash-receipt action is only for walk-in requests."
                })
            if document_request.status != DocumentRequest.Status.READY_FOR_PICKUP:
                raise ValidationError({
                    "detail": "The request must be ready for pickup before recording payment."
                })
            if (
                document_request.fee_amount <= 0
                or document_request.fee_assessment_status
                != DocumentRequest.FeeAssessmentStatus.ASSESSED
            ):
                raise ValidationError({
                    "detail": "Assess a positive document fee before recording cash payment."
                })

            payment_was_already_confirmed = (
                document_request.payment_method in (
                    "",
                    DocumentRequest.PaymentMethod.CASH,
                )
                and document_request.payment_status
                == DocumentRequest.PaymentStatus.VERIFIED
            )
            if payment_was_already_confirmed and document_request.or_number:
                return Response(
                    DocumentRequestSerializer(
                        document_request,
                        context={"request": request},
                    ).data,
                    status=status.HTTP_200_OK,
                )

            if document_request.payment_method not in (
                "",
                DocumentRequest.PaymentMethod.CASH,
            ):
                raise ValidationError({
                    "payment_method": (
                        "This walk-in request has an electronic payment method. Review that payment instead."
                    )
                })
            if not payment_was_already_confirmed and document_request.payment_status not in (
                DocumentRequest.PaymentStatus.UNPAID,
                DocumentRequest.PaymentStatus.REJECTED,
            ):
                raise ValidationError({
                    "payment_status": "This payment cannot be changed in its current state."
                })

            old_proof_name = None
            old_storage = None
            if document_request.payment_proof_image and document_request.payment_proof_image.name:
                old_proof_name = document_request.payment_proof_image.name
                old_storage = document_request.payment_proof_image.storage

            document_request.payment_method = DocumentRequest.PaymentMethod.CASH
            document_request.payment_recipient = None
            document_request.payment_recipient_name_snapshot = ""
            document_request.payment_recipient_identifier_snapshot = ""
            document_request.payment_instructions_snapshot = ""
            document_request.payment_reference = ""
            if not payment_was_already_confirmed:
                document_request.payment_transacted_at = timezone.now()
            document_request.payment_proof_image = None
            document_request.payment_status = DocumentRequest.PaymentStatus.VERIFIED
            document_request.payment_review_note = "Walk-in cash received in person."
            assigned_or_number = assign_official_receipt_number(document_request)
            document_request.save(
                update_fields=[
                    "payment_method",
                    "payment_recipient",
                    "payment_recipient_name_snapshot",
                    "payment_recipient_identifier_snapshot",
                    "payment_instructions_snapshot",
                    "payment_reference",
                    "payment_transacted_at",
                    "payment_proof_image",
                    "payment_status",
                    "payment_review_note",
                    "or_number",
                    "updated_at",
                ]
            )
            if old_proof_name and old_storage:
                transaction.on_commit(
                    lambda s=old_storage, p=old_proof_name: safe_delete_storage_file(s, p)
                )

            log_action(
                user=request.user,
                action_type=AuditLog.ActionType.DOCUMENT_ACTION,
                description=(
                    f"Recorded cash payment of ₱{document_request.fee_amount} for "
                    f"walk-in document request #{document_request.pk}; assigned O.R. {assigned_or_number}."
                ),
                request=request,
            )

        return Response(
            DocumentRequestSerializer(
                document_request,
                context={"request": request},
            ).data,
            status=status.HTTP_200_OK,
        )

    @transaction.atomic
    def perform_create(self, serializer):
        user = self.request.user
        data = serializer.validated_data
        submission_key = getattr(self.request, "_document_submission_key", None)
        submission_fingerprint = self._submission_fingerprint(data)
        if submission_key is not None:
            existing = DocumentRequest.objects.filter(
                submitted_by=user,
                submission_key=submission_key,
            ).first()
            if existing is not None:
                if existing.submission_fingerprint != submission_fingerprint:
                    raise DocumentSubmissionConflict({
                        "Idempotency-Key": (
                            "This submission key was already used for different request details."
                        )
                    })
                serializer.instance = existing
                self.request._document_submission_replayed = True
                return

        offering = data.get("offering")
        barangay = user.barangay if user and user.is_authenticated else None

        doc_type_clean = " ".join((data.get("document_type") or "").split())

        if not offering and barangay:
            offering = DocumentServiceOffering.objects.filter(
                barangay=barangay,
                is_active=True,
                document_type__iexact=doc_type_clean,
            ).first()
            if offering:
                serializer.validated_data["offering"] = offering

        offering_snapshot = {}
        if offering:
            offering_snapshot = {
                "requirements_snapshot": list(offering.requirements),
                "published_fee_amount_snapshot": offering.published_fee_amount,
                "details_snapshot": offering.details,
            }
        else:
            canonical = CANONICAL_DOCUMENT_SNAPSHOTS.get(doc_type_clean.casefold())
            if canonical:
                offering_snapshot = {
                    "requirements_snapshot": list(canonical.get("requirements", [])),
                    "published_fee_amount_snapshot": canonical.get("published_fee_amount"),
                    "details_snapshot": canonical.get("details", ""),
                }

        if user.role == User.Role.ADMIN:
            if not user.barangay_id:
                raise PermissionDenied(
                    "Your account must be assigned to a barangay to record walk-ins."
                )

            walkin_name = data.get("walkin_name")

            if not walkin_name or not walkin_name.strip():
                raise ValidationError({
                    "walkin_name": "Walk-in resident's full name is required."
                })

            doc_type_clean = " ".join((data.get("document_type") or "").split()).casefold()
            is_statutory = doc_type_clean in FEE_EXEMPT_DOCUMENT_TYPES

            serializer.save(
                user=None,
                submitted_by=user,
                submission_key=submission_key,
                submission_fingerprint=(
                    submission_fingerprint if submission_key is not None else ""
                ),
                barangay=user.barangay,
                is_walkin=True,
                walkin_name=walkin_name.strip(),
                walkin_purok=data.get("walkin_purok") or "",
                or_number="",
                fee_amount=Decimal("0.00"),
                fee_assessment_status=(
                    DocumentRequest.FeeAssessmentStatus.STATUTORY_EXEMPT
                    if is_statutory
                    else DocumentRequest.FeeAssessmentStatus.AWAITING_ASSESSMENT
                ),
                fee_assessed_by=None,
                fee_assessed_at=timezone.now() if is_statutory else None,
                fee_waiver_reason="",
                status=DocumentRequest.Status.PENDING,
                admin_notes="",
                **offering_snapshot,
            )

            log_action(
                user=user,
                action_type=AuditLog.ActionType.DOCUMENT_ACTION,
                description=(
                    f"Recorded walk-in clearance for {walkin_name.strip()} "
                    f"({data.get('document_type', 'Clearance')})."
                ),
                request=self.request,
            )
            return

        if user.role != User.Role.RESIDENT:
            raise PermissionDenied(
                "Only residents can create personal document requests."
            )

        expected_barangay_id = user.barangay_id
        if expected_barangay_id is None:
            raise PermissionDenied(
                "Your account must be assigned to a Barangay before requesting a document."
            )
        Barangay.objects.select_for_update().get(pk=expected_barangay_id)
        user = User.objects.select_for_update().get(pk=user.pk)
        if user.barangay_id != expected_barangay_id:
            raise ValidationError({
                "detail": "Your Barangay assignment changed. Refresh and submit again."
            })

        if hasattr(user, "profile") and not user.profile.is_verified:
            raise PermissionDenied(
                "Your account is currently pending verification. Please verify "
                "your residency with Barangay Hall before requesting clearances."
            )

        doc_type_clean = " ".join((data.get("document_type") or "").split()).casefold()
        is_statutory = doc_type_clean in FEE_EXEMPT_DOCUMENT_TYPES

        serializer.save(
            user=user,
            submitted_by=user,
            submission_key=submission_key,
            submission_fingerprint=(
                submission_fingerprint if submission_key is not None else ""
            ),
            barangay=user.barangay,
            is_walkin=False,
            walkin_name=None,
            walkin_purok="",
            or_number="",
            fee_amount=Decimal("0.00"),
            fee_assessment_status=(
                DocumentRequest.FeeAssessmentStatus.STATUTORY_EXEMPT
                if is_statutory
                else DocumentRequest.FeeAssessmentStatus.AWAITING_ASSESSMENT
            ),
            fee_assessed_by=None,
            fee_assessed_at=timezone.now() if is_statutory else None,
            fee_waiver_reason="",
            status=DocumentRequest.Status.PENDING,
            admin_notes="",
            **offering_snapshot,
        )
        notify_barangay_admins(
            barangay_id=user.barangay_id,
            notification_type='document',
        )

    def perform_destroy(self, instance):
        user = self.request.user
        barangay_id = instance.barangay_id or (
            instance.user.barangay_id if instance.user_id else user.barangay_id
        )

        # Keep deletion in the same lock order as queue advancement and release:
        # Barangay -> document -> linked queue ticket. This prevents a released
        # request from being deleted while a pickup ticket is being completed.
        with transaction.atomic():
            if barangay_id is not None:
                Barangay.objects.select_for_update().get(pk=barangay_id)
            try:
                locked_instance = DocumentRequest.objects.select_for_update().get(
                    pk=instance.pk
                )
            except DocumentRequest.DoesNotExist:
                raise Http404("Document request was already removed.")

            # 1. Resident self-service cancellation.
            if user.role == User.Role.RESIDENT:
                if locked_instance.user_id != user.id:
                    raise PermissionDenied(
                        "You can only cancel your own document requests."
                    )
                if locked_instance.status != DocumentRequest.Status.PENDING:
                    raise ValidationError({
                        "detail": (
                            "You can only cancel document requests that are still "
                            "pending review."
                        )
                    })
                description = (
                    f"Resident {user.username} cancelled pending document request "
                    f"#{locked_instance.id} ({locked_instance.document_type})."
                )
            # 2. Barangay official archival deletion after resolution.
            elif user.role in [User.Role.ADMIN, User.Role.FIELD_OFFICIAL]:
                if locked_instance.status not in [
                    DocumentRequest.Status.RELEASED,
                    DocumentRequest.Status.REJECTED,
                ]:
                    raise ValidationError({
                        "detail": (
                            "Only resolved (released or rejected) clearance "
                            "requests can be deleted by officials."
                        )
                    })

                if locked_instance.status == DocumentRequest.Status.RELEASED:
                    _resolve_active_pickup_tickets(
                        locked_instance,
                        actor=user,
                        request=self.request,
                    )
                elif QueueTicket.objects.filter(
                    document_request=locked_instance,
                    status__in=(QueueTicket.Status.WAITING, QueueTicket.Status.SERVING),
                ).exists():
                    raise ValidationError({
                        "detail": (
                            "Resolve the linked queue ticket before deleting this "
                            "rejected request."
                        )
                    })

                recipient_desc = (
                    locked_instance.user.username
                    if locked_instance.user_id
                    else (locked_instance.walkin_name or "Resident")
                )
                description = (
                    f"Deleted {locked_instance.get_status_display().lower()} "
                    f"document request #{locked_instance.id} "
                    f"({locked_instance.document_type}) for {recipient_desc}."
                )
            else:
                raise PermissionDenied(
                    "You do not have permission to delete this document request."
                )

            log_action(
                user=user,
                action_type=AuditLog.ActionType.DOCUMENT_ACTION,
                description=description,
                request=self.request,
            )
            locked_instance.delete()

    @action(detail=True, methods=['patch'], permission_classes=[IsBarangayOfficialOrField])
    def validate(self, request, pk=None):
        with transaction.atomic():
            scoped_request = self.get_object()
            # Queue advancement locks the Barangay before a linked document and
            # ticket. Take the same parent lock before a release can lock those
            # rows, avoiding a document/ticket lock inversion under concurrency.
            if (
                request.data.get("status") == DocumentRequest.Status.RELEASED
                or "or_number" in request.data
            ):
                barangay_id = _document_barangay_id(scoped_request)
                if barangay_id is not None:
                    Barangay.objects.select_for_update().get(pk=barangay_id)
            document_request = DocumentRequest.objects.select_for_update().get(
                pk=scoped_request.pk
            )
            if (
                request.user.role == User.Role.FIELD_OFFICIAL
                and FINANCIAL_REVIEW_FIELDS.intersection(request.data.keys())
            ):
                raise PermissionDenied(
                    "Only a Barangay Admin can assess fees, grant fee exemptions, or record an O.R. number."
                )

            original_status = document_request.status
            initial_fee_assessment_status = document_request.fee_assessment_status
            serializer = DocumentRequestReviewSerializer(
                document_request,
                data=request.data,
                partial=True,
            )
            if "or_number" in request.data:
                submitted_or_number = request.data.get("or_number")
                if submitted_or_number is None:
                    submitted_or_number = ""
                if (
                    not isinstance(submitted_or_number, str)
                    or submitted_or_number.strip() != (document_request.or_number or "")
                ):
                    raise ValidationError({
                        "or_number": (
                            "O.R. numbers are assigned automatically from the Barangay's approved series when staff confirms payment."
                        )
                    })
            serializer.is_valid(raise_exception=True)
            document_request = serializer.save()
            doc_type_clean = " ".join((document_request.document_type or "").split()).casefold()
            is_statutory = doc_type_clean in FEE_EXEMPT_DOCUMENT_TYPES

            fee_amount_input = request.data.get("fee_amount")
            fee_waiver_reason_input = request.data.get("fee_waiver_reason")
            fee_assessment_status_input = request.data.get("fee_assessment_status")
            statutory_exempt_flag = request.data.get("statutory_exempt") or request.data.get("is_statutory_exempt")

            if (
                fee_assessment_status_input is not None
                and fee_assessment_status_input
                != DocumentRequest.FeeAssessmentStatus.STATUTORY_EXEMPT
            ):
                raise ValidationError({
                    "fee_assessment_status": (
                        "Assessment status is derived from fee assessment inputs and cannot be set directly."
                    )
                })

            if fee_assessment_status_input == DocumentRequest.FeeAssessmentStatus.STATUTORY_EXEMPT or statutory_exempt_flag:
                # Staff explicitly grants statutory exemption under RA 11261
                is_eligible, ineligibility_reason = check_ra11261_eligibility(
                    user=document_request.user,
                    document_type=document_request.document_type,
                    current_request_id=document_request.pk,
                )
                if not is_eligible:
                    raise ValidationError({"fee_assessment_status": ineligibility_reason})

                statutory_waiver_reason = (fee_waiver_reason_input or "").strip()
                if not statutory_waiver_reason:
                    raise ValidationError({
                        "fee_waiver_reason": "A written verification reason is required for an RA 11261 exemption."
                    })

                document_request.fee_amount = Decimal("0.00")
                document_request.fee_assessment_status = DocumentRequest.FeeAssessmentStatus.STATUTORY_EXEMPT
                document_request.fee_assessed_by = request.user
                document_request.fee_assessed_at = timezone.now()
                document_request.fee_waiver_reason = statutory_waiver_reason
                document_request.payment_status = DocumentRequest.PaymentStatus.NOT_REQUIRED
                log_action(
                    user=request.user,
                    action_type=AuditLog.ActionType.DOCUMENT_ACTION,
                    description=(
                        f"Granted RA 11261 statutory fee exemption for document request #{document_request.id} "
                        f"({document_request.document_type}). Justification: {document_request.fee_waiver_reason}"
                    ),
                    request=self.request,
                )
            elif is_statutory or initial_fee_assessment_status == DocumentRequest.FeeAssessmentStatus.STATUTORY_EXEMPT:
                document_request.fee_amount = Decimal("0.00")
                document_request.fee_assessment_status = DocumentRequest.FeeAssessmentStatus.STATUTORY_EXEMPT
                document_request.fee_waiver_reason = document_request.fee_waiver_reason or ""
                document_request.fee_assessed_by = request.user
                if not document_request.fee_assessed_at:
                    document_request.fee_assessed_at = timezone.now()
            elif fee_amount_input is not None or fee_waiver_reason_input is not None:
                if document_request.fee_amount > 0:
                    document_request.fee_assessment_status = DocumentRequest.FeeAssessmentStatus.ASSESSED
                    document_request.fee_assessed_by = request.user
                    document_request.fee_assessed_at = timezone.now()
                    document_request.fee_waiver_reason = ""
                    if document_request.payment_status == DocumentRequest.PaymentStatus.NOT_REQUIRED:
                        document_request.payment_status = DocumentRequest.PaymentStatus.UNPAID
                    log_action(
                        user=request.user,
                        action_type=AuditLog.ActionType.DOCUMENT_ACTION,
                        description=(
                            f"Assessed fee of ₱{document_request.fee_amount} for document request #{document_request.id} ({document_request.document_type})."
                        ),
                        request=self.request,
                    )
                else:
                    waiver_reason = (fee_waiver_reason_input or "").strip()
                    if not waiver_reason:
                        raise ValidationError({
                            "fee_waiver_reason": "A written justification is required when waiving document fees."
                        })
                    document_request.fee_amount = Decimal("0.00")
                    document_request.fee_assessment_status = DocumentRequest.FeeAssessmentStatus.WAIVED
                    document_request.fee_assessed_by = request.user
                    document_request.fee_assessed_at = timezone.now()
                    document_request.fee_waiver_reason = waiver_reason
                    document_request.payment_status = DocumentRequest.PaymentStatus.NOT_REQUIRED
                    log_action(
                        user=request.user,
                        action_type=AuditLog.ActionType.DOCUMENT_ACTION,
                        description=(
                            f"Approved zero-fee waiver for document request #{document_request.id} ({document_request.document_type}). Reason: {waiver_reason}"
                        ),
                        request=self.request,
                    )

            if document_request.fee_amount <= 0:
                document_request.payment_method = ""
                document_request.payment_reference = ""
                document_request.payment_status = (
                    DocumentRequest.PaymentStatus.NOT_REQUIRED
                )
                document_request.payment_review_note = ""
                document_request.payment_recipient = None
                document_request.payment_recipient_name_snapshot = ""
                document_request.payment_recipient_identifier_snapshot = ""
                document_request.payment_instructions_snapshot = ""
                if document_request.payment_proof_image:
                    old_proof_name = document_request.payment_proof_image.name
                    storage = document_request.payment_proof_image.storage
                    document_request.payment_proof_image = None
                    document_request.payment_transacted_at = None
                    transaction.on_commit(
                        lambda s=storage, p=old_proof_name: safe_delete_storage_file(s, p)
                    )
            elif document_request.payment_status == (
                DocumentRequest.PaymentStatus.NOT_REQUIRED
            ):
                document_request.payment_status = (
                    DocumentRequest.PaymentStatus.UNPAID
                )

            if (
                document_request.is_walkin
                and document_request.fee_amount > 0
                and not document_request.payment_method
            ):
                # Walk-ins have no account to choose a method; collect their fee at the desk.
                document_request.payment_method = DocumentRequest.PaymentMethod.CASH

            if document_request.payment_method == DocumentRequest.PaymentMethod.CASH:
                document_request.payment_recipient = None
                document_request.payment_recipient_name_snapshot = ""
                document_request.payment_recipient_identifier_snapshot = ""
                document_request.payment_instructions_snapshot = ""
                document_request.payment_reference = ""
                if document_request.payment_proof_image:
                    old_proof_name = document_request.payment_proof_image.name
                    storage = document_request.payment_proof_image.storage
                    document_request.payment_proof_image = None
                    document_request.payment_transacted_at = None
                    transaction.on_commit(
                        lambda s=storage, p=old_proof_name: safe_delete_storage_file(s, p)
                    )

            validate_document_release_requirements(document_request)

            if (
                original_status == DocumentRequest.Status.RELEASED
                and document_request.status != DocumentRequest.Status.RELEASED
            ):
                revoked_count = DocumentCertificateVerification.objects.filter(
                    document_request=document_request,
                    revoked_at__isnull=True,
                ).update(revoked_at=timezone.now())
                if revoked_count:
                    log_action(
                        user=request.user,
                        action_type=AuditLog.ActionType.DOCUMENT_ACTION,
                        description=(
                            f"Revoked the certificate verification QR after document request "
                            f"#{document_request.pk} left the released status."
                        ),
                        request=request,
                    )

            document_request.save(
                update_fields=[
                    "fee_amount",
                    "fee_assessment_status",
                    "fee_assessed_by",
                    "fee_assessed_at",
                    "fee_waiver_reason",
                    "payment_method",
                    "payment_recipient",
                    "payment_recipient_name_snapshot",
                    "payment_recipient_identifier_snapshot",
                    "payment_instructions_snapshot",
                    "payment_reference",
                    "payment_proof_image",
                    "payment_transacted_at",
                    "payment_status",
                    "payment_review_note",
                    "updated_at",
                ]
            )
            if (
                original_status != DocumentRequest.Status.RELEASED
                and document_request.status == DocumentRequest.Status.RELEASED
            ):
                _resolve_active_pickup_tickets(
                    document_request,
                    actor=request.user,
                    request=request,
                )
            if document_request.user and document_request.status != original_status:
                display_status = document_request.get_status_display()
                ResidentNotification.objects.create(
                    user=document_request.user,
                    notification_type=ResidentNotification.Type.DOCUMENT,
                    title="Document request update",
                    message=(
                        f"Your {document_request.document_type} request is now {display_status}. "
                        "Open Documents to review the latest requirements and next steps."
                    ),
                    data={
                        "type": "document",
                        "document_request_id": str(document_request.pk),
                        "status": document_request.status,
                    },
                )
            recipient_desc = (
                document_request.user.username
                if document_request.user
                else document_request.walkin_name
            )

            log_action(
                user=request.user,
                action_type=AuditLog.ActionType.DOCUMENT_ACTION,
                description=(
                    f"Validated document request #{document_request.id} "
                    f"({document_request.document_type}) for {recipient_desc} "
                    f"as {document_request.get_status_display()}."
                ),
                request=request
            )

        if document_request.user and document_request.status != original_status:
            try:
                send_notification_to_user_task.delay(
                    user_id=document_request.user.id,
                    title="Document Request Update",
                    body=(
                        f"Your request for {document_request.document_type} is now "
                        f"{document_request.get_status_display()}."
                    ),
                    data={
                        "type": "document",
                        "request_id": str(document_request.id),
                    },
                )
            except Exception as exc:
                logger.warning(
                    "Could not queue document update notification (%s).",
                    type(exc).__name__,
                )

        return Response(
            DocumentRequestSerializer(document_request, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsResident],
        parser_classes=[MultiPartParser, FormParser, JSONParser],
        url_path="payment-reference",
        url_name="payment-reference",
    )
    def submit_payment_reference(self, request, pk=None):
        document_request = self.get_object()
        serializer = PaymentReferenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        old_proof_name = None
        old_storage = None
        new_saved_name = None
        new_storage = None

        try:
            with transaction.atomic():
                document_request = DocumentRequest.objects.select_for_update().get(
                    pk=document_request.pk,
                    user_id=request.user.id,
                )
                if document_request.status != DocumentRequest.Status.READY_FOR_PICKUP:
                    raise ValidationError({
                        "detail": "Payment details can be submitted after the document is ready."
                    })
                if document_request.fee_amount <= 0:
                    raise ValidationError({
                        "detail": "This request does not require a payment."
                    })
                if document_request.payment_status not in {
                    DocumentRequest.PaymentStatus.UNPAID,
                    DocumentRequest.PaymentStatus.REJECTED,
                }:
                    raise ValidationError({
                        "detail": "This payment is already awaiting review or verified."
                    })

                recipient = PaymentRecipient.objects.filter(
                    pk=serializer.validated_data["payment_recipient_id"],
                    barangay_id=document_request.barangay_id,
                    is_active=True,
                ).first()
                if recipient is None:
                    raise ValidationError({
                        "payment_recipient_id": "Select an active payment recipient configured by your barangay."
                    })

                if (
                    document_request.payment_method != recipient.provider
                    or document_request.payment_recipient_id != recipient.pk
                ):
                    raise ValidationError({
                        "payment_recipient_id": "Select this e-payment option as your payment method before submitting its transfer reference."
                    })

                if document_request.payment_proof_image and document_request.payment_proof_image.name:
                    old_proof_name = document_request.payment_proof_image.name
                    old_storage = document_request.payment_proof_image.storage

                document_request.payment_method = recipient.provider
                document_request.payment_recipient = recipient
                document_request.payment_recipient_name_snapshot = recipient.recipient_name
                document_request.payment_recipient_identifier_snapshot = recipient.recipient_identifier
                document_request.payment_instructions_snapshot = recipient.instructions
                document_request.payment_reference = serializer.validated_data[
                    "payment_reference"
                ]
                document_request.payment_transacted_at = serializer.validated_data[
                    "payment_transacted_at"
                ]
                proof_upload = serializer.validated_data["payment_proof_image"]
                document_request.payment_proof_image.save(
                    proof_upload.name,
                    proof_upload,
                    save=False,
                )
                new_saved_name = document_request.payment_proof_image.name
                new_storage = document_request.payment_proof_image.storage
                document_request.payment_status = (
                    DocumentRequest.PaymentStatus.PENDING_VERIFICATION
                )
                document_request.payment_review_note = ""
                document_request.save(
                    update_fields=[
                        "payment_method",
                        "payment_recipient",
                        "payment_recipient_name_snapshot",
                        "payment_recipient_identifier_snapshot",
                        "payment_instructions_snapshot",
                        "payment_reference",
                        "payment_transacted_at",
                        "payment_proof_image",
                        "payment_status",
                        "payment_review_note",
                        "updated_at",
                    ]
                )
                if old_proof_name and old_proof_name != new_saved_name and old_storage:
                    transaction.on_commit(
                        lambda s=old_storage, p=old_proof_name: safe_delete_storage_file(s, p)
                    )

                log_action(
                    user=request.user,
                    action_type=AuditLog.ActionType.DOCUMENT_ACTION,
                    description=(
                        f"Resident submitted a {document_request.get_payment_method_display()} "
                        f"reference for document request #{document_request.id}."
                    ),
                    request=request,
                )
        except Exception:
            if new_saved_name and new_saved_name != old_proof_name and new_storage:
                safe_delete_storage_file(new_storage, new_saved_name)
            raise

        return Response(
            DocumentRequestSerializer(document_request, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["patch"],
        permission_classes=[IsBarangayOfficial],
        url_path="payment-review",
        url_name="payment-review",
    )
    def review_payment(self, request, pk=None):
        document_request = self.get_object()
        user = request.user
        doc_barangay_id = document_request.barangay_id or (
            document_request.user.barangay_id if document_request.user else None
        )
        if not user.barangay_id or user.barangay_id != doc_barangay_id:
            raise Http404("Document request not found.")

        serializer = PaymentReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            document_request = DocumentRequest.objects.select_for_update().get(
                pk=document_request.pk
            )
            payment_status = serializer.validated_data["status"]
            note = serializer.validated_data.get("note", "").strip()

            if (
                payment_status == DocumentRequest.PaymentStatus.VERIFIED
                and document_request.payment_status == DocumentRequest.PaymentStatus.VERIFIED
                and document_request.or_number
            ):
                return Response(
                    DocumentRequestSerializer(
                        document_request,
                        context={"request": request},
                    ).data,
                    status=status.HTTP_200_OK,
                )

            if document_request.status != DocumentRequest.Status.READY_FOR_PICKUP:
                raise ValidationError({
                    "detail": "Payment can be confirmed only while the document is ready for pickup."
                })

            is_cash_payment = (
                document_request.payment_method == DocumentRequest.PaymentMethod.CASH
            )
            if is_cash_payment:
                can_confirm_cash = (
                    payment_status == DocumentRequest.PaymentStatus.VERIFIED
                    and document_request.payment_status in {
                        DocumentRequest.PaymentStatus.UNPAID,
                        DocumentRequest.PaymentStatus.REJECTED,
                    }
                )
                can_assign_missing_receipt = (
                    payment_status == DocumentRequest.PaymentStatus.VERIFIED
                    and document_request.payment_status == DocumentRequest.PaymentStatus.VERIFIED
                    and not document_request.or_number
                )
                if not (can_confirm_cash or can_assign_missing_receipt):
                    raise ValidationError({
                        "detail": "Confirm cash only after the Treasurer receives it, or assign the missing O.R. to a previously confirmed payment."
                    })
            else:
                is_supported_transfer = document_request.payment_method in {
                    DocumentRequest.PaymentMethod.GCASH,
                    DocumentRequest.PaymentMethod.MAYA,
                    DocumentRequest.PaymentMethod.BANK,
                    DocumentRequest.PaymentMethod.OTHER,
                }
                can_review_pending_transfer = (
                    is_supported_transfer
                    and document_request.payment_status
                    == DocumentRequest.PaymentStatus.PENDING_VERIFICATION
                )
                can_assign_missing_receipt = (
                    is_supported_transfer
                    and payment_status == DocumentRequest.PaymentStatus.VERIFIED
                    and document_request.payment_status
                    == DocumentRequest.PaymentStatus.VERIFIED
                    and not document_request.or_number
                )
                if not (can_review_pending_transfer or can_assign_missing_receipt):
                    raise ValidationError({
                        "detail": "Only a pending electronic transfer or a previously verified payment missing its O.R. can be reviewed."
                    })

            assigned_or_number = None
            if payment_status == DocumentRequest.PaymentStatus.VERIFIED:
                if document_request.fee_amount <= 0:
                    raise ValidationError({
                        "detail": "No receipt number is issued for a zero-fee request."
                    })
                assigned_or_number = assign_official_receipt_number(document_request)

            document_request.payment_status = payment_status
            document_request.payment_review_note = note

            update_fields = [
                "payment_status",
                "payment_review_note",
                "updated_at",
            ]
            if assigned_or_number:
                update_fields.append("or_number")

            document_request.save(update_fields=update_fields)
            log_action(
                user=request.user,
                action_type=AuditLog.ActionType.DOCUMENT_ACTION,
                description=(
                    f"Official {request.user.username} marked {document_request.get_payment_method_display()} "
                    f"payment for document request #{document_request.id} as {payment_status}."
                    + (f" Assigned O.R. {assigned_or_number}." if assigned_or_number else "")
                    + (f" Note: {note}" if note else "")
                ),
                request=request,
            )
        return Response(
            DocumentRequestSerializer(document_request, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=['get'],
        url_path='payment-proof',
        url_name='payment-proof',
    )
    def payment_proof(self, request, pk=None):
        user = request.user
        if not user or not user.is_authenticated:
            return Response(
                {"detail": "Authentication credentials were not provided."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        document_request = (
            DocumentRequest.objects.filter(pk=pk)
            .select_related("user", "barangay")
            .first()
        )
        if not document_request:
            raise Http404("Document request not found.")

        doc_barangay_id = document_request.barangay_id or (
            document_request.user.barangay_id if document_request.user else None
        )
        is_owner = bool(document_request.user_id is not None and user.id == document_request.user_id)
        is_same_barangay_staff = bool(
            user.role in (User.Role.ADMIN, User.Role.FIELD_OFFICIAL)
            and user.barangay_id is not None
            and doc_barangay_id is not None
            and user.barangay_id == doc_barangay_id
        )

        if not (is_owner or is_same_barangay_staff):
            raise Http404("Document request not found.")

        if not document_request.payment_proof_image or not document_request.payment_proof_image.name:
            raise Http404("No payment proof image available.")

        proof_field = document_request.payment_proof_image
        storage = proof_field.storage
        file_name = proof_field.name

        try:
            if hasattr(storage, "open_private_resident_media"):
                file_obj = storage.open_private_resident_media(file_name)
            else:
                file_obj = proof_field.open("rb")
        except (FileNotFoundError, IOError):
            raise Http404("Payment proof file could not be found.")

        try:
            with Image.open(file_obj) as proof_image:
                content_type = {
                    "JPEG": "image/jpeg",
                    "PNG": "image/png",
                    "WEBP": "image/webp",
                }.get(proof_image.format)
            file_obj.seek(0)
        except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError):
            file_obj.close()
            raise Http404("Payment proof image is invalid.")

        if content_type is None:
            file_obj.close()
            raise Http404("Payment proof image format is unsupported.")

        response = FileResponse(file_obj, content_type=content_type)
        response["Cache-Control"] = "private, no-store, max-age=0"
        response["X-Content-Type-Options"] = "nosniff"
        return response
    @action(
        detail=True,
        methods=["get", "post", "delete"],
        permission_classes=[IsBarangayOfficial],
        url_path="certificate-verification",
        url_name="certificate-verification",
    )
    def certificate_verification(self, request, pk=None):
        """Manage an opaque public verification token for a released paper certificate."""
        document_request = self.get_object()
        active_record = DocumentCertificateVerification.objects.filter(
            document_request=document_request,
            revoked_at__isnull=True,
        ).first()

        if request.method == "GET":
            if (
                active_record is None
                or document_request.status != DocumentRequest.Status.RELEASED
            ):
                return Response({"active": False}, status=status.HTTP_200_OK)
            return Response(
                self._certificate_verification_data(active_record),
                status=status.HTTP_200_OK,
            )

        if request.method == "DELETE":
            with transaction.atomic():
                DocumentRequest.objects.select_for_update().get(pk=document_request.pk)
                active_record = DocumentCertificateVerification.objects.select_for_update().filter(
                    document_request=document_request,
                    revoked_at__isnull=True,
                ).first()
                if active_record is not None:
                    active_record.revoked_at = timezone.now()
                    active_record.save(update_fields=["revoked_at"])
                    log_action(
                        user=request.user,
                        action_type=AuditLog.ActionType.DOCUMENT_ACTION,
                        description=(
                            f"Revoked the public verification QR for document request #{document_request.pk}."
                        ),
                        request=request,
                    )
            return Response({"active": False}, status=status.HTTP_200_OK)

        if document_request.status != DocumentRequest.Status.RELEASED:
            return Response(
                {"detail": "A verification QR is available only after the request is released."},
                status=status.HTTP_409_CONFLICT,
            )
        if request.data.get("confirm_paper_certificate_issued") is not True:
            raise ValidationError({
                "confirm_paper_certificate_issued": (
                    "Confirm that the Barangay has issued the paper certificate."
                )
            })

        with transaction.atomic():
            locked_request = DocumentRequest.objects.select_for_update().select_related("user").get(
                pk=document_request.pk
            )
            document_barangay_id = locked_request.barangay_id
            if document_barangay_id != request.user.barangay_id:
                raise Http404("Document request not found.")
            if locked_request.status != DocumentRequest.Status.RELEASED:
                return Response(
                    {"detail": "A verification QR is available only after the request is released."},
                    status=status.HTTP_409_CONFLICT,
                )

            active_record = DocumentCertificateVerification.objects.filter(
                document_request=locked_request,
                revoked_at__isnull=True,
            ).first()
            if active_record is None:
                try:
                    with transaction.atomic():
                        active_record = DocumentCertificateVerification.objects.create(
                            document_request=locked_request,
                            issued_by=request.user,
                        )
                except IntegrityError:
                    # Concurrent repeated clicks converge on the same active token.
                    active_record = DocumentCertificateVerification.objects.get(
                        document_request=locked_request,
                        revoked_at__isnull=True,
                    )
                else:
                    log_action(
                        user=request.user,
                        action_type=AuditLog.ActionType.DOCUMENT_ACTION,
                        description=(
                            f"Recorded issuance of a paper certificate and created a verification QR "
                            f"for document request #{locked_request.pk}."
                        ),
                        request=request,
                    )

        return Response(
            self._certificate_verification_data(active_record),
            status=status.HTTP_200_OK,
        )

    @staticmethod
    def _certificate_verification_data(record):
        token = str(record.token)
        return {
            "active": True,
            "token": token,
            "verification_url": (
                f"{settings.FRONTEND_URL.rstrip('/')}/verify-certificate/{token}"
            ),
            "issued_at": record.issued_at,
        }

    @action(detail=True, methods=['get'], url_path='generate-pdf')
    def generate_pdf(self, request, pk=None):
        document = self.get_object()
        if document.status != DocumentRequest.Status.RELEASED:
            return Response(
                {"detail": "The O.R. number PDF is available after the Barangay releases the request."},
                status=status.HTTP_409_CONFLICT,
            )
        if not document.or_number:
            return Response(
                {"detail": "The Barangay has not recorded an O.R. number for this request."},
                status=status.HTTP_409_CONFLICT,
            )

        template = get_template('gridy_services/pdf_or_number.html')
        html = template.render({'or_number': document.or_number})
        response = HttpResponse(content_type='application/pdf')
        safe_filename = re.sub(r'[^A-Za-z0-9_-]', '_', document.or_number)[:50] or f'request_{document.id}'
        response['Content-Disposition'] = f'attachment; filename="OR_{safe_filename}.pdf"'
        response['Cache-Control'] = 'private, no-store, max-age=0'
        response['X-Content-Type-Options'] = 'nosniff'
        pisa_status = pisa.CreatePDF(html, dest=response)

        if pisa_status.err:
            return Response({"detail": "Failed to generate the O.R. number PDF."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return response
