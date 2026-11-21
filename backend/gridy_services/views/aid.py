from django.db import transaction
from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError

from gridy_audit.models import AuditLog
from gridy_audit.services import log_action
from gridy_auth.models import User
from gridy_auth.permissions import IsBarangayOfficial, IsResident
from gridy_services.models import AidRequest
from gridy_services.serializers import (
    AidRequestReviewSerializer,
    AidRequestSerializer,
)


class AidRequestViewSet(viewsets.ModelViewSet):
    lookup_value_regex = r"\d+"
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return AidRequest.objects.none()
        if user.role == User.Role.ADMIN and user.barangay_id:
            return AidRequest.objects.filter(barangay_id=user.barangay_id)
        if user.role == User.Role.RESIDENT:
            return AidRequest.objects.filter(requester_id=user.id)
        return AidRequest.objects.none()

    def get_permissions(self):
        if self.action == "create":
            return [IsResident()]
        if self.action in ("update", "partial_update"):
            return [IsBarangayOfficial()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.action in ("update", "partial_update"):
            return AidRequestReviewSerializer
        return AidRequestSerializer

    def perform_create(self, serializer):
        user = self.request.user
        if user.barangay_id is None:
            raise PermissionDenied(
                "Your account must be assigned to a barangay before requesting assistance."
            )
        if not hasattr(user, "profile") or not user.profile.is_verified:
            raise PermissionDenied(
                "Your resident account must be verified before requesting assistance."
            )
        serializer.save(requester=user, barangay_id=user.barangay_id)

    def perform_update(self, serializer):
        request = self.request
        allowed_transitions = {
            AidRequest.Status.PENDING: {
                AidRequest.Status.UNDER_REVIEW,
                AidRequest.Status.APPROVED,
                AidRequest.Status.DECLINED,
            },
            AidRequest.Status.UNDER_REVIEW: {
                AidRequest.Status.APPROVED,
                AidRequest.Status.DECLINED,
            },
            AidRequest.Status.APPROVED: set(),
            AidRequest.Status.DECLINED: set(),
        }
        with transaction.atomic():
            instance = AidRequest.objects.select_for_update().get(
                pk=serializer.instance.pk,
                barangay_id=request.user.barangay_id,
            )
            previous_status = instance.status
            next_status = serializer.validated_data.get("status", previous_status)
            if previous_status in {
                AidRequest.Status.APPROVED,
                AidRequest.Status.DECLINED,
            }:
                raise ValidationError({
                    "status": "Decided assistance requests cannot be edited."
                })
            if next_status != previous_status and next_status not in (
                allowed_transitions[previous_status]
            ):
                raise ValidationError({
                    "status": "This assistance request has already been decided."
                })
            serializer.instance = instance
            instance = serializer.save(
                reviewed_by=request.user
                if next_status != previous_status
                else instance.reviewed_by
            )
            if previous_status != instance.status or "staff_notes" in serializer.validated_data:
                log_action(
                    user=request.user,
                    action_type=AuditLog.ActionType.USER_ACTION,
                    description=(
                        f"Official {request.user.username} reviewed assistance "
                        f"request #{instance.id}: {previous_status} to "
                        f"{instance.status}."
                    ),
                    request=request,
                )
