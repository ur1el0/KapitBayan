from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied

from gridy_auth.models import User
from gridy_auth.permissions import IsBarangayOfficial
from gridy_services.models import DocumentServiceOffering
from gridy_services.serializers.documents import DocumentServiceOfferingSerializer


class DocumentServiceOfferingViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentServiceOfferingSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.IsAuthenticated()]
        return [IsBarangayOfficial()]

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated or not user.barangay_id:
            return DocumentServiceOffering.objects.none()

        offerings = DocumentServiceOffering.objects.filter(
            barangay_id=user.barangay_id,
        )
        if user.role != User.Role.ADMIN:
            offerings = offerings.filter(is_active=True)
        return offerings

    def perform_create(self, serializer):
        user = self.request.user
        if not user.barangay_id:
            raise PermissionDenied(
                "Your account must be assigned to a Barangay to manage its document services."
            )
        serializer.save(barangay_id=user.barangay_id)

    def perform_destroy(self, instance):
        # Preserve offerings referenced by request snapshots and the audit trail.
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])
