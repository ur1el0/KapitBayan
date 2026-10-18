from django.urls import reverse
from rest_framework import status

from gridy_audit.models import AuditLog
from gridy_auth.models import Barangay, Resident, User
from .base import IsolatedAuthAPITestCase


class ResidentProfileAPITests(IsolatedAuthAPITestCase):
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

    def test_profile_endpoint_requires_auth(self):
        # Hardcoding path to catch routing bugs
        url = "/api/v1/auth/me/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_update_cannot_restore_revoked_verification(self):
        resident_profile = Resident.objects.create(
            user=self.user,
            full_name="Verification Test Resident",
            birth_date="1995-05-15",
            is_verified=False,
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            "/api/v1/auth/me/",
            {"profile": {"is_verified": True}},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        resident_profile.refresh_from_db()
        self.assertFalse(resident_profile.is_verified)

    def test_profile_endpoint_success(self):
        #  1. Login the user to obtain a token
        login_url = reverse('auth_login')
        login_payload = {
            "username": self.username,
            "password": self.password
        }
        login_response = self.client.post(login_url, login_payload, format='json')
        token = login_response.data['access']

        # 2. Add JWT token to Auth headers
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        # 3. Request the user profile
        url = "/api/v1/auth/me/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], self.username)

    def test_notification_preferences_are_returned_and_updated_for_self(self):
        self.client.force_authenticate(user=self.user)

        profile_response = self.client.get("/api/v1/auth/me/")

        self.assertEqual(profile_response.status_code, status.HTTP_200_OK)
        self.assertTrue(profile_response.data["email_alerts"])
        self.assertFalse(profile_response.data["push_alerts"])

        update_response = self.client.patch(
            "/api/v1/auth/me/",
            {"email_alerts": False, "push_alerts": True},
            format="json",
        )

        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertFalse(self.user.email_alerts)
        self.assertTrue(self.user.push_alerts)

    def test_self_deletion_preserves_audit_event_without_actor(self):
        user_id = self.user.pk
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(reverse("auth_me"))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(User.objects.filter(pk=user_id).exists())

        audit_log = AuditLog.objects.get(
            action_type=AuditLog.ActionType.USER_ACTION,
            description__startswith=(
                f"User {self.username} (ID: {user_id}) voluntarily exercised"
            ),
        )
        self.assertIsNone(audit_log.action_by_id)
        self.assertTrue(
            str(audit_log).startswith("Deleted user - USER_ACTION at ")
        )


class ResidentVerificationAPITests(IsolatedAuthAPITestCase):
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

    def test_reject_resident_deletes_account(self):
        barangay = Barangay.objects.create(name="Resident Rejection Test")

        dummy_user = User.objects.create_user(
            username="dummy_pending",
            password="password123",
            email="dummy@example.com",
            role=User.Role.RESIDENT,
            barangay=barangay,
        )
        dummy_resident = Resident.objects.create(
            user=dummy_user,
            full_name="Dummy Pending",
            birth_date="2000-01-01",
        )

        self.user.role = User.Role.ADMIN
        self.user.barangay = barangay
        self.user.save()
        self.client.force_authenticate(user=self.user)

        url = reverse("reject_resident", args=[dummy_resident.pk])
        response = self.client.delete(
            url,
            {"rejection_reason": "The submitted details could not be verified."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(User.objects.filter(pk=dummy_user.pk).exists())

        audit_log = AuditLog.objects.get(
            action_by=self.user,
            action_type=AuditLog.ActionType.USER_ACTION,
        )
        self.assertIn(
            "Reason: The submitted details could not be verified.",
            audit_log.description,
        )

    def test_reject_resident_requires_nonblank_reason(self):
        barangay = Barangay.objects.create(name="Rejection Reason Test")
        target_user = User.objects.create_user(
            username="pending_without_reason",
            password="password123",
            email="pending-without-reason@example.com",
            role=User.Role.RESIDENT,
            barangay=barangay,
        )
        resident = Resident.objects.create(
            user=target_user,
            full_name="Pending Resident",
            birth_date="2000-01-01",
        )

        self.user.role = User.Role.ADMIN
        self.user.barangay = barangay
        self.user.save()
        self.client.force_authenticate(user=self.user)

        url = reverse("reject_resident", args=[resident.pk])

        for reason in ("", "   "):
            with self.subTest(reason=reason):
                response = self.client.delete(
                    url,
                    {"rejection_reason": reason},
                    format="json",
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertTrue(User.objects.filter(pk=target_user.pk).exists())
        self.assertFalse(
            AuditLog.objects.filter(
                action_by=self.user,
                action_type=AuditLog.ActionType.USER_ACTION,
            ).exists()
        )

    def test_official_cannot_reject_resident_from_another_barangay(self):
        official_barangay = Barangay.objects.create(name="Official Barangay")
        other_barangay = Barangay.objects.create(name="Other Barangay")
        target_user = User.objects.create_user(
            username="other_barangay_pending",
            password="password123",
            email="other-pending@example.com",
            role=User.Role.RESIDENT,
            barangay=other_barangay,
        )
        resident = Resident.objects.create(
            user=target_user,
            full_name="Resident From Other Barangay",
            birth_date="2000-01-01",
        )

        self.user.role = User.Role.ADMIN
        self.user.barangay = official_barangay
        self.user.save()
        self.client.force_authenticate(user=self.user)

        url = reverse("reject_resident", args=[resident.pk])
        response = self.client.delete(
            url,
            {"rejection_reason": "Test rejection reason."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(User.objects.filter(pk=target_user.pk).exists())

    def test_official_cannot_verify_resident_from_another_barangay(self):
        official_barangay = Barangay.objects.create(name="Verification Official Barangay")
        other_barangay = Barangay.objects.create(name="Verification Other Barangay")
        target_user = User.objects.create_user(
            username="other_barangay_unverified",
            password="password123",
            email="other-unverified@example.com",
            role=User.Role.RESIDENT,
            barangay=other_barangay,
        )
        resident = Resident.objects.create(
            user=target_user,
            full_name="Unverified Resident From Other Barangay",
            birth_date="2000-01-01",
        )

        self.user.role = User.Role.ADMIN
        self.user.barangay = official_barangay
        self.user.save()
        self.client.force_authenticate(user=self.user)

        url = reverse("verify_resident", args=[resident.pk])
        response = self.client.patch(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        resident.refresh_from_db()
        self.assertFalse(resident.is_verified)
