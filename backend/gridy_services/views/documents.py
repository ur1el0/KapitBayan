from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Q
from django.template.loader import get_template
from django.http import FileResponse, Http404, HttpResponse
from PIL import Image, UnidentifiedImageError
from django.utils import timezone
from xhtml2pdf import pisa
from gridy_auth.models import User
from gridy_auth.permissions import (
    IsBarangayOfficial,
    IsBarangayOfficialOrField,
    IsResident,
    IsResidentOrBarangayOfficial,
)
from gridy_services.models import DocumentRequest, DocumentServiceOffering, PaymentRecipient
from gridy_services.signals import safe_delete_storage_file
from gridy_services.serializers import (
    DocumentRequestSerializer,
    DocumentRequestReviewSerializer,
    PaymentReferenceSerializer,
    PaymentReviewSerializer,
)
from gridy_communications.tasks import send_notification_to_user_task
from gridy_communications.admin_notifications import notify_barangay_admins
from decimal import Decimal
from gridy_audit.services import log_action
from gridy_audit.models import AuditLog
from rest_framework.exceptions import PermissionDenied, ValidationError
from ..fee_policy import FEE_EXEMPT_DOCUMENT_TYPES, check_ra11261_eligibility

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

class DocumentRequestViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentRequestSerializer
    
    def get_permissions(self):
        # Authenticated users can list, view, and download their own approved PDFs or payment proof
        if self.action in ['list', 'retrieve', 'generate_pdf', 'payment_proof']:
            return [permissions.IsAuthenticated()]

        if self.action == "submit_payment_reference":
            return [permissions.IsAuthenticated(), IsResident()]

        if self.action == "create":
            return [
                permissions.IsAuthenticated(),
                IsResidentOrBarangayOfficial(),
            ]
        
        # Allow authenticated users to access destroy (role and status checks enforced in perform_destroy)
        if self.action == 'destroy':
            return [permissions.IsAuthenticated()]

        if self.action in ["review_payment", "validate"]:
            return [permissions.IsAuthenticated(), IsBarangayOfficialOrField()]

        return [IsBarangayOfficial()]

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return DocumentRequest.objects.none()
        
        # The request's barangay is authoritative; only legacy null-barangay
        # digital requests fall back to the resident's current barangay.
        if user.role in [User.Role.ADMIN, User.Role.FIELD_OFFICIAL]:
            if user.barangay_id is None:
                return DocumentRequest.objects.none()
            return DocumentRequest.objects.filter(
                Q(barangay_id=user.barangay_id)
                | Q(
                    barangay_id__isnull=True,
                    is_walkin=False,
                    user__barangay_id=user.barangay_id,
                )
            ).select_related("offering").order_by('-created_at')

        # Residents see only their own requests
        return DocumentRequest.objects.filter(user=user).select_related(
            "offering"
        ).order_by('-created_at')

    @transaction.atomic
    def perform_create(self, serializer):
        user = self.request.user
        data = serializer.validated_data
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

        if hasattr(user, "profile") and not user.profile.is_verified:
            raise PermissionDenied(
                "Your account is currently pending verification. Please verify "
                "your residency with Barangay Hall before requesting clearances."
            )

        doc_type_clean = " ".join((data.get("document_type") or "").split()).casefold()
        is_statutory = doc_type_clean in FEE_EXEMPT_DOCUMENT_TYPES

        serializer.save(
            user=user,
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
        
        # 1. Citizen Resident Self-Service Cancellation
        if user.role == User.Role.RESIDENT:
            if instance.user != user:
                raise PermissionDenied("You can only cancel your own document requests.")
            
            if instance.status != DocumentRequest.Status.PENDING:
                raise ValidationError(
                    {"detail": "You can only cancel document requests that are still pending review."}
                )
            
            log_action(
                user=user,
                action_type=AuditLog.ActionType.DOCUMENT_ACTION,
                description=f"Resident {user.username} cancelled pending document request #{instance.id} ({instance.document_type}).",
                request=self.request
            )
            instance.delete()
            return

        # 2. Barangay Official Administrative Deletion
        if user.role in [User.Role.ADMIN, User.Role.FIELD_OFFICIAL]:
            if instance.status not in [DocumentRequest.Status.RELEASED, DocumentRequest.Status.REJECTED]:
                raise ValidationError(
                    {"detail": "Only resolved (released or rejected) clearance requests can be deleted by officials."}
                )

            recipient_desc = instance.user.username if instance.user else (instance.walkin_name or "Resident")
            log_action(
                user=user,
                action_type=AuditLog.ActionType.DOCUMENT_ACTION,
                description=f"Deleted {instance.get_status_display().lower()} document request #{instance.id} ({instance.document_type}) for {recipient_desc}.",
                request=self.request
            )
            instance.delete()
            return

        raise PermissionDenied("You do not have permission to delete this document request.")

    @action(detail=True, methods=['patch'], permission_classes=[IsBarangayOfficialOrField])
    def validate(self, request, pk=None):
        with transaction.atomic():
            document_request = DocumentRequest.objects.select_for_update().get(
                pk=self.get_object().pk
            )
            initial_fee_assessment_status = document_request.fee_assessment_status
            serializer = DocumentRequestReviewSerializer(
                document_request,
                data=request.data,
                partial=True,
            )
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

            if document_request.status in (DocumentRequest.Status.READY_FOR_PICKUP, DocumentRequest.Status.RELEASED):
                if document_request.fee_assessment_status == DocumentRequest.FeeAssessmentStatus.AWAITING_ASSESSMENT:
                    raise ValidationError({
                        "fee_assessment_status": "Document fee must be assessed or explicitly waived before marking ready for pickup."
                    })

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

            if document_request.status == DocumentRequest.Status.RELEASED:
                if document_request.fee_amount > 0 and (
                    not document_request.or_number or not document_request.or_number.strip()
                ):
                    raise ValidationError({
                        "or_number": (
                            "An official receipt number is required before release."
                        )
                    })
                if document_request.fee_amount > 0:
                    if document_request.payment_method == DocumentRequest.PaymentMethod.CASH:
                        document_request.payment_status = DocumentRequest.PaymentStatus.VERIFIED
                    elif document_request.payment_method in {
                        DocumentRequest.PaymentMethod.GCASH,
                        DocumentRequest.PaymentMethod.MAYA,
                        DocumentRequest.PaymentMethod.BANK,
                        DocumentRequest.PaymentMethod.OTHER,
                    }:
                        if document_request.payment_status != DocumentRequest.PaymentStatus.VERIFIED:
                            raise ValidationError({
                                "payment_status": (
                                    "Verify the transfer before releasing this document."
                                )
                            })
                    else:
                        raise ValidationError({
                            "payment_method": "Record cash or a verified electronic transfer."
                        })

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

        if document_request.user:
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
        permission_classes=[IsBarangayOfficialOrField],
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
            if (
                document_request.payment_method not in {
                    DocumentRequest.PaymentMethod.GCASH,
                    DocumentRequest.PaymentMethod.MAYA,
                    DocumentRequest.PaymentMethod.BANK,
                    DocumentRequest.PaymentMethod.OTHER,
                }
                or document_request.payment_status
                != DocumentRequest.PaymentStatus.PENDING_VERIFICATION
            ):
                raise ValidationError({
                    "detail": "Only pending electronic transfer references can be reviewed."
                })

            payment_status = serializer.validated_data["status"]
            note = serializer.validated_data.get("note", "").strip()
            document_request.payment_status = payment_status
            document_request.payment_review_note = note

            update_fields = [
                "payment_status",
                "payment_review_note",
                "updated_at",
            ]
            if "or_number" in serializer.validated_data:
                or_number_val = serializer.validated_data["or_number"].strip()
                if or_number_val:
                    document_request.or_number = or_number_val
                    update_fields.append("or_number")

            document_request.save(
                update_fields=update_fields
            )
            log_action(
                user=request.user,
                action_type=AuditLog.ActionType.DOCUMENT_ACTION,
                description=(
                    f"Official {request.user.username} marked {document_request.get_payment_method_display()} "
                    f"payment for document request #{document_request.id} as {payment_status}."
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

    @action(detail=True, methods=['get'], url_path='generate-pdf')
    def generate_pdf(self, request, pk=None):
        document = self.get_object()
        
        if document.status not in [DocumentRequest.Status.PROCESSING, DocumentRequest.Status.READY_FOR_PICKUP, DocumentRequest.Status.RELEASED]:
            return Response(
                {"error": "You cannot generate PDFs for pending or rejected documents."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        template_path = 'gridy_services/pdf_clearance.html'
        resident = (
            document.user.profile
            if document.user_id and hasattr(document.user, 'profile')
            else None
        )
        barangay = document.barangay

        if barangay is None and document.user_id:
            barangay = document.user.barangay

        if barangay is None:
            raise ValidationError({
                "detail": "A barangay must be assigned before generating this PDF."
            })

        # Calculate age if birth_date is present
        age = None
        if resident and resident.birth_date:
            today = timezone.now().date()
            age = today.year - resident.birth_date.year - ((today.month, today.day) < (resident.birth_date.month, resident.birth_date.day))
        
        recipient_name = resident.full_name if resident else (document.walkin_name or "RESIDENT")
        if resident:
            purok_name = f"Purok {resident.purok}" if resident.purok else "N/A"
        else:
            purok_name = document.walkin_purok or "N/A"

        context = {
            'document': document,
            'resident': resident,
            'recipient_name': recipient_name,
            'purok_name': purok_name,
            'barangay': barangay,
            'office_contact': self._pdf_office_contact(barangay.office_contact),
            'age': age,
            'date_issued': timezone.now()
        }
        
        # Create a Django response object with application/pdf content_type
        response = HttpResponse(content_type='application/pdf')
        safe_filename = document.document_type.replace(' ', '_')
        response['Content-Disposition'] = f'attachment; filename="{safe_filename}_{document.id}.pdf"'
        
        # Render the template to HTML, then convert HTML to PDF
        template = get_template(template_path)
        html = template.render(context)
        
        pisa_status = pisa.CreatePDF(html, dest=response)
        
        if pisa_status.err:
            return Response({"error": "Failed to generate PDF"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        return response

    @staticmethod
    def _pdf_office_contact(value):
        contact = (value or "").strip()
        if not contact or ("{{" in contact and "}}" in contact):
            return "Office of the Punong Barangay"
        return contact
