from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image
from rest_framework import status

from gridy_auth.models import Barangay, User
from .base import IsolatedAuthAPITestCase


def profile_image(name="admin-profile.png"):
    image_data = BytesIO()
    Image.new("RGB", (16, 16), color="navy").save(image_data, format="PNG")
    return SimpleUploadedFile(name, image_data.getvalue(), content_type="image/png")


class AdminProfilePictureAPITests(IsolatedAuthAPITestCase):
    def setUp(self):
        self.barangay = Barangay.objects.create(name="Profile Picture Barangay")
        self.user = User.objects.create_user(
            username="profile_admin",
            email="admin@example.com",
            password="SecurePassword123!",
            role=User.Role.ADMIN,
            barangay=self.barangay,
            first_name="Ada",
            last_name="Official",
        )
        self.client.force_authenticate(self.user)

    def test_admin_can_upload_and_remove_own_profile_picture(self):
        response = self.client.patch(
            reverse("auth_me"),
            {"profile_picture": profile_image()},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.profile_picture.name.startswith("profile_pictures/"))
        self.assertIn("profile_pictures/", response.data["profile_picture"])
        self.assertEqual(response.data["full_name"], "Ada Official")

        removed = self.client.patch(
            reverse("auth_me"),
            {"remove_profile_picture": True},
            format="json",
        )

        self.assertEqual(removed.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertFalse(self.user.profile_picture)
        self.assertIsNone(removed.data["profile_picture"])
