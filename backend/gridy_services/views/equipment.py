import logging
from django.db import transaction
from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError

from gridy_audit.models import AuditLog
from gridy_audit.services import log_action
from gridy_auth.models import User
from gridy_auth.permissions import IsBarangayOfficial, IsResident
from gridy_communications.models import AdminNotification, ResidentNotification
from gridy_communications.tasks import send_notification_to_user_task
from gridy_services.models import EquipmentBorrowRequest
from gridy_services.serializers import (
    EquipmentBorrowRequestReviewSerializer,
    EquipmentBorrowRequestSerializer,
)

logger = logging.getLogger(__name__)


class EquipmentBorrowRequestViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return EquipmentBorrowRequest.objects.none()

        queryset = EquipmentBorrowRequest.objects.none()
        if user.role == User.Role.ADMIN and user.barangay_id:
            queryset = EquipmentBorrowRequest.objects.filter(
                barangay_id=user.barangay_id
            ).select_related("resident", "resident__profile", "reviewed_by")
        elif user.role == User.Role.RESIDENT:
            queryset = EquipmentBorrowRequest.objects.filter(
                resident_id=user.id
            ).select_related("resident", "resident__profile", "reviewed_by")

        status_filter = (self.request.query_params.get("status") or "").strip().upper()
        if status_filter in EquipmentBorrowRequest.Status.values:
            queryset = queryset.filter(status=status_filter)

        return queryset.order_by("-created_at", "-id")

    def get_permissions(self):
        if self.action == "create":
            return [IsResident()]
        if self.action in ("update", "partial_update"):
            return [IsBarangayOfficial()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.action in ("update", "partial_update"):
            return EquipmentBorrowRequestReviewSerializer
        return EquipmentBorrowRequestSerializer

    def perform_create(self, serializer):
        user = self.request.user
        if user.barangay_id is None:
            raise PermissionDenied(
                "Your account must be assigned to a barangay before borrowing equipment."
            )
        if not hasattr(user, "profile") or not user.profile.is_verified:
            raise PermissionDenied(
                "Your resident account must be verified before borrowing equipment."
            )
        with transaction.atomic():
            instance = serializer.save(
                resident=user,
                barangay_id=user.barangay_id,
                status=EquipmentBorrowRequest.Status.PENDING,
                admin_notes="",
                reviewed_by=None,
                reviewed_at=None,
                returned_at=None,
            )
            admin_ids = User.objects.filter(
                role=User.Role.ADMIN,
                barangay_id=user.barangay_id,
                is_active=True,
            ).values_list("id", flat=True)
            AdminNotification.objects.bulk_create([
                AdminNotification(
                    user_id=admin_id,
                    notification_type=AdminNotification.Type.SYSTEM,
                    title="New equipment borrowing request",
                    message=(
                        f"A resident submitted a request to borrow "
                        f"{instance.item_type} (x{instance.quantity})."
                    ),
                )
                for admin_id in admin_ids
            ])
            log_action(
                user=user,
                action_type=AuditLog.ActionType.USER_ACTION,
                description=(
                    f"Resident {user.username} submitted equipment borrow "
                    f"request #{instance.id} for {instance.item_type} (x{instance.quantity})."
                ),
                request=self.request,
            )

    def perform_update(self, serializer):
        request = self.request
        allowed_transitions = {
            EquipmentBorrowRequest.Status.PENDING: {
                EquipmentBorrowRequest.Status.APPROVED,
                EquipmentBorrowRequest.Status.DECLINED,
            },
            EquipmentBorrowRequest.Status.APPROVED: {
                EquipmentBorrowRequest.Status.RETURNED,
            },
            EquipmentBorrowRequest.Status.DECLINED: set(),
            EquipmentBorrowRequest.Status.RETURNED: set(),
        }
        status_changed = False
        with transaction.atomic():
            instance = EquipmentBorrowRequest.objects.select_for_update().get(
                pk=serializer.instance.pk,
                barangay_id=request.user.barangay_id,
            )
            previous_status = instance.status
            next_status = serializer.validated_data.get("status", previous_status)
            if previous_status in {
                EquipmentBorrowRequest.Status.DECLINED,
                EquipmentBorrowRequest.Status.RETURNED,
            }:
                raise ValidationError({
                    "status": "Completed or declined borrowing requests cannot be edited."
                })
            if next_status != previous_status and next_status not in (
                allowed_transitions[previous_status]
            ):
                raise ValidationError({
                    "status": (
                        f"Cannot transition borrowing request from "
                        f"{previous_status} to {next_status}."
                    )
                })

            now = timezone.now()
            extra_save_kwargs = {}
            if next_status != previous_status:
                status_changed = True
                extra_save_kwargs["reviewed_by"] = request.user
                if next_status in {
                    EquipmentBorrowRequest.Status.APPROVED,
                    EquipmentBorrowRequest.Status.DECLINED,
                }:
                    extra_save_kwargs["reviewed_at"] = now
                elif next_status == EquipmentBorrowRequest.Status.RETURNED:
                    extra_save_kwargs["returned_at"] = now
                    if instance.reviewed_at is None:
                        extra_save_kwargs["reviewed_at"] = now

            serializer.instance = instance
            instance = serializer.save(**extra_save_kwargs)

            if status_changed and instance.resident_id:
                display_status = instance.get_status_display()
                ResidentNotification.objects.create(
                    user=instance.resident,
                    notification_type=ResidentNotification.Type.DOCUMENT,
                    title="Equipment borrowing request update",
                    message=(
                        f"Your borrowing request for {instance.item_type} is now "
                        f"{display_status}."
                    ),
                    data={
                        "type": "equipment",
                        "equipment_request_id": str(instance.pk),
                        "status": instance.status,
                    },
                )

            if status_changed or "admin_notes" in serializer.validated_data:
                log_action(
                    user=request.user,
                    action_type=AuditLog.ActionType.USER_ACTION,
                    description=(
                        f"Official {request.user.username} reviewed equipment "
                        f"borrow request #{instance.id}: {previous_status} to "
                        f"{instance.status}."
                    ),
                    request=request,
                )

        if status_changed and instance.resident_id:
            try:
                send_notification_to_user_task.delay(
                    user_id=instance.resident_id,
                    title="Equipment Borrowing Update",
                    body=(
                        f"Your borrowing request for {instance.item_type} is now "
                        f"{instance.get_status_display()}."
                    ),
                    data={
                        "type": "equipment",
                        "equipment_request_id": str(instance.pk),
                        "status": instance.status,
                    },
                )
            except Exception as exc:
                logger.warning(
                    "Could not queue equipment borrowing notification (%s).",
                    type(exc).__name__,
                )
