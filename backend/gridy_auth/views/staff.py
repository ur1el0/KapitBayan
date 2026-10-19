from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.db import transaction
import uuid
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from gridy_audit.models import AuditLog
from gridy_audit.services import log_action
from gridy_auth.models import RefreshSession, User
from gridy_auth.serializers.staff import (
    StaffUserCreateSerializer,
    StaffUserListSerializer,
    StaffUserUpdateSerializer,
)
from gridy_auth.tasks import send_field_official_setup_email


class IsAssignedBarangayAdmin(permissions.BasePermission):
    """Allow Field Official management only to admins assigned to a Barangay."""

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.role == User.Role.ADMIN
            and user.barangay_id is not None
        )


@extend_schema(tags=["Staff Management"])
class StaffManagementViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    Management of Field Officials by their assigned Barangay Admin.
    Admin account creation and listing are reserved for platform operators.
    """
    permission_classes = [permissions.IsAuthenticated, IsAssignedBarangayAdmin]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "staff_management"

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated or user.role != User.Role.ADMIN or not user.barangay_id:
            return User.objects.none()
        return (
            User.objects.filter(
                barangay_id=user.barangay_id,
                role=User.Role.FIELD_OFFICIAL,
            )
            .order_by("-date_joined")
        )

    def get_serializer_class(self):
        if self.action == "create":
            return StaffUserCreateSerializer
        if self.action in {"update", "partial_update"}:
            return StaffUserUpdateSerializer
        return StaffUserListSerializer

    @extend_schema(
        summary="List Barangay Field Officials",
        description="Returns all active and inactive Field Officials belonging to the authenticated Admin's Barangay.",
        responses={200: StaffUserListSerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Onboard New Field Official",
        description="Creates a new Field Official bound to the authenticated Admin's Barangay.",
        request=StaffUserCreateSerializer,
        responses={
            201: StaffUserListSerializer,
            400: OpenApiResponse(description="Validation error or duplicate credentials."),
            403: OpenApiResponse(description="Restricted to Barangay Admins with assigned Barangay."),
        },
    )
    def create(self, request, *args, **kwargs):
        if not request.user.barangay:
            return Response(
                {"detail": "Administrator is not assigned to an active Barangay."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            user = User(
                username=f"field-official-{uuid.uuid4().hex}",
                email=data["email"].strip().lower(),
                first_name=data["first_name"],
                last_name=data["last_name"],
                role=User.Role.FIELD_OFFICIAL,
                barangay=request.user.barangay,
                is_staff=False,
                is_active=True,
            )
            user.set_unusable_password()
            user.save()

            log_action(
                user=request.user,
                action_type=AuditLog.ActionType.USER_ACTION,
                description=f"Admin {request.user.email} created a Field Official account for Barangay {request.user.barangay.name}.",
                request=request,
            )

            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            setup_link = (
                f"{settings.FRONTEND_URL.rstrip('/')}/set-password"
                f"?uidb64={uid}&token={token}"
            )
            transaction.on_commit(
                lambda email=user.email, full_name=user.get_full_name(),
                barangay_name=request.user.barangay.name, link=setup_link:
                    send_field_official_setup_email.delay(
                        email,
                        full_name,
                        barangay_name,
                        link,
                    )
            )

        read_serializer = StaffUserListSerializer(user)
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Update Field Official Profile",
        description=(
            "Updates a Field Official's first name, last name, and/or email. "
            "The target must belong to the authenticated Admin's Barangay. "
            "Sign-in email, role, Barangay, password, and privilege fields cannot be changed here."
        ),
        request=StaffUserUpdateSerializer,
        responses={
            200: StaffUserListSerializer,
            400: OpenApiResponse(description="Invalid profile fields or disallowed request fields."),
            404: OpenApiResponse(description="Field Official not found in administrator's Barangay."),
        },
    )
    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        response.data = StaffUserListSerializer(self.get_object()).data
        return response

    @extend_schema(
        summary="Partially Update Field Official Profile",
        description=(
            "Updates a Field Official's first name, last name, and/or email. "
            "The target must belong to the authenticated Admin's Barangay. "
            "Sign-in email, role, Barangay, password, and privilege fields cannot be changed here."
        ),
        request=StaffUserUpdateSerializer,
        responses={
            200: StaffUserListSerializer,
            400: OpenApiResponse(description="Invalid profile fields or disallowed request fields."),
            404: OpenApiResponse(description="Field Official not found in administrator's Barangay."),
        },
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    def perform_update(self, serializer):
        target = serializer.instance
        changed_fields = sorted(serializer.validated_data)
        with transaction.atomic():
            serializer.save()
            log_action(
                user=self.request.user,
                action_type=AuditLog.ActionType.USER_ACTION,
                description=(
                    f"Admin {self.request.user.email} updated profile fields "
                    f"{', '.join(changed_fields)} for Field Official account ID {target.pk}."
                ),
                request=self.request,
            )

    @extend_schema(
        summary="Toggle Field Official Active Status",
        description="Activates or deactivates a Field Official. Deactivating immediately revokes all active refresh sessions.",
        request=None,
        responses={
            200: StaffUserListSerializer,
            404: OpenApiResponse(description="Field Official not found in administrator's Barangay."),
        },
    )
    @action(detail=True, methods=["post"], url_path="toggle-status")
    def toggle_status(self, request, pk=None):
        with transaction.atomic():
            user = self.get_object()
            user.is_active = not user.is_active
            user.save(update_fields=["is_active"])

            if not user.is_active:
                RefreshSession.objects.filter(user=user, is_revoked=False).update(is_revoked=True)

            action_word = "activated" if user.is_active else "deactivated"
            log_action(
                user=request.user,
                action_type=AuditLog.ActionType.USER_ACTION,
                description=f"Admin {request.user.email} {action_word} Field Official account {user.email}.",
                request=request,
            )

        serializer = StaffUserListSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)
