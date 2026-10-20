import csv
import io
import logging
import uuid
from datetime import datetime
from django.db import transaction
from django.db.transaction import atomic as import_atomic
from django.shortcuts import get_object_or_404
from rest_framework import status, permissions, viewsets
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from drf_spectacular.utils import extend_schema, OpenApiTypes

from gridy_auth.models import User, Resident
from gridy_auth.serializers import (
    ResidentAdminUpdateSerializer,
    ResidentSerializer,
)
from gridy_auth.permissions import IsBarangayOfficial
from gridy_auth.lifecycle import erase_user_account
from gridy_audit.services import log_action
from gridy_audit.models import AuditLog

from rest_framework import serializers

from rest_framework.exceptions import PermissionDenied

logger = logging.getLogger(__name__)

MAX_RESIDENT_IMPORT_SIZE_BYTES = 5 * 1024 * 1024
MAX_RESIDENT_IMPORT_ROWS = 1000

class FileUploadSerializer(serializers.Serializer):
    file = serializers.FileField(help_text="CSV file containing resident accounts to import.")

class ResidentImportResponseSerializer(serializers.Serializer):
    imported = serializers.IntegerField(help_text="Number of residents successfully imported.")
    skipped_due_to_duplicate = serializers.IntegerField(help_text="Number of records skipped due to pre-existing username.")
    errors = serializers.ListField(child=serializers.CharField(), help_text="List of validation error messages.")

class ResidentRejectionSerializer(serializers.Serializer):
    rejection_reason = serializers.CharField(
        max_length=1000,
        allow_blank=False,
        trim_whitespace=True,
    )

@extend_schema(
    summary="Bulk Import Residents from CSV",
    description=(
        "Bulk imports residents from a historical Registry of Barangay Inhabitants (RBI) "
        "CSV file (Barangay Official only). Unlike resident self-service registration, "
        "historical RBI records do not require uploaded proof images; the authorized official's "
        "import serves as an administrative residency attestation. Imported resident accounts "
        "are assigned to the official's barangay, marked as pre-verified (is_verified=True), "
        "and provisioned without usable passwords. Durably logs audit provenance linked to the "
        "importing official, the CSV file, and the imported resident records."
    ),
    request={
        'multipart/form-data': FileUploadSerializer
    },
    responses={
        200: ResidentImportResponseSerializer,
        207: ResidentImportResponseSerializer,
        400: OpenApiTypes.OBJECT,
        403: OpenApiTypes.OBJECT,
        413: OpenApiTypes.OBJECT,
        429: OpenApiTypes.OBJECT,
    }
)

