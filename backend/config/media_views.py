import os
from django.conf import settings
from django.http import FileResponse, Http404
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

class ProtectedMediaView(APIView):
    """
    Serves media files securely with directory-aware access control.
    Ensures that sensitive government IDs and resident billings are strictly
    protected under RA 10173 while public assets (logos, announcements) remain accessible.
    """
    permission_classes = [AllowAny]

    # Directories containing sensitive PII under RA 10173
    SENSITIVE_DIRECTORIES = (
        'resident_ids/', 'resident_billings/', 'blotter/', 'payment_proofs/',
        'barangay_onboarding/',
    )

    def get(self, request, path):
        if not hasattr(settings, "MEDIA_ROOT"):
            raise Http404("File not found.")

        document_root = os.path.realpath(settings.MEDIA_ROOT)
        file_path = os.path.realpath(os.path.join(document_root, path))

        try:
            if os.path.commonpath((document_root, file_path)) != document_root:
                raise Http404("Invalid file path.")
        except ValueError:
            raise Http404("Invalid file path.")

        relative_path = os.path.relpath(file_path, document_root).replace(os.sep, "/")
        if any(
            relative_path == directory.rstrip("/")
            or relative_path.startswith(directory)
            for directory in self.SENSITIVE_DIRECTORIES
        ):
            raise Http404("File not found.")

        if not os.path.exists(file_path):
            raise Http404("File not found.")

        return FileResponse(open(file_path, "rb"))
