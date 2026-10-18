from drf_spectacular.utils import extend_schema
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from gridy_auth.models import Barangay
from gridy_auth.serializers.onboarding import PublicBarangaySerializer


@extend_schema(tags=["Barangay Directory"])
class PublicBarangayDirectoryView(APIView):
    """List existing Barangays so residents can select their jurisdiction."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(responses=PublicBarangaySerializer(many=True))
    def get(self, request):
        barangays = Barangay.objects.all().order_by("province", "municipality", "name")
        return Response(PublicBarangaySerializer(barangays, many=True).data)
