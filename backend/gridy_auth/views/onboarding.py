from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from datetime import timedelta
from urllib.parse import quote, urlencode

from gridy_audit.models import AuditLog
from gridy_audit.services import log_action
from gridy_auth.lifecycle import (
    attempt_private_media_cleanup_safely,
    erase_user_account,
    queue_private_media_cleanup,
)
from gridy_auth.models import Barangay, BarangayApplication, User
from gridy_auth.permissions import IsBarangayOnboardingReviewer
from gridy_auth.serializers.onboarding import (
    BarangayApplicationApproveSerializer,
    BarangayApplicationCreateSerializer,
    BarangayApplicationEmailVerificationSerializer,
    BarangayApplicationErasureSerializer,
    BarangayApplicationOperatorSerializer,
    BarangayApplicationReceiptSerializer,
    BarangayApplicationRejectSerializer,
    BarangayApplicationVerificationResendSerializer,
    PublicBarangaySerializer,
)
from gridy_auth.tasks import (
    send_barangay_admin_setup_email,
    send_barangay_application_verification_email,
)
from gridy_auth.tokens import barangay_application_email_token_generator
from gridy_auth.throttling import SharedDatabaseScopedRateThrottle


@extend_schema(tags=["Barangay Directory"])
class PublicBarangayDirectoryView(APIView):
    """List approved Barangays so residents can select their jurisdiction."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(responses=PublicBarangaySerializer(many=True))
    def get(self, request):
        barangays = Barangay.get_eligible_for_registration()
        return Response(PublicBarangaySerializer(barangays, many=True).data)


@extend_schema(tags=["Barangay Onboarding"])
class PublicBarangayApplicationCreateView(APIView):
    """Accept a request and inactive applicant account; activation waits for review."""

    permission_classes = [permissions.AllowAny]
    throttle_classes = [SharedDatabaseScopedRateThrottle]
    throttle_scope = "barangay_onboarding_application"
    parser_classes = [MultiPartParser, FormParser]

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
                _schedule_barangay_application_verification(application)
        except IntegrityError:
            return Response(
                {"detail": "A matching pending application already exists. Contact KapitBayan support if you need help."},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            BarangayApplicationReceiptSerializer(application).data,
            status=status.HTTP_201_CREATED,
        )


def _schedule_barangay_application_verification(application):
    applicant = application.applicant_user
    if applicant is None:
        return
    token = barangay_application_email_token_generator.make_token(applicant)
    application_query = urlencode({"application": application.pk})
    verification_url = (
        f"{settings.FRONTEND_URL.rstrip('/')}/verify-barangay-email"
        f"?{application_query}#token={quote(token, safe='')}"
    )
    transaction.on_commit(
        lambda email=application.applicant_email,
        name=application.applicant_name,
        barangay_name=application.name,
        link=verification_url: send_barangay_application_verification_email.delay(
            email, name, barangay_name, link
        )
    )


@extend_schema(tags=["Barangay Onboarding"])
class PublicBarangayApplicationEmailVerificationView(APIView):
    """Verify email ownership after an explicit POST from the applicant."""

    permission_classes = [permissions.AllowAny]
    throttle_classes = [SharedDatabaseScopedRateThrottle]
    throttle_scope = "barangay_onboarding_verification"
    parser_classes = [JSONParser]

    @extend_schema(
        summary="Verify the official email for a pending Barangay application",
        request=BarangayApplicationEmailVerificationSerializer,
        responses={
            200: OpenApiResponse(description="Email verified; Barangay Operator review is still required."),
            400: OpenApiResponse(description="The verification link is invalid, expired, or already used."),
            404: OpenApiResponse(description="Application not found."),
            429: OpenApiResponse(description="Verification request limit reached."),
        },
    )
    def post(self, request, application_id):
        serializer = BarangayApplicationEmailVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                application = (
                    BarangayApplication.objects.select_for_update(of=("self",))
                    .select_related("applicant_user")
                    .get(pk=application_id)
                )
                applicant = application.applicant_user
                if application.email_verified_at is not None:
                    return Response(
                        {"detail": "This verification link is invalid, expired, or already used."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if (
                    application.status != BarangayApplication.Status.PENDING
                    or applicant is None
                    or applicant.is_active
                    or not barangay_application_email_token_generator.check_token(
                        applicant, serializer.validated_data["token"]
                    )
                ):
                    return Response(
                        {"detail": "This verification link is invalid or expired. Request a new link and try again."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                application.email_verified_at = timezone.now()
                application.save(update_fields=["email_verified_at", "updated_at"])
        except BarangayApplication.DoesNotExist:
            return Response({"detail": "Application not found."}, status=status.HTTP_404_NOT_FOUND)

        return Response({"detail": "Email verified. The application still requires Barangay Operator review."})


@extend_schema(tags=["Barangay Onboarding"])
class PublicBarangayApplicationVerificationResendView(APIView):
    """Resend a pending applicant's link without exposing account existence."""

    permission_classes = [permissions.AllowAny]
    throttle_classes = [SharedDatabaseScopedRateThrottle]
    throttle_scope = "barangay_onboarding_verification"
    parser_classes = [JSONParser]
    COOLDOWN = timedelta(minutes=10)

    @extend_schema(
        summary="Request another email verification link",
        request=BarangayApplicationVerificationResendSerializer,
        responses={
            202: OpenApiResponse(description="A generic response is returned whether or not a link was sent."),
            400: OpenApiResponse(description="Invalid request fields."),
            429: OpenApiResponse(description="Verification request limit reached."),
        },
    )
    def post(self, request):
        serializer = BarangayApplicationVerificationResendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application_id = serializer.validated_data["application_id"]
        email = serializer.validated_data["applicant_email"]

        with transaction.atomic():
            application = (
                BarangayApplication.objects.select_for_update(of=("self",))
                .select_related("applicant_user")
                .filter(
                    pk=application_id,
                    applicant_email__iexact=email,
                    status=BarangayApplication.Status.PENDING,
                    email_verified_at__isnull=True,
                )
                .first()
            )
            now = timezone.now()
            if (
                application is not None
                and application.applicant_user is not None
                and (
                    application.email_verification_sent_at is None
                    or application.email_verification_sent_at <= now - self.COOLDOWN
                )
            ):
                application.email_verification_sent_at = now
                application.save(update_fields=["email_verification_sent_at", "updated_at"])
                _schedule_barangay_application_verification(application)

        return Response(
            {"detail": "If this application is pending and needs email verification, a new link will be sent when eligible."},
            status=status.HTTP_202_ACCEPTED,
        )


