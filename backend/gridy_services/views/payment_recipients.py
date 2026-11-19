from django.db import IntegrityError, transaction
from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError

from gridy_audit.models import AuditLog
from gridy_audit.services import log_action
from gridy_auth.models import User
from gridy_auth.permissions import IsBarangayOfficial, IsResidentOrBarangayOfficial
from gridy_services.models import PaymentRecipient
from gridy_services.payment_serializers import PaymentRecipientSerializer


class PaymentRecipientViewSet(viewsets.ModelViewSet):
    lookup_value_regex = r"\d+"
    serializer_class = PaymentRecipientSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.IsAuthenticated(), IsResidentOrBarangayOfficial()]
        return [permissions.IsAuthenticated(), IsBarangayOfficial()]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated or user.role not in (User.Role.ADMIN, User.Role.RESIDENT):
            return PaymentRecipient.objects.none()

        queryset = PaymentRecipient.objects.filter(barangay_id=user.barangay_id)
        if user.role == User.Role.RESIDENT:
            queryset = queryset.filter(is_active=True)
        return queryset

    @transaction.atomic
    def perform_create(self, serializer):
        user = self.request.user
        if not user.barangay_id:
            raise PermissionDenied("Your account must belong to a barangay to manage payment recipients.")
        try:
            with transaction.atomic():
                recipient = serializer.save(barangay=user.barangay)
        except IntegrityError as exc:
            raise ValidationError({
                "display_name": "A payment recipient with this provider and display name already exists for your barangay."
            }) from exc
        log_action(
            user=user,
            action_type=AuditLog.ActionType.USER_ACTION,
            description=(
                f"Configured payment recipient #{recipient.pk} "
                f"({recipient.get_provider_display()}) for barangay ID {user.barangay_id}."
            ),
            request=self.request,
        )

    @transaction.atomic
    def perform_update(self, serializer):
        user = self.request.user
        try:
            with transaction.atomic():
                recipient = serializer.save()
        except IntegrityError as exc:
            raise ValidationError({
                "display_name": "A payment recipient with this provider and display name already exists for your barangay."
            }) from exc
        log_action(
            user=user,
            action_type=AuditLog.ActionType.USER_ACTION,
            description=(
                f"Updated payment recipient #{recipient.pk} "
                f"({recipient.get_provider_display()}) for barangay ID {user.barangay_id}. "
                f"Active: {recipient.is_active}."
            ),
            request=self.request,
        )
