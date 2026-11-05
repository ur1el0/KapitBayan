from io import BytesIO
from unittest.mock import patch

from django.core.files.base import ContentFile
from django.urls import reverse
from PIL import Image
from rest_framework import status

from gridy_auth.models import Barangay, Resident, User
from gridy_auth.serializers import ResidentSerializer
from .base import IsolatedAuthAPITestCase


class ResidentPrivateMediaAPITests(IsolatedAuthAPITestCase):
    def setUp(self):
        self.barangay = Barangay.objects.create(name="Private Media Barangay")
        self.other_barangay = Barangay.objects.create(name="Foreign Media Barangay")
        self.resident_user = User.objects.create_user(
            username="private_media_resident",
            password=None,
            role=User.Role.RESIDENT,
            barangay=self.barangay,
        )
        self.resident = Resident.objects.create(
            user=self.resident_user,
            full_name="Private Media Resident",
            birth_date="1990-01-01",
            philsys_id_photo="resident_ids/private-test.png",
            guardianship_evidence="resident_guardianship/private-test.png",
        )
        image_data = BytesIO()
        Image.new("RGB", (1, 1)).save(image_data, format="PNG")
        self.test_image_bytes = image_data.getvalue()
        self.other_resident_user = User.objects.create_user(
            username="other_private_media_resident",
            password=None,
            role=User.Role.RESIDENT,
            barangay=self.barangay,
        )
        self.other_resident = Resident.objects.create(
            user=self.other_resident_user,
            full_name="Other Private Media Resident",
            birth_date="1991-01-01",
            philsys_id_photo="resident_ids/other-test.png",
        )
        self.admin = User.objects.create_user(
            username="private_media_admin",
            password=None,
            role=User.Role.ADMIN,
            barangay=self.barangay,
        )
        self.foreign_admin = User.objects.create_user(
            username="foreign_private_media_admin",
            password=None,
            role=User.Role.ADMIN,
            barangay=self.other_barangay,
        )

    def media_url(self, resident=None, field_name="philsys_id_photo"):
        return reverse(
            "resident_private_media",
            kwargs={
                "resident_id": (resident or self.resident).pk,
                "field_name": field_name,
            },
        )

    def get_media_as(self, user, resident=None, field_name="philsys_id_photo"):
        self.client.force_authenticate(user=user)
        with patch(
            "gridy_auth.views.resident_media.ResidentPrivateMediaView._open_media",
            return_value=ContentFile(self.test_image_bytes, name="private-test.png"),
        ):
            return self.client.get(self.media_url(resident, field_name))

    def test_resident_can_access_own_private_media(self):
        response = self.get_media_as(self.resident_user)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertEqual(response["Cache-Control"], "private, no-store, max-age=0")
        self.assertEqual(response["Content-Disposition"], "inline")
        self.assertEqual(
            b"".join(response.streaming_content),
            self.test_image_bytes,
        )

    def test_inline_media_type_comes_from_image_content_not_filename(self):
        self.resident.philsys_id_photo = "resident_ids/untrusted.html"
        self.resident.save(update_fields=["philsys_id_photo"])

        response = self.get_media_as(self.resident_user)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")

    def test_invalid_image_content_is_not_served_inline(self):
        self.client.force_authenticate(user=self.resident_user)
        with patch(
            "gridy_auth.views.resident_media.ResidentPrivateMediaView._open_media",
            return_value=ContentFile(b"not an image", name="private-test.png"),
        ):
            response = self.client.get(self.media_url())

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_same_barangay_official_can_access_resident_private_media(self):
        response = self.get_media_as(self.admin)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_only_same_barangay_admin_can_access_guardianship_evidence(self):
        response = self.get_media_as(
            self.admin,
            resident=self.resident,
            field_name="guardianship_evidence",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.get_media_as(
            self.resident_user,
            resident=self.resident,
            field_name="guardianship_evidence",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        response = self.get_media_as(
            self.foreign_admin,
            resident=self.resident,
            field_name="guardianship_evidence",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_resident_cannot_access_another_residents_private_media(self):
        response = self.get_media_as(
            self.other_resident_user,
            resident=self.resident,
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_official_cannot_access_private_media_from_another_barangay(self):
        response = self.get_media_as(
            self.foreign_admin,
            resident=self.resident,
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unapproved_field_names_are_not_served(self):
        response = self.get_media_as(
            self.admin,
            field_name="philsys_id_number",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_field_official_cannot_access_private_media(self):
        field_official = User.objects.create_user(
            username="private_media_field_official",
            password=None,
            role=User.Role.FIELD_OFFICIAL,
            barangay=self.barangay,
        )

        response = self.get_media_as(field_official)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_request_cannot_access_private_media(self):
        response = self.client.get(self.media_url())

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_media_is_not_opened(self):
        self.resident.philsys_id_photo = ""
        self.resident.save(update_fields=["philsys_id_photo"])
        self.client.force_authenticate(user=self.admin)

        with patch(
            "gridy_auth.views.resident_media.ResidentPrivateMediaView._open_media"
        ) as open_media:
            response = self.client.get(self.media_url())

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        open_media.assert_not_called()

    def test_resident_serializer_returns_authorized_endpoint_not_storage_url(self):
        data = ResidentSerializer(self.resident).data

        self.assertEqual(
            data["philsys_id_photo"],
            self.media_url().removeprefix("/api/v1/"),
        )
        self.assertEqual(
            data["guardianship_evidence"],
            self.media_url(field_name="guardianship_evidence").removeprefix("/api/v1/"),
        )

    def test_legacy_media_route_never_serves_resident_evidence(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get("/media/resident_ids/private-test.png")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
