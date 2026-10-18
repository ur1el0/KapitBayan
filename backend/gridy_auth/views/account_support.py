import logging

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from gridy_audit.models import AuditLog
from gridy_audit.services import log_action
from gridy_auth.models import Barangay, RefreshSession, User
from gridy_auth.permissions import IsDILGAdmin
from gridy_auth.serializers.account_support import (
    ACCOUNT_SUPPORT_ROLES,
    DILGAccountActiveStateSerializer,
    DILGAccountDirectoryQuerySerializer,
    DILGAccountEmailCorrectionSerializer,
    DILGAccountRecoveryLinkSerializer,
    DILGAccountSummarySerializer,
)
from gridy_auth.tasks import send_password_reset_email
from gridy_auth.throttling import SharedDatabaseScopedRateThrottle

logger = logging.getLogger(__name__)


def _dispatch_recovery_link(user_id):
    """Queue a private setup/reset link without exposing its token to the caller."""
    try:
        user = User.objects.get(
            pk=user_id,
            role__in=ACCOUNT_SUPPORT_ROLES,
            is_superuser=False,
        )
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_link = (
            f"{settings.FRONTEND_URL.rstrip('/')}/reset-password"
            f"?uidb64={uid}&token={token}"
        )
        send_password_reset_email.delay(user.email, reset_link)
    except User.DoesNotExist:
        logger.error("Account recovery dispatch skipped for an unavailable account.")
    except Exception as exc:
        logger.error("Account recovery dispatch failed (%s).", type(exc).__name__)


