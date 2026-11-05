from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from gridy_auth.serializers import (
    UserSerializer,
    RegisterSerializer,
)
from gridy_auth.tasks import send_welcome_email

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
            user = serializer.save()

            # Send welcome email asynchronously
            full_name = getattr(user, 'profile', user).full_name if hasattr(user, 'profile') else user.username 
            send_welcome_email.delay(user.email, full_name)

            return Response(
                UserSerializer(user).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