@extend_schema(tags=["Barangay Onboarding Review"])
class PlatformBarangayApplicationProofView(APIView):
    """Stream pending authority proof only to authorized onboarding reviewers."""

    permission_classes = [permissions.IsAuthenticated, IsBarangayOnboardingReviewer]
    throttle_classes = [SharedDatabaseScopedRateThrottle]
    throttle_scope = "platform_account_support"

    @extend_schema(
        summary="Download pending Barangay application authority proof",
        responses={
            200: OpenApiResponse(description="Private authority document download."),
            403: OpenApiResponse(description="Restricted to active Barangay Operators and Django superusers."),
            404: OpenApiResponse(description="Application or pending proof not found."),
        },
    )
    def get(self, request, application_id):
        application = BarangayApplication.objects.filter(
            pk=application_id,
            status=BarangayApplication.Status.PENDING,
        ).first()
        if application is None or not application.proof_of_authority:
            raise Http404("Private application proof not found.")

        proof = application.proof_of_authority
        file_name = proof.name
        extension = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
        content_types = {"pdf": "application/pdf", "jpg": "image/jpeg", "png": "image/png"}
        content_type = content_types.get(extension)
        if content_type is None:
            raise Http404("Private application proof not found.")

        try:
            storage = proof.storage
            if hasattr(storage, "open_private_media"):
                file_handle = storage.open_private_media(file_name, "rb")
            elif hasattr(storage, "open_private_resident_media"):
                file_handle = storage.open_private_resident_media(file_name, "rb")
            else:
                file_handle = storage.open(file_name, "rb")
        except (FileNotFoundError, OSError):
            raise Http404("Private application proof not found.")

        response = FileResponse(
            file_handle,
            as_attachment=True,
            filename=f"barangay-authority-proof-{application.pk}.{extension}",
            content_type=content_type,
        )
        response["Cache-Control"] = "private, no-store, max-age=0"
        response["X-Content-Type-Options"] = "nosniff"
        response["Referrer-Policy"] = "no-referrer"
        return response


