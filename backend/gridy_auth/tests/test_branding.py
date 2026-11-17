from django.urls import reverse
from rest_framework import status

from gridy_auth.models import Barangay, User
from .base import IsolatedAuthAPITestCase


class BarangayBrandingAPITests(IsolatedAuthAPITestCase):
    def setUp(self):
        self.barangay = Barangay.objects.create(name="Barangay Branding Test")
        self.admin = User.objects.create_user(
            username="branding_admin",
            email="branding-admin@example.com",
            password="StrongTestPassword123!",
            role=User.Role.ADMIN,
            barangay=self.barangay,
        )
        self.client.force_authenticate(user=self.admin)
        self.detail_url = reverse(
            "barangay-detail",
            args=[self.barangay.pk],
        )

    def test_detail_returns_default_primary_color(self):
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["primary_color"], "#082B66")

    def test_official_can_update_primary_color(self):
        response = self.client.patch(
            self.detail_url,
            {"primary_color": "#C70039"},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.barangay.refresh_from_db()
        self.assertEqual(self.barangay.primary_color, "#C70039")

    def test_invalid_primary_color_is_rejected(self):
        response = self.client.patch(
            self.detail_url,
            {"primary_color": "not-a-color"},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("primary_color", response.data)

    def test_official_cannot_update_another_barangay_color(self):
        other_barangay = Barangay.objects.create(
            name="Another Branding Test Barangay"
        )
        other_url = reverse(
            "barangay-detail",
            args=[other_barangay.pk],
        )

        response = self.client.patch(
            other_url,
            {"primary_color": "#C70039"},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        other_barangay.refresh_from_db()
        self.assertEqual(other_barangay.primary_color, "#082B66")

    def test_official_can_configure_and_clear_kiosk_staff_pin(self):
        set_resp = self.client.patch(
            self.detail_url,
            {"kiosk_staff_pin": "2468"},
            format="multipart",
        )
        self.assertEqual(set_resp.status_code, status.HTTP_200_OK)
        self.assertTrue(set_resp.data["has_kiosk_staff_pin"])
        self.assertNotIn("kiosk_staff_pin", set_resp.data)
        self.assertNotIn("kiosk_staff_pin_hash", set_resp.data)

        self.barangay.refresh_from_db()
        self.assertTrue(self.barangay.check_kiosk_staff_pin("2468"))
        self.assertNotEqual(self.barangay.kiosk_staff_pin_hash, "2468")

        short_resp = self.client.patch(
            self.detail_url,
            {"kiosk_staff_pin": "12"},
            format="multipart",
        )
        self.assertEqual(short_resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("kiosk_staff_pin", short_resp.data)

        clear_resp = self.client.patch(
            self.detail_url,
            {"clear_kiosk_staff_pin": "true"},
            format="multipart",
        )
        self.assertEqual(clear_resp.status_code, status.HTTP_200_OK)
        self.assertFalse(clear_resp.data["has_kiosk_staff_pin"])
        self.barangay.refresh_from_db()
        self.assertFalse(self.barangay.check_kiosk_staff_pin("2468"))
