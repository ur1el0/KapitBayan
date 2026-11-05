import os
import subprocess
import sys
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from rest_framework import status

from gridy_auth.models import Barangay, BarangayApplication, Resident, User
from .base import IsolatedAuthAPITestCase


def create_test_image_upload(name="registration-proof.png"):
    image_data = BytesIO()
    Image.new("RGB", (1, 1), color="white").save(image_data, format="PNG")
    return SimpleUploadedFile(name, image_data.getvalue(), content_type="image/png")


class AuthRegistrationAPITests(IsolatedAuthAPITestCase):
    def setUp(self):
        self.barangay = Barangay.objects.create(name="Auth Fixture Barangay")
        BarangayApplication.objects.create(
            name=self.barangay.name,
            applicant_name="Fixture Official",
            applicant_position="Secretary",
            applicant_email="fixture.admin@example.test",
            applicant_phone="09123456789",
            status=BarangayApplication.Status.APPROVED,
            created_barangay=self.barangay,
            review_verified=True,
        )
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
            "purok": "Purok 1",
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
            "purok": "Purok 1",
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
                "purok": "Purok 1",
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
            "purok": "Purok 1",
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
            "purok": "Purok 1",
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

    def _minor_payload(self, username, guardian_id=None, birth_date=None):
        today = timezone.localdate()
        return {
            "username": username,
            "email": f"{username}@example.com",
            "password": "ValidPassword123!",
            "full_name": "Minor Test Resident",
            "birth_date": birth_date or today.replace(year=today.year - 17).isoformat(),
            "barangay_id": self.barangay.id,
            "privacy_consent": True,
            "privacy_consent_version": settings.PRIVACY_CONSENT_VERSION,
            "purok": "Purok 1",
            "guardian_id": guardian_id or "",
            "guardian_relationship": Resident.GuardianRelationship.PARENT,
            "guardianship_evidence": create_test_image_upload(f"{username}-guardian.png"),
            "philsys_id_photo": create_test_image_upload(f"{username}.png"),
        }

    def _post_resident_registration(self, payload):
        storage = Resident._meta.get_field("philsys_id_photo").storage
        with patch.object(
            storage,
            "save",
            side_effect=lambda name, content, max_length=None: name,
        ):
            return self.client.post(reverse("auth_register"), payload, format="multipart")

    def test_minor_registration_requires_a_guardian(self):
        response = self._post_resident_registration(
            self._minor_payload("minor_without_guardian")
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("guardian_id", response.data)
        self.assertFalse(User.objects.filter(username="minor_without_guardian").exists())

    def test_minor_registration_rejects_a_future_birth_date(self):
        future_date = (timezone.localdate().replace(year=timezone.localdate().year + 1)).isoformat()
        response = self._post_resident_registration(
            self._minor_payload(
                "minor_future_birth_date",
                guardian_id="verified_adult_guardian",
                birth_date=future_date,
            )
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("birth_date", response.data)
        self.assertFalse(User.objects.filter(username="minor_future_birth_date").exists())

    def test_minor_must_link_to_a_verified_active_adult_in_the_same_barangay(self):
        guardian = User.objects.create_user(
            username="verified_adult_guardian",
            password="ValidPassword123!",
            email="verified-guardian@example.com",
            role=User.Role.RESIDENT,
            barangay=self.barangay,
        )
        guardian_profile = Resident.objects.create(
            user=guardian,
            full_name="Verified Adult Guardian",
            birth_date="1980-01-01",
            is_verified=True,
        )

        response = self._post_resident_registration(
            self._minor_payload("minor_with_verified_guardian", guardian.username)
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            User.objects.get(username="minor_with_verified_guardian").profile.guardian,
            guardian_profile,
        )
        minor_profile = User.objects.get(username="minor_with_verified_guardian").profile
        self.assertEqual(
            minor_profile.guardian_relationship,
            Resident.GuardianRelationship.PARENT,
        )
        self.assertTrue(minor_profile.guardianship_evidence.name)

    def test_minor_registration_requires_relationship_and_supporting_evidence(self):
        guardian = User.objects.create_user(
            username="guardian_missing_review_data",
            password="ValidPassword123!",
            email="guardian-review-data@example.com",
            role=User.Role.RESIDENT,
            barangay=self.barangay,
        )
        Resident.objects.create(
            user=guardian,
            full_name="Verified Adult Guardian",
            birth_date="1980-01-01",
            is_verified=True,
        )

        payload = self._minor_payload("minor_missing_guardian_review_data", guardian.username)
        payload.pop("guardian_relationship")
        payload.pop("guardianship_evidence")
        response = self._post_resident_registration(payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("guardian_relationship", response.data)
        self.assertIn("guardianship_evidence", response.data)
        self.assertFalse(
            User.objects.filter(username="minor_missing_guardian_review_data").exists()
        )

    def test_minor_rejects_unverified_underage_or_cross_barangay_guardians(self):
        other_barangay = Barangay.objects.create(name="Guardian Other Barangay")
        cases = (
            ("unverified", "1980-01-01", False, self.barangay, True),
            ("underage", timezone.localdate().replace(year=timezone.localdate().year - 16), True, self.barangay, True),
            ("cross_barangay", "1980-01-01", True, other_barangay, True),
            ("inactive", "1980-01-01", True, self.barangay, False),
        )

        for label, birth_date, verified, barangay, active in cases:
            with self.subTest(guardian_case=label):
                guardian = User.objects.create_user(
                    username=f"guardian_{label}",
                    password="ValidPassword123!",
                    email=f"guardian-{label}@example.com",
                    role=User.Role.RESIDENT,
                    barangay=barangay,
                    is_active=active,
                )
                Resident.objects.create(
                    user=guardian,
                    full_name=f"Guardian {label}",
                    birth_date=birth_date,
                    is_verified=verified,
                )
                response = self._post_resident_registration(
                    self._minor_payload(f"minor_{label}", guardian.username)
                )

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("guardian_id", response.data)
                self.assertFalse(User.objects.filter(username=f"minor_{label}").exists())

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
                "purok": "Purok 1",
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
                    "purok": "Purok 1",
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
            "purok": "Purok 1",
            "privacy_consent_version": settings.PRIVACY_CONSENT_VERSION,
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_registration_rejected_for_unapproved_pending_rejected_and_inactive_barangay(self):
        url = reverse('auth_register')
        def make_payload(username, barangay_id):
            return {
                "username": username,
                "email": f"{username}@example.test",
                "password": "ValidPassword123!",
                "full_name": "Test Resident",
                "birth_date": "2000-01-01",
                "barangay_id": barangay_id,
                "privacy_consent": True,
                "purok": "Purok 1",
                "privacy_consent_version": settings.PRIVACY_CONSENT_VERSION,
                "philsys_id_photo": create_test_image_upload(f"{username}.png"),
            }

        # 1. Unregistered barangay (no application at all)
        b_unregistered = Barangay.objects.create(name="Barangay Unregistered")
        res1 = self.client.post(
            url,
            make_payload("res_unreg", b_unregistered.id),
            format="multipart",
        )
        self.assertEqual(res1.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("barangay_id", res1.data)
        self.assertFalse(User.objects.filter(username="res_unreg").exists())

        # 2. Pending barangay
        b_pending = Barangay.objects.create(name="Barangay Pending")
        BarangayApplication.objects.create(
            name=b_pending.name,
            applicant_name="Pending Official",
            applicant_position="Official",
            applicant_email="pending@example.test",
            applicant_phone="09123456782",
            status=BarangayApplication.Status.PENDING,
            created_barangay=b_pending,
        )
        res2 = self.client.post(
            url,
            make_payload("res_pending", b_pending.id),
            format="multipart",
        )
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("barangay_id", res2.data)
        self.assertFalse(User.objects.filter(username="res_pending").exists())

        # 3. Rejected barangay
        b_rejected = Barangay.objects.create(name="Barangay Rejected")
        BarangayApplication.objects.create(
            name=b_rejected.name,
            applicant_name="Rejected Official",
            applicant_position="Official",
            applicant_email="rejected@example.test",
            applicant_phone="09123456783",
            status=BarangayApplication.Status.REJECTED,
            created_barangay=b_rejected,
            review_note="Rejected proof",
        )
        res3 = self.client.post(
            url,
            make_payload("res_rejected", b_rejected.id),
            format="multipart",
        )
        self.assertEqual(res3.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("barangay_id", res3.data)
        self.assertFalse(User.objects.filter(username="res_rejected").exists())

        # 4. Inactive barangay (approved but admin deactivated)
        b_inactive = Barangay.objects.create(name="Barangay Inactive")
        admin_inactive = User.objects.create_user(
            username="admin_inactive_user",
            role=User.Role.ADMIN,
            is_active=False,
            barangay=b_inactive,
        )
        BarangayApplication.objects.create(
            name=b_inactive.name,
            applicant_name="Inactive Official",
            applicant_position="Official",
            applicant_email="inactive@example.test",
            applicant_phone="09123456784",
            status=BarangayApplication.Status.APPROVED,
            created_barangay=b_inactive,
            created_admin=admin_inactive,
            review_verified=True,
        )
        res4 = self.client.post(
            url,
            make_payload("res_inactive", b_inactive.id),
            format="multipart",
        )
        self.assertEqual(res4.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("barangay_id", res4.data)
        self.assertFalse(User.objects.filter(username="res_inactive").exists())
