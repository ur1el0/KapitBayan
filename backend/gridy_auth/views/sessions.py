from rest_framework import permissions, viewsets

from gridy_auth.models import RefreshSession
from gridy_auth.serializers import RefreshSessionSerializer


class SessionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Exposes the user's active and revoked sessions for security management.
    """
    lookup_value_regex = r"\d+"
    serializer_class = RefreshSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return RefreshSession.objects.filter(user=self.request.user).order_by('-created_at')
