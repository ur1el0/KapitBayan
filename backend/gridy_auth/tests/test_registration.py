import os
import subprocess
import sys
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image
from rest_framework import status

from gridy_auth.models import Barangay, Resident, User
from .base import IsolatedAuthAPITestCase


def create_test_image_upload(name="registration-proof.png"):
    image_data = BytesIO()
    Image.new("RGB", (1, 1), color="white").save(image_data, format="PNG")
    return SimpleUploadedFile(name, image_data.getvalue(), content_type="image/png")


class AuthRegistrationAPITests(IsolatedAuthAPITestCase):
    def setUp(self):
        self.barangay = Barangay.objects.create(name="Auth Fixture Barangay")
        self.username = "resident_test"
        self.password = "SecurePassword123!"
        self.user = User.objects.create_user(
            username=self.username,
            password=self.password,
            email="resident@example.com",
            role=User.Role.RESIDENT,
        )

    def test_unauthenticated_admin_registration_endpoint_closed(self):
        # Attempting to call the legacy unauthenticated admin registration route returns 404
        response = self.client.post(
            "/api/v1/auth/register/admin/",
            {
                "username": "unauthorized_admin",
                "full_name": "Unauthorized Admin",
                "barangay_id": self.barangay.id,
                "email": "unauth@example.com",
                "password": "SecurePassword123!",
                "confirm_password": "SecurePassword123!",
                "affirmation": True,
                "passkey": "AnyPasskeyVal",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(User.objects.filter(username="unauthorized_admin").exists())

    def test_public_registration_cannot_elevate_to_admin_role(self):
        # Public resident registration ignores or forbids setting role to ADMIN
        url = reverse('auth_register')
        payload = {
            "username": "sneaky_admin_attempt",
            "email": "sneaky@example.com",
            "password": "ValidPassword123!",
            "full_name": "Sneaky User",
            "birth_date": "1995-05-15",
            "barangay_id": self.barangay.id,
            "role": User.Role.ADMIN,
            "privacy_consent": True,
            "privacy_consent_version": settings.PRIVACY_CONSENT_VERSION,
            "philsys_id_photo": create_test_image_upload(),
        }
        response = self.client.post(url, payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created_user = User.objects.get(username="sneaky_admin_attempt")
        self.assertEqual(created_user.role, User.Role.RESIDENT)
        self.assertFalse(created_user.is_staff)

    def test_user_registration_success(self):
        url = reverse('auth_register')
        payload = {
            "username": "new_resident",
            "email": "new@example.com",
            "password": "ValidPassword123!",
            "full_name": "Test Resident",
            "birth_date": "2000-01-01",
            "barangay_id": self.barangay.id,
            "privacy_consent": True,
            "privacy_consent_version": settings.PRIVACY_CONSENT_VERSION,
            "philsys_id_photo": create_test_image_upload(),
        }

        storage = Resident._meta.get_field("philsys_id_photo").storage
        with patch.object(
            storage,
            "save",
            side_effect=lambda name, content, max_length=None: name,
        ):
            response = self.client.post(url, payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.filter(username="new_resident").count(), 1)
        self.assertEqual(User.objects.get(username="new_resident").barangay, self.barangay)

        resident = User.objects.get(username="new_resident").profile
        self.assertEqual(
            resident.privacy_consent_version,
            settings.PRIVACY_CONSENT_VERSION,
        )
        self.assertIsNotNone(resident.privacy_consent_at)

    def test_user_registration_requires_an_uploaded_id_or_residency_proof(self):
        response = self.client.post(
            reverse("auth_register"),
            {
                "username": "resident_without_proof",
                "email": "resident-without-proof@example.com",
                "password": "ValidPassword123!",
                "full_name": "Resident Without Proof",
                "birth_date": "2000-01-01",
                "barangay_id": self.barangay.id,
                "philsys_id_number": "1234567890123456",
                "privacy_consent": True,
                "privacy_consent_version": settings.PRIVACY_CONSENT_VERSION,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("verification_documents", response.data)
        self.assertFalse(
            User.objects.filter(username="resident_without_proof").exists()
        )

    def test_user_registration_accepts_a_residency_proof_without_an_id_photo(self):
        payload = {
            "username": "resident_with_bill_only",
            "email": "resident-with-bill@example.com",
            "password": "ValidPassword123!",
            "full_name": "Resident With Bill",
            "birth_date": "2000-01-01",
            "barangay_id": self.barangay.id,
            "privacy_consent": True,
            "privacy_consent_version": settings.PRIVACY_CONSENT_VERSION,
            "utility_billing_photo": create_test_image_upload("utility-proof.png"),
        }
        storage = Resident._meta.get_field("utility_billing_photo").storage

        with patch.object(
            storage,
            "save",
            side_effect=lambda name, content, max_length=None: name,
        ):
            response = self.client.post(
                reverse("auth_register"), payload, format="multipart"
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            User.objects.filter(username="resident_with_bill_only").exists()
        )

    def test_user_registration_accepts_a_secondary_id_without_other_proofs(self):
        payload = {
            "username": "resident_with_secondary_id",
            "email": "resident-with-secondary-id@example.com",
            "password": "ValidPassword123!",
            "full_name": "Resident With Secondary ID",
            "birth_date": "2000-01-01",
            "barangay_id": self.barangay.id,
            "privacy_consent": True,
            "privacy_consent_version": settings.PRIVACY_CONSENT_VERSION,
            "secondary_id_type": "Passport",
            "secondary_id_photo": create_test_image_upload("passport.png"),
        }
        storage = Resident._meta.get_field("secondary_id_photo").storage

        with patch.object(
            storage,
            "save",
            side_effect=lambda name, content, max_length=None: name,
        ):
            response = self.client.post(
                reverse("auth_register"), payload, format="multipart"
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            User.objects.filter(username="resident_with_secondary_id").exists()
        )

    def test_user_registration_requires_barangay(self):
        response = self.client.post(
            reverse("auth_register"),
            {
                "username": "resident_without_tenant",
                "email": "resident-without-tenant@example.com",
                "password": "ValidPassword123!",
                "full_name": "Resident Without Tenant",
                "birth_date": "2000-01-01",
                "privacy_consent": True,
                "privacy_consent_version": settings.PRIVACY_CONSENT_VERSION,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("barangay_id", response.data)
        self.assertFalse(User.objects.filter(username="resident_without_tenant").exists())

    def test_user_registration_rejects_missing_false_or_stale_consent(self):
        cases = (
            (
                "missing",
                {"privacy_consent_version": settings.PRIVACY_CONSENT_VERSION},
                "privacy_consent",
            ),
            (
                "false",
                {
                    "privacy_consent": False,
                    "privacy_consent_version": settings.PRIVACY_CONSENT_VERSION,
                },
                "privacy_consent",
            ),
            (
                "stale_version",
                {
                    "privacy_consent": True,
                    "privacy_consent_version": "resident-v0",
                },
                "privacy_consent_version",
            ),
        )

        for label, consent_fields, expected_error in cases:
            with self.subTest(consent_case=label):
                payload = {
                    "username": f"consent_{label}",
                    "email": f"consent_{label}@example.com",
                    "password": "ValidPassword123!",
                    "full_name": "Consent Test Resident",
                    "birth_date": "2000-01-01",
                    "barangay_id": self.barangay.id,
                    **consent_fields,
                }
                response = self.client.post(
                    reverse("auth_register"),
                    payload,
                    format="json",
                )

                self.assertEqual(
                    response.status_code,
                    status.HTTP_400_BAD_REQUEST,
                )
                self.assertIn(expected_error, response.data)
                self.assertFalse(
                    User.objects.filter(username=payload["username"]).exists()
                )

    def test_user_registration_weak_password(self):
        url = reverse('auth_register')
        payload = {
            "username": "weak_resident",
            "email": "weak@example.com",
            "password": "123",
            "full_name": "Weak Password Test Resident",
            "birth_date": "2000-01-01",
            "barangay_id": self.barangay.id,
            "privacy_consent": True,
            "privacy_consent_version": settings.PRIVACY_CONSENT_VERSION,
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)