@extend_schema(tags=["DILG Account Support"])
class DILGAccountSupportViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Limited DILG recovery and active-state support for barangay accounts."""

    permission_classes = [permissions.IsAuthenticated, IsDILGAdmin]
    throttle_classes = [SharedDatabaseScopedRateThrottle]
    throttle_scope = "dilg_account_support"
    serializer_class = DILGAccountSummarySerializer
    http_method_names = ["get", "patch", "post", "head", "options"]

    def get_queryset(self):
        actor = getattr(self.request, "user", None)
        if not actor or not actor.is_authenticated or actor.role != User.Role.DILG_ADMIN:
            return User.objects.none()
        # Write actions must scope row locks to User: these optional joins
        # otherwise make PostgreSQL reject FOR UPDATE on nullable join sides.
        return (
            User.objects.filter(
                role__in=ACCOUNT_SUPPORT_ROLES,
                is_superuser=False,
            )
            .select_related("barangay", "profile")
            .order_by("barangay__province", "barangay__municipality", "barangay__name", "username")
        )

    def get_serializer_class(self):
        if self.action == "partial_update":
            return DILGAccountEmailCorrectionSerializer
        if self.action == "send_password_link":
            return DILGAccountRecoveryLinkSerializer
        if self.action == "set_active":
            return DILGAccountActiveStateSerializer
        return DILGAccountSummarySerializer

    @extend_schema(
        summary="Search barangay accounts for DILG support",
        parameters=[DILGAccountDirectoryQuerySerializer],
        responses={200: DILGAccountSummarySerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        query_data = {
            key: request.query_params[key]
            for key in ("search", "role", "active")
            if key in request.query_params
        }
        query_serializer = DILGAccountDirectoryQuerySerializer(data=query_data)
        query_serializer.is_valid(raise_exception=True)
        filters = query_serializer.validated_data

        queryset = self.filter_queryset(self.get_queryset())
        if search := filters.get("search"):
            queryset = queryset.filter(
                Q(username__icontains=search)
                | Q(email__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(profile__full_name__icontains=search)
            )
        if role := filters.get("role"):
            queryset = queryset.filter(role=role)
        if "active" in filters:
            queryset = queryset.filter(is_active=filters["active"])

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = DILGAccountSummarySerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = DILGAccountSummarySerializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Correct a barangay account email and send a secure setup/reset link",
        request=DILGAccountEmailCorrectionSerializer,
        responses={200: DILGAccountSummarySerializer, 400: OpenApiResponse(description="Invalid email, reason, or verification attestation"), 404: OpenApiResponse(description="Account not found or not eligible")},
    )
    @transaction.atomic
    def partial_update(self, request, *args, **kwargs):
        target = get_object_or_404(
            self.get_queryset().select_for_update(of=("self",)),
            pk=kwargs["pk"],
        )
        serializer = DILGAccountEmailCorrectionSerializer(
            data=request.data,
            context={"target": target},
        )
        serializer.is_valid(raise_exception=True)

        target.email = serializer.validated_data["email"]
        target.save(update_fields=["email"])
        RefreshSession.objects.filter(user=target, is_revoked=False).update(is_revoked=True)
        self._log_action(
            request,
            target,
            action="email corrected and recovery link requested",
            reason=serializer.validated_data["reason"],
            contact_verified=True,
        )
        transaction.on_commit(lambda account_id=target.pk: _dispatch_recovery_link(account_id))
        return Response(DILGAccountSummarySerializer(target).data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Send a private setup/reset link to the verified account email",
        request=DILGAccountRecoveryLinkSerializer,
        responses={202: OpenApiResponse(description="Recovery email dispatch requested"), 400: OpenApiResponse(description="Contact verification and reason are required"), 404: OpenApiResponse(description="Account not found or not eligible")},
    )
    @action(detail=True, methods=["post"], url_path="send-password-link")
    @transaction.atomic
    def send_password_link(self, request, pk=None):
        target = get_object_or_404(
            self.get_queryset().select_for_update(of=("self",)),
            pk=pk,
        )
        serializer = DILGAccountRecoveryLinkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        matching_email_accounts = User.objects.filter(email__iexact=target.email).count()
        if not target.email or matching_email_accounts != 1:
            raise ValidationError({
                "email": "This account must have a unique email before a recovery link can be sent."
            })

        self._log_action(
            request,
            target,
            action="setup/reset link dispatch requested",
            reason=serializer.validated_data["reason"],
            contact_verified=True,
        )
        transaction.on_commit(lambda account_id=target.pk: _dispatch_recovery_link(account_id))
        return Response(
            {"detail": "If email delivery is available, a private setup/reset link will be sent to the verified account email."},
            status=status.HTTP_202_ACCEPTED,
        )

    @extend_schema(
        summary="Activate or deactivate a barangay account",
        request=DILGAccountActiveStateSerializer,
        responses={200: DILGAccountSummarySerializer, 400: OpenApiResponse(description="Invalid state or last active barangay administrator guard"), 404: OpenApiResponse(description="Account not found or not eligible")},
    )
    @action(detail=True, methods=["post"], url_path="set-active")
    @transaction.atomic
    def set_active(self, request, pk=None):
        candidate = get_object_or_404(self.get_queryset(), pk=pk)
        # Lock the tenant row first so concurrent changes cannot disable two
        # administrators after each request observed the same pre-change count.
        if candidate.barangay_id is not None:
            get_object_or_404(Barangay.objects.select_for_update(), pk=candidate.barangay_id)
        target = get_object_or_404(
            self.get_queryset().select_for_update(of=("self",)),
            pk=pk,
        )
        serializer = DILGAccountActiveStateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_active_state = serializer.validated_data["is_active"]
        reason = serializer.validated_data["reason"]

        if new_active_state == target.is_active:
            return Response(DILGAccountSummarySerializer(target).data)

        if not new_active_state and target.role == User.Role.ADMIN and target.barangay_id is not None:
            active_admin_count = User.objects.filter(
                barangay_id=target.barangay_id,
                role=User.Role.ADMIN,
                is_active=True,
                is_superuser=False,
            ).count()
            if active_admin_count <= 1:
                raise ValidationError({
                    "is_active": "The last active administrator for a barangay cannot be disabled."
                })

        target.is_active = new_active_state
        target.save(update_fields=["is_active"])
        if not new_active_state:
            RefreshSession.objects.filter(user=target, is_revoked=False).update(is_revoked=True)

        self._log_action(
            request,
            target,
            action="account activated" if new_active_state else "account deactivated",
            reason=reason,
        )
        return Response(DILGAccountSummarySerializer(target).data)

    @staticmethod
    def _log_action(request, target, *, action, reason, contact_verified=False):
        verification_note = " External contact verification was attested." if contact_verified else ""
        log_action(
            user=request.user,
            action_type=AuditLog.ActionType.USER_ACTION,
            description=(
                f"DILG account support: {action}; target account ID={target.pk}; "
                f"role={target.role}; barangay ID={target.barangay_id or 'unassigned'}; "
                f"reason={reason}.{verification_note}"
            ),
            request=request,
        )