@extend_schema(tags=["Barangay Onboarding Review"])
class PlatformBarangayApplicationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Let Barangay Operators or controlled superusers review new Barangays."""

    permission_classes = [permissions.IsAuthenticated, IsBarangayOnboardingReviewer]
    throttle_classes = [SharedDatabaseScopedRateThrottle]
    throttle_scope = "platform_account_support"
    serializer_class = BarangayApplicationOperatorSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        user = getattr(self.request, "user", None)
        if not user or not user.is_authenticated or not (
            user.is_superuser or user.role == User.Role.BARANGAY_OPERATOR
        ):
            return BarangayApplication.objects.none()
        return BarangayApplication.objects.select_related(
            "reviewed_by", "created_barangay", "created_admin", "applicant_user"
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
        summary="Approve a verified Barangay application and activate its applicant Admin",
        request=BarangayApplicationApproveSerializer,
        responses={
            200: BarangayApplicationOperatorSerializer,
            400: OpenApiResponse(description="Verification attestation or application state is invalid."),
            403: OpenApiResponse(description="Restricted to active Barangay Operators and Django superusers."),
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

                email = application.applicant_email.strip().lower()
                admin = None
                applicant = application.applicant_user
                if applicant is not None:
                    applicant = User.objects.select_for_update().get(pk=applicant.pk)
                    if application.email_verified_at is None:
                        return Response(
                            {"detail": "The applicant must verify the official email before approval."},
                            status=status.HTTP_409_CONFLICT,
                        )
                    if not application.proof_of_authority:
                        return Response(
                            {"detail": "A pending authority document is required before approval."},
                            status=status.HTTP_409_CONFLICT,
                        )
                    if not serializer.validated_data["proof_reviewed"]:
                        return Response(
                            {"proof_reviewed": "Confirm that you reviewed the uploaded authority document."},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    if (
                        applicant.is_active
                        or applicant.role != User.Role.ADMIN
                        or applicant.barangay_id is not None
                        or applicant.is_staff
                        or applicant.is_superuser
                        or not applicant.has_usable_password()
                        or applicant.email.strip().casefold() != email.casefold()
                    ):
                        return Response(
                            {"detail": "The linked applicant account is no longer in the expected pending state. Resolve it manually before approval."},
                            status=status.HTTP_409_CONFLICT,
                        )
                    account_conflict = User.objects.filter(
                        Q(email__iexact=email) | Q(username__iexact=email)
                    ).exclude(pk=applicant.pk).exists()
                    if account_conflict:
                        return Response(
                            {"applicant_email": "This email address is now tied to another account. Resolve the account conflict before approval."},
                            status=status.HTTP_409_CONFLICT,
                        )
                    admin = applicant
                else:
                    # Preserve the former setup-link approval flow for historical applications.
                    username = application.admin_username.strip().lower()
                    if not username:
                        return Response(
                            {"detail": "This historical application has no linked applicant account or Admin username. Ask the official to submit a new application."},
                            status=status.HTTP_409_CONFLICT,
                        )
                    if User.objects.filter(username__iexact=username).exists():
                        return Response(
                            {"admin_username": "This historical Admin username is already in use. Resolve the account conflict before approval."},
                            status=status.HTTP_409_CONFLICT,
                        )
                    if User.objects.filter(
                        Q(email__iexact=email) | Q(username__iexact=email)
                    ).exists():
                        return Response(
                            {"applicant_email": "This email address is already tied to an account. Resolve the account conflict before approval."},
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

                if applicant is not None:
                    admin.barangay = barangay
                    admin.is_staff = True
                    admin.is_superuser = False
                    admin.is_active = True
                    admin.first_name = application.applicant_name.strip()
                    admin.save(update_fields=[
                        "barangay", "is_staff", "is_superuser", "is_active", "first_name",
                    ])
                else:
                    admin = User.objects.create_user(
                        username=username,
                        email=email,
                        first_name=application.applicant_name.strip(),
                        password=None,
                        role=User.Role.ADMIN,
                        barangay=barangay,
                        is_staff=True,
                        is_superuser=False,
                        is_active=True,
                    )
                    admin.set_unusable_password()
                    admin.save(update_fields=["password"])

                application.status = BarangayApplication.Status.APPROVED
                application.review_note = serializer.validated_data.get("review_note", "").strip()
                application.reviewed_by = request.user
                application.reviewed_at = timezone.now()
                application.review_verified = True
                application.proof_reviewed = bool(
                    applicant is not None and serializer.validated_data["proof_reviewed"]
                )
                application.created_barangay = barangay
                application.created_admin = admin
                proof_cleanup = None
                if application.proof_of_authority:
                    proof_cleanup = queue_private_media_cleanup(
                        "gridy_auth.BarangayApplication",
                        "proof_of_authority",
                        application.proof_of_authority.name,
                    )
                    application.proof_of_authority = ""
                application.save(update_fields=[
                    "status", "review_note", "reviewed_by", "reviewed_at",
                    "review_verified", "proof_reviewed", "created_barangay", "created_admin",
                    "proof_of_authority", "updated_at",
                ])
                if proof_cleanup is not None:
                    transaction.on_commit(
                        lambda cleanup_id=proof_cleanup.pk:
                            attempt_private_media_cleanup_safely(cleanup_id)
                    )

                log_action(
                    user=request.user,
                    action_type=AuditLog.ActionType.USER_ACTION,
                    description=(
                        f"{request.user.role} reviewer approved Barangay application #{application.pk}, "
                        f"activating first Admin account #{admin.pk} for Barangay #{barangay.pk}."
                    ),
                    request=request,
                )

                if applicant is None:
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
            403: OpenApiResponse(description="Restricted to active Barangay Operators and Django superusers."),
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

                applicant = application.applicant_user
                if applicant is not None:
                    applicant = User.objects.select_for_update().get(pk=applicant.pk)
                    if (
                        applicant.is_active
                        or applicant.role != User.Role.ADMIN
                        or applicant.barangay_id is not None
                        or applicant.is_staff
                        or applicant.is_superuser
                    ):
                        return Response(
                            {"detail": "The linked applicant account is no longer in the expected pending state. Resolve it manually before rejection."},
                            status=status.HTTP_409_CONFLICT,
                        )
                    application.applicant_user = None

                application.status = BarangayApplication.Status.REJECTED
                application.review_note = serializer.validated_data["reason"].strip()
                application.reviewed_by = request.user
                application.reviewed_at = timezone.now()
                application.review_verified = False
                proof_cleanup = None
                if application.proof_of_authority:
                    proof_cleanup = queue_private_media_cleanup(
                        "gridy_auth.BarangayApplication",
                        "proof_of_authority",
                        application.proof_of_authority.name,
                    )
                    application.proof_of_authority = ""
                application.save(update_fields=[
                    "status", "review_note", "reviewed_by", "reviewed_at",
                    "review_verified", "applicant_user", "proof_of_authority", "updated_at",
                ])
                if proof_cleanup is not None:
                    transaction.on_commit(
                        lambda cleanup_id=proof_cleanup.pk:
                            attempt_private_media_cleanup_safely(cleanup_id)
                    )

                if applicant is not None:
                    applicant.delete()

                log_action(
                    user=request.user,
                    action_type=AuditLog.ActionType.USER_ACTION,
                    description=f"{request.user.role} reviewer rejected Barangay application #{application.pk} with a recorded reason.",
                    request=request,
                )
        except BarangayApplication.DoesNotExist:
            return Response({"detail": "Application not found."}, status=status.HTTP_404_NOT_FOUND)

        return Response(BarangayApplicationOperatorSerializer(application).data)

    @extend_schema(
        summary="Permanently erase a Barangay application and its linked applicant account",
        request=BarangayApplicationErasureSerializer,
        responses={
            204: OpenApiResponse(description="Application and linked applicant account erased."),
            400: OpenApiResponse(description="A deletion reason or exact application confirmation is invalid."),
            403: OpenApiResponse(description="Restricted to active Barangay Operators and Django superusers."),
            404: OpenApiResponse(description="Application not found."),
            409: OpenApiResponse(description="The linked account is inconsistent or is the Barangay's last active Admin."),
        },
    )
    @action(detail=True, methods=["post"], url_path="erase")
    @transaction.atomic
    def erase(self, request, pk=None):
        candidate = get_object_or_404(self.get_queryset(), pk=pk)
        candidate_account_ids = {
            account_id
            for account_id in (candidate.applicant_user_id, candidate.created_admin_id)
            if account_id is not None
        }
        if len(candidate_account_ids) > 1:
            return Response(
                {"detail": "This application links to conflicting Admin accounts. Resolve the links before deleting it."},
                status=status.HTTP_409_CONFLICT,
            )

        candidate_account = (
            User.objects.filter(pk=next(iter(candidate_account_ids))).first()
            if candidate_account_ids
            else None
        )
        candidate_barangay_id = candidate_account.barangay_id if candidate_account else None
        if candidate_barangay_id is not None:
            get_object_or_404(
                Barangay.objects.select_for_update(),
                pk=candidate_barangay_id,
            )

        # Lock the application after its tenant row so this action serializes
        # with account erasure and the final-active-Admin guard.
        application_lock_filter = Q(pk=pk)
        if candidate_account_ids:
            candidate_account_id = next(iter(candidate_account_ids))
            application_lock_filter |= Q(applicant_user_id=candidate_account_id) | Q(
                created_admin_id=candidate_account_id
            )
        locked_application_ids = list(
            BarangayApplication.objects.filter(application_lock_filter)
            .order_by("pk")
            .select_for_update(of=("self",))
            .values_list("pk", flat=True)
        )
        if not any(str(application_id) == str(pk) for application_id in locked_application_ids):
            raise Http404("Application not found.")
        application = get_object_or_404(BarangayApplication.objects, pk=pk)
        linked_account_ids = {
            account_id
            for account_id in (application.applicant_user_id, application.created_admin_id)
            if account_id is not None
        }
        if len(linked_account_ids) > 1:
            return Response(
                {"detail": "This application links to conflicting Admin accounts. Resolve the links before deleting it."},
                status=status.HTTP_409_CONFLICT,
            )
        if linked_account_ids != candidate_account_ids:
            return Response(
                {"detail": "The application changed while deletion was being prepared. Refresh and retry."},
                status=status.HTTP_409_CONFLICT,
            )

        target = (
            User.objects.select_for_update().filter(pk=next(iter(linked_account_ids))).first()
            if linked_account_ids
            else None
        )
        if target is not None and target.barangay_id != candidate_barangay_id:
            return Response(
                {"detail": "The application changed while deletion was being prepared. Refresh and retry."},
                status=status.HTTP_409_CONFLICT,
            )
        if target is not None and (
            target.role != User.Role.ADMIN
            or target.is_superuser
            or target.pk == request.user.pk
        ):
            return Response(
                {"detail": "The linked account is not an eligible Barangay Admin account for this action."},
                status=status.HTTP_409_CONFLICT,
            )

        serializer = BarangayApplicationErasureSerializer(
            data=request.data,
            context={"application_id": application.pk},
        )
        serializer.is_valid(raise_exception=True)

        if target and target.is_active and target.barangay_id is not None:
            active_admin_count = User.objects.filter(
                barangay_id=target.barangay_id,
                role=User.Role.ADMIN,
                is_active=True,
                is_superuser=False,
            ).count()
            if active_admin_count <= 1:
                return Response(
                    {"account": "Deleting this account would remove the Barangay's last active Admin. Arrange another active Admin before retrying."},
                    status=status.HTTP_409_CONFLICT,
                )

        reason = serializer.validated_data["reason"]
        log_action(
            user=request.user,
            action_type=AuditLog.ActionType.USER_ACTION,
            description=(
                f"{request.user.role} reviewer permanently erased Barangay application "
                f"#{application.pk}; status={application.status}; "
                f"linked account ID={target.pk if target else 'none'}; reason={reason}."
            ),
            request=request,
        )

        if target is not None:
            erase_user_account(
                target,
                reason=(
                    f"Barangay onboarding application #{application.pk} permanently erased; "
                    f"account ID={target.pk}; reason={reason}."
                ),
                request=request,
                actor=request.user,
            )

        if application.proof_of_authority:
            cleanup = queue_private_media_cleanup(
                "gridy_auth.BarangayApplication",
                "proof_of_authority",
                application.proof_of_authority.name,
            )
            transaction.on_commit(
                lambda cleanup_id=cleanup.pk:
                    attempt_private_media_cleanup_safely(cleanup_id)
            )

        application.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
