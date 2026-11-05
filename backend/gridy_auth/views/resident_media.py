import logging

from PIL import Image
from django.http import FileResponse, Http404
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from gridy_auth.models import Resident, User


logger = logging.getLogger(__name__)


class MediaStorageUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Resident media storage is temporarily unavailable."
    default_code = "media_storage_unavailable"


class ResidentPrivateMediaView(APIView):
    permission_classes = [IsAuthenticated]

    PRIVATE_FIELDS = {
        "philsys_id_photo",
        "secondary_id_photo",
        "utility_billing_photo",
        "guardianship_evidence",
    }

    def get(self, request, resident_id, field_name):
        if field_name not in self.PRIVATE_FIELDS:
            raise Http404("Media not found.")

        try:
            resident = Resident.objects.select_related("user").get(pk=resident_id)
        except Resident.DoesNotExist:
            raise Http404("Media not found.")

        requester = request.user
        is_owner = (
            requester.role == User.Role.RESIDENT
            and requester.pk == resident.user_id
        )
        is_same_barangay_official = (
            requester.role == User.Role.ADMIN
            and requester.barangay_id is not None
            and requester.barangay_id == resident.user.barangay_id
        )
        # Guardianship documents are available only to the assigned Barangay Admin
        # reviewing the application, never from the applicant's own account.
        allowed_guardianship_review = (
            field_name == "guardianship_evidence" and is_same_barangay_official
        )
        if field_name == "guardianship_evidence":
            allowed = allowed_guardianship_review
        else:
            allowed = is_owner or is_same_barangay_official
        if not allowed:
            raise Http404("Media not found.")

        media_file = getattr(resident, field_name)
        if not media_file or not media_file.name:
            raise Http404("Media not found.")

        try:
            opened_file = self._open_media(media_file)
            content_type = self._content_type(opened_file)
        except (FileNotFoundError, OSError):
            raise Http404("Media not found.")
        except Exception as error:
            logger.error(
                "Resident media storage failed (%s).",
                type(error).__name__,
            )
            raise MediaStorageUnavailable() from None

        response = FileResponse(opened_file, content_type=content_type)
        response["Content-Disposition"] = "inline"
        response["Cache-Control"] = "private, no-store, max-age=0"
        response["X-Content-Type-Options"] = "nosniff"
        return response

    @staticmethod
    def _open_media(media_file):
        private_open = getattr(
            media_file.storage,
            "open_private_resident_media",
            None,
        )
        if private_open:
            return private_open(media_file.name, "rb")
        return media_file.open("rb")

    @staticmethod
    def _content_type(opened_file):
        position = opened_file.tell()
        try:
            with Image.open(opened_file) as image:
                image_format = image.format
                image.verify()

            content_type = Image.MIME.get(image_format)
            if not content_type or not content_type.startswith("image/"):
                raise OSError("Unsupported resident image format.")
            return content_type
        finally:
            opened_file.seek(position)
