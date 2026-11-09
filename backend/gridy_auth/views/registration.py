import logging

from django.db import IntegrityError
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from gridy_auth.models import User
from gridy_auth.serializers import (
    UserSerializer,
    RegisterSerializer,
)
from gridy_auth.tasks import send_welcome_email

logger = logging.getLogger(__name__)

@extend_schema(tags=['Authentication'])
class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = 'auth_register'

    @extend_schema(
        request=RegisterSerializer,
        responses={201: UserSerializer},
        description=(
            "Resident registration requires at least one valid uploaded image: "
            "a PhilSys ID photo, a secondary ID photo, or a utility/residency "
            "proof photo. Applicants under 18 must also provide a verified adult "
            "guardian account, relationship, and supporting evidence for Barangay "
            "Admin review. The review is a human check and does not automatically "
            "determine legal guardianship. A typed PhilSys ID number alone does not satisfy this "
            "requirement. For historical administrative bulk ingestion without "
            "digital proof images, authorized barangay officials must use the "
            "RBI CSV import endpoint (/api/v1/auth/import-residents/)."
        ),
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = serializer.save()
            except IntegrityError as exc:
                # Validation can race with another registration. Report a
                # username conflict when that is what actually happened; do
                # not mislabel a different database constraint as a username
                # problem.
                if User.objects.filter(
                    username__iexact=serializer.validated_data["username"]
                ).exists():
                    return Response(
                        {"username": ["This username is already in use."]},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                logger.warning(
                    "Resident registration hit a database constraint (%s).",
                    type(exc).__name__,
                )
                return Response(
                    {
                        "detail": (
                            "Registration could not be completed because the account "
                            "details changed while you submitted the form. Review the "
                            "details and try again."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            # Send welcome email asynchronously
            full_name = getattr(user, 'profile', user).full_name if hasattr(user, 'profile') else user.username 
            try:
                send_welcome_email.delay(user.email, full_name)
            except Exception as exc:
                # The user is already created. A mail-broker outage must not
                # turn a successful registration into a misleading HTTP 500.
                logger.warning(
                    "Could not queue resident welcome email (%s).",
                    type(exc).__name__,
                )

            return Response(
                UserSerializer(user).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
