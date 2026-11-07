from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from gridy_services.models import DocumentCertificateVerification, DocumentRequest


class PublicCertificateVerificationView(APIView):
    """Publicly confirm a Barangay certificate record without exposing resident data."""

    permission_classes = [permissions.AllowAny]
    throttle_scope = "certificate_verification"

    def get(self, request, token):
        record = (
            DocumentCertificateVerification.objects.filter(
                token=token,
                revoked_at__isnull=True,
                document_request__status=DocumentRequest.Status.RELEASED,
            )
            .select_related("document_request__barangay")
            .first()
        )

        if record is None:
            response = Response({"valid": False}, status=status.HTTP_200_OK)
        else:
            document_request = record.document_request
            barangay = document_request.barangay
            data = (
                {
                    "valid": True,
                    "barangay_name": barangay.name,
                    "document_type": document_request.document_type,
                    "issued_at": record.issued_at,
                }
                if barangay
                else {"valid": False}
            )
            response = Response(data, status=status.HTTP_200_OK)

        response["Cache-Control"] = "no-store, max-age=0"
        response["X-Content-Type-Options"] = "nosniff"
        return response
