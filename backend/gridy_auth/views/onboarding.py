from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from gridy_audit.models import AuditLog
from gridy_audit.services import log_action
from gridy_auth.models import Barangay, BarangayApplication, User
from gridy_auth.permissions import IsDjangoSuperuser
from gridy_auth.serializers.onboarding import (
    BarangayApplicationApproveSerializer,
    BarangayApplicationCreateSerializer,
    BarangayApplicationOperatorSerializer,
    BarangayApplicationReceiptSerializer,
    BarangayApplicationRejectSerializer,
    PublicBarangaySerializer,
)
from gridy_auth.tasks import send_barangay_admin_setup_email
from gridy_auth.throttling import SharedDatabaseScopedRateThrottle


@extend_schema(tags=["Barangay Directory"])
class PublicBarangayDirectoryView(APIView):
    """List existing Barangays so residents can select their jurisdiction."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(responses=PublicBarangaySerializer(many=True))
    def get(self, request):
        barangays = Barangay.objects.all().order_by("province", "municipality", "name")
        return Response(PublicBarangaySerializer(barangays, many=True).data)


@extend_schema(tags=["Barangay Onboarding"])
class PublicBarangayApplicationCreateView(APIView):
    """Accept an application only; provisioning waits for platform review."""

    permission_classes = [permissions.AllowAny]
    throttle_classes = [SharedDatabaseScopedRateThrottle]
    throttle_scope = "barangay_onboarding_application"

    @extend_schema(
        summary="Submit a new Barangay onboarding application",
        request=BarangayApplicationCreateSerializer,
        responses={
            201: BarangayApplicationReceiptSerializer,
            400: OpenApiResponse(description="Invalid application details."),
            429: OpenApiResponse(description="Application request limit reached."),
        },
    )
    def post(self, request):
        serializer = BarangayApplicationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                application = serializer.save()
        except IntegrityError:
            return Response(
                {"detail": "A matching pending application already exists. Contact KapitBayan support if you need help."},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            BarangayApplicationReceiptSerializer(application).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Platform Barangay Onboarding"])
class PlatformBarangayApplicationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Let platform operators review requests and provision first Admins."""

    permission_classes = [permissions.IsAuthenticated, IsDjangoSuperuser]
    throttle_classes = [SharedDatabaseScopedRateThrottle]
    throttle_scope = "platform_account_support"
    serializer_class = BarangayApplicationOperatorSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        user = getattr(self.request, "user", None)
        if not user or not user.is_authenticated or not user.is_superuser:
            return BarangayApplication.objects.none()
        return BarangayApplication.objects.select_related(
            "reviewed_by", "created_barangay", "created_admin"
        ).order_by("-created_at", "-pk")

    def list(self, request, *args, **kwargs):
        selected_status = request.query_params.get("status", BarangayApplication.Status.PENDING)
        valid_statuses = {choice for choice, _label in BarangayApplication.Status.choices}
        if selected_status not in valid_statuses:
            return Response(
                {"status": "Select PENDING, APPROVED, or REJECTED."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        queryset = self.filter_queryset(self.get_queryset().filter(status=selected_status))
        page = self.paginate_queryset(queryset)
        if page is not None:
            return self.get_paginated_response(
                BarangayApplicationOperatorSerializer(page, many=True).data
            )
        return Response(BarangayApplicationOperatorSerializer(queryset, many=True).data)

    @extend_schema(
        summary="Approve a verified Barangay application and provision its first Admin",
        request=BarangayApplicationApproveSerializer,
        responses={
            200: BarangayApplicationOperatorSerializer,
            400: OpenApiResponse(description="Verification attestation or application state is invalid."),
            403: OpenApiResponse(description="Restricted to active Django superusers."),
            409: OpenApiResponse(description="A matching tenant/Admin or account conflict prevents provisioning."),
        },
    )
    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        serializer = BarangayApplicationApproveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application_id = pk
        try:
            with transaction.atomic():
                application = BarangayApplication.objects.select_for_update().get(pk=application_id)
                if application.status != BarangayApplication.Status.PENDING:
                    return Response(
                        {"detail": "Only pending applications can be approved."},
                        status=status.HTTP_409_CONFLICT,
                    )

                username = application.admin_username.strip().lower()
                email = application.applicant_email.strip().lower()
                if not username:
                    return Response(
                        {"detail": "This older application has no proposed Admin username. Ask the official to submit a new application with a username."},
                        status=status.HTTP_409_CONFLICT,
                    )
                if User.objects.filter(username__iexact=username).exists():
                    return Response(
                        {"admin_username": "This username is already in use. Reject the application with a note asking the official to submit another username."},
                        status=status.HTTP_409_CONFLICT,
                    )
                if User.objects.filter(email__iexact=email).exists():
                    return Response(
                        {"applicant_email": "This email address is already tied to an account. Ask the official to submit a different verified email, or resolve the existing account through Platform Account Support."},
                        status=status.HTTP_409_CONFLICT,
                    )

                locality_matches = list(
                    Barangay.objects.select_for_update()
                    .filter(name__iexact=application.name)
                    .filter(
                        (Q(municipality__iexact=application.municipality) | Q(municipality=""))
                        & (Q(province__iexact=application.province) | Q(province=""))
                    )
                    .order_by("pk")
                )
                if len(locality_matches) > 1:
                    return Response(
                        {"detail": "Several Barangay records match this locality. Resolve the duplicate records before approving this application."},
                        status=status.HTTP_409_CONFLICT,
                    )

                barangay = locality_matches[0] if locality_matches else None
                if barangay and User.objects.filter(
                    barangay=barangay,
                    role=User.Role.ADMIN,
                    is_superuser=False,
                ).exists():
                    return Response(
                        {"detail": "This Barangay already has an Admin account. Use the existing Barangay's staff-management flow instead."},
                        status=status.HTTP_409_CONFLICT,
                    )

                if barangay is None:
                    barangay = Barangay.objects.create(
                        name=application.name.strip(),
                        municipality=application.municipality.strip(),
                        province=application.province.strip(),
                    )
                else:
                    changed_fields = []
                    if not barangay.municipality:
                        barangay.municipality = application.municipality.strip()
                        changed_fields.append("municipality")
                    if not barangay.province:
                        barangay.province = application.province.strip()
                        changed_fields.append("province")
                    if changed_fields:
                        barangay.save(update_fields=changed_fields)

                admin = User(
                    username=username,
                    email=email,
                    first_name=application.applicant_name.strip(),
                    role=User.Role.ADMIN,
                    barangay=barangay,
                    is_staff=True,
                    is_superuser=False,
                    is_active=True,
                )
                admin.set_unusable_password()
                admin.save()

                application.status = BarangayApplication.Status.APPROVED
                application.review_note = serializer.validated_data.get("review_note", "").strip()
                application.reviewed_by = request.user
                application.reviewed_at = timezone.now()
                application.review_verified = True
                application.created_barangay = barangay
                application.created_admin = admin
                application.save(update_fields=[
                    "status", "review_note", "reviewed_by", "reviewed_at",
                    "review_verified", "created_barangay", "created_admin", "updated_at",
                ])

                log_action(
                    user=request.user,
                    action_type=AuditLog.ActionType.USER_ACTION,
                    description=(
                        f"Platform operator approved Barangay application #{application.pk}, "
                        f"provisioning Barangay #{barangay.pk} and first Admin account #{admin.pk}."
                    ),
                    request=request,
                )

                uid = urlsafe_base64_encode(force_bytes(admin.pk))
                token = default_token_generator.make_token(admin)
                setup_link = (
                    f"{settings.FRONTEND_URL.rstrip('/')}/set-password"
                    f"?uidb64={uid}&token={token}"
                )
                transaction.on_commit(
                    lambda email=admin.email, name=application.applicant_name,
                    barangay_name=barangay.name, link=setup_link:
                        send_barangay_admin_setup_email.delay(
                            email, name, barangay_name, link
                        )
                )
        except BarangayApplication.DoesNotExist:
            return Response({"detail": "Application not found."}, status=status.HTTP_404_NOT_FOUND)
        except IntegrityError:
            return Response(
                {"detail": "A conflicting Barangay or account record was created while this application was being reviewed. Refresh the queue and inspect the matching records."},
                status=status.HTTP_409_CONFLICT,
            )

        application.refresh_from_db()
        return Response(BarangayApplicationOperatorSerializer(application).data)

    @extend_schema(
        summary="Reject a Barangay onboarding application with a recorded reason",
        request=BarangayApplicationRejectSerializer,
        responses={
            200: BarangayApplicationOperatorSerializer,
            400: OpenApiResponse(description="A rejection reason is required or application state is invalid."),
            403: OpenApiResponse(description="Restricted to active Django superusers."),
            409: OpenApiResponse(description="Only pending applications can be rejected."),
        },
    )
    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, pk=None):
        serializer = BarangayApplicationRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                application = BarangayApplication.objects.select_for_update().get(pk=pk)
                if application.status != BarangayApplication.Status.PENDING:
                    return Response(
                        {"detail": "Only pending applications can be rejected."},
                        status=status.HTTP_409_CONFLICT,
                    )

                application.status = BarangayApplication.Status.REJECTED
                application.review_note = serializer.validated_data["reason"].strip()
                application.reviewed_by = request.user
                application.reviewed_at = timezone.now()
                application.review_verified = False
                application.save(update_fields=[
                    "status", "review_note", "reviewed_by", "reviewed_at",
                    "review_verified", "updated_at",
                ])

                log_action(
                    user=request.user,
                    action_type=AuditLog.ActionType.USER_ACTION,
                    description=f"Platform operator rejected Barangay application #{application.pk} with a recorded reason.",
                    request=request,
                )
        except BarangayApplication.DoesNotExist:
            return Response({"detail": "Application not found."}, status=status.HTTP_404_NOT_FOUND)

        return Response(BarangayApplicationOperatorSerializer(application).data)