class ResidentImportView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsBarangayOfficial]
    parser_classes = [MultiPartParser, FormParser]
    throttle_scope = "resident_import"

    def post(self, request, *args, **kwargs):
        if request.user.barangay_id is None:
            raise PermissionDenied("A barangay assignment is required to import residents.")

        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({"detail": "No file was uploaded"}, status=status.HTTP_400_BAD_REQUEST)
        if not file_obj.name.endswith('.csv'):
            return Response({"detail": "File is not a CSV."}, status=status.HTTP_400_BAD_REQUEST)
        if file_obj.size > MAX_RESIDENT_IMPORT_SIZE_BYTES:
            return Response(
                {"detail": "The CSV file exceeds the 5 MiB upload limit."},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )

        try:
            decoded_file = file_obj.read().decode('utf-8')
            io_string = io.StringIO(decoded_file)
            rows = []
            for row_idx, row in enumerate(csv.DictReader(io_string), start=1):
                if row_idx > MAX_RESIDENT_IMPORT_ROWS:
                    return Response(
                        {"detail": "The CSV file exceeds the 1,000 resident row limit."},
                        status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    )
                rows.append(row)
        except Exception:
            logger.exception("Failed to read uploaded resident import file.")
            return Response(
                {"detail": "The uploaded resident file could not be read."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        imported_count = 0
        skipped_count = 0
        errors = []
        imported_records = []
        batch_id = str(uuid.uuid4())

        try:
            with import_atomic():
                for row_idx, row in enumerate(rows, start=1):
                    # Sanitize inputs by stripping whitespace
                    username = (row.get('username') or '').strip()
                    email = (row.get('email') or '').strip().lower()
                    full_name = (row.get('full_name') or '').strip()
                    birth_date_str = (row.get('birth_date') or '').strip()
                    contact_number = (row.get('contact_number') or '').strip()
                    purok = (row.get('purok') or '').strip()
                    voter_status_str = (row.get('voter_status') or 'False').strip().lower()
                    
                    if not username or not full_name or not birth_date_str:
                        errors.append(f"Row {row_idx}: Missing required fields ('username', 'full_name', 'birth_date').")
                        continue

                    # Fallback date parsing for robust sanitization
                    birth_date = None
                    for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%m-%d-%Y'):
                        try:
                            birth_date = datetime.strptime(birth_date_str, fmt).date()
                            break
                        except ValueError:
                            pass

                    if not birth_date:
                        errors.append(f"Row {row_idx}: Invalid date format for '{birth_date_str}'. Expected YYYY-MM-DD or MM/DD/YYYY.")
                        continue

                    if User.objects.filter(username=username).exists():
                        skipped_count += 1
                        continue

                    if email and User.objects.filter(email__iexact=email).exists():
                        errors.append(f"Row {row_idx}: Email '{email}' is already in use by another resident.")
                        continue

                    voter_status = voter_status_str in ['true', '1', 'yes']
                    
                    # 1. Create User bound strictly to the importing official's Barangay
                    user = User.objects.create_user(
                        username=username, 
                        email=email, 
                        password=None,
                        role=User.Role.RESIDENT,
                        barangay=request.user.barangay
                    )

                    # 2. Create Resident Profile pre-verified from official Census / RBI records
                    resident = Resident.objects.create(
                        user=user, 
                        full_name=full_name, 
                        birth_date=birth_date,
                        voter_status=voter_status, 
                        contact_number=contact_number,
                        purok=purok if purok else None,
                        is_verified=True
                    )
                    imported_records.append((user, resident))
                    imported_count += 1

                if imported_records:
                    barangay_name = request.user.barangay.name
                    barangay_id = request.user.barangay_id
                    resident_ids_str = ", ".join(str(r.id) for _, r in imported_records)
                    log_action(
                        user=request.user,
                        action_type=AuditLog.ActionType.USER_ACTION,
                        description=(
                            f"Administrative RBI attestation batch {batch_id}: imported {len(imported_records)} "
                            f"pre-verified resident(s) from CSV '{file_obj.name}' into Barangay {barangay_name} "
                            f"(ID: {barangay_id}). Resident IDs: {resident_ids_str}."
                        ),
                        request=request,
                    )
                    for u, r in imported_records:
                        log_action(
                            user=request.user,
                            action_type=AuditLog.ActionType.USER_ACTION,
                            description=(
                                f"Administrative RBI attestation: imported and verified resident account "
                                f"for {r.full_name} (ID: {r.id}, Username: {u.username}) in Barangay {barangay_name} "
                                f"(ID: {barangay_id}) from CSV '{file_obj.name}' (Batch: {batch_id})."
                            ),
                            request=request,
                        )
        except Exception:
            logger.exception("Resident CSV import transaction failed.")
            return Response(
                {"detail": "Resident import could not be completed."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        response_data = {
            "imported": imported_count,
            "skipped_due_to_duplicate": skipped_count,
            "errors": errors
        }

        if errors:
            return Response(response_data, status=status.HTTP_207_MULTI_STATUS)
        return Response(response_data, status=status.HTTP_200_OK)

def _get_barangay_scoped_resident_or_404(user, pk, *, pending_only=False):
    if user.barangay_id is None:
        raise PermissionDenied("Your account is not assigned to a barangay.")
    residents = Resident.objects.select_related("user").filter(
        user__barangay_id=user.barangay_id
    )
    if pending_only:
        residents = residents.filter(is_verified=False).select_for_update()

    return get_object_or_404(residents, pk=pk)

class PendingResidentsView(ListAPIView):
    permission_classes = [permissions.IsAuthenticated, IsBarangayOfficial]
    serializer_class = ResidentSerializer

    def get_queryset(self):
        user = self.request.user
        return (
            Resident.objects.filter(
                is_verified=False,
                user__barangay_id=user.barangay_id,
            )
            .select_related("user")
            .order_by("-user__date_joined", "-pk")
        )


class VerifyResidentView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsBarangayOfficial]

    @extend_schema(summary="Verify a resident account", responses={200: ResidentSerializer, 404: OpenApiTypes.OBJECT})
    def patch(self, request, pk):
        with transaction.atomic():
            resident = _get_barangay_scoped_resident_or_404(
                request.user,
                pk,
                pending_only=True,
            )
            resident.is_verified = True
            resident.save(update_fields=["is_verified"])

            log_action(
                user=request.user,
                action_type=AuditLog.ActionType.USER_ACTION,
                description=(
                    f"Verified resident account for {resident.full_name} "
                    f"(ID: {resident.id})."
                ),
                request=request,
            )

        return Response(ResidentSerializer(resident).data, status=status.HTTP_200_OK)

class RejectResidentView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsBarangayOfficial]

    @extend_schema(
        summary="Reject and delete a pending resident account",
        request=ResidentRejectionSerializer,
        responses={
            204: None,
            400: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
    )
    def delete(self, request, pk):
        reason_serializer = ResidentRejectionSerializer(data=request.data)
        reason_serializer.is_valid(raise_exception=True)
        rejection_reason = reason_serializer.validated_data["rejection_reason"]

        with transaction.atomic():
            resident = _get_barangay_scoped_resident_or_404(
                request.user,
                pk,
                pending_only=True,
            )
            resident_name = resident.full_name
            resident_id = resident.id
            resident_user = resident.user

            erase_user_account(
                user=resident_user,
                reason=(
                    f"Rejected pending resident account for {resident_name} "
                    f"(ID: {resident_id}). Reason: {rejection_reason}"
                ),
                request=request,
                actor=request.user,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)

class ResidentViewSet(viewsets.ModelViewSet):
    """Directory endpoint for verified residents. Supports list, retrieve, update, and delete."""
    http_method_names = ["get", "put", "patch", "delete", "head", "options"]
    permission_classes = [permissions.IsAuthenticated, IsBarangayOfficial]
    serializer_class = ResidentSerializer

    def get_serializer_class(self):
        if self.action in ("update", "partial_update"):
            return ResidentAdminUpdateSerializer
        return ResidentSerializer

    def perform_update(self, serializer):
        email_update = "email" in serializer.validated_data.get("user", {})

        with transaction.atomic():
            resident = serializer.save()

            if email_update:
                log_action(
                    user=self.request.user,
                    action_type=AuditLog.ActionType.USER_ACTION,
                    description=(
                        "Updated the login email for resident account "
                        f"(ID: {resident.id})."
                    ),
                    request=self.request,
                )

    def perform_destroy(self, instance):
        resident_name = instance.full_name
        resident_id = instance.id
        resident_user = instance.user

        erase_user_account(
            user=resident_user,
            reason=(
                f"Removed resident account for {resident_name} "
                f"(ID: {resident_id})"
            ),
            request=self.request,
            actor=self.request.user,
        )

    def get_queryset(self):
        user = self.request.user
        return Resident.objects.filter(is_verified=True, user__barangay=user.barangay).select_related('user').order_by('full_name')
