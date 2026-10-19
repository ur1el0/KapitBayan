from unittest.mock import patch
from datetime import timedelta
from uuid import uuid4

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from gridy_audit.models import AuditLog
from gridy_auth.models import Barangay, RefreshSession, User
from .base import IsolatedAuthAPITestCase


class PlatformAccountSupportTests(IsolatedAuthAPITestCase):
    def setUp(self):
        self.barangay = Barangay.objects.create(name="Support Test Barangay")
        self.admin = User.objects.create_user(
            username="support_test_admin",
            password="test-password-123",
            role=User.Role.ADMIN,
            barangay=self.barangay,
        )
        self.other_admin = User.objects.create_user(
            username="support_test_admin_2",
            password="test-password-123",
            role=User.Role.ADMIN,
            barangay=self.barangay,
        )
        self.resident = User.objects.create_user(
            username="support_test_resident",
            password="test-password-123",
            email="resident-old@example.test",
            role=User.Role.RESIDENT,
            barangay=self.barangay,
        )
        self.operator = User.objects.create_user(
            username="support_test_operator",
            email="operator@example.test",
            password="test-password-123",
            role=User.Role.BARANGAY_OPERATOR,
        )
        self.superuser = User.objects.create_superuser(
            username="support_test_superuser",
            email="superuser@example.test",
            password="test-password-123",
        )
        self.client = APIClient()
        self.list_url = reverse("platform-account-support-list")

    def test_only_active_operator_or_superuser_can_list_supported_accounts(self):
        self.assertEqual(self.client.get(self.list_url).status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get(self.list_url).status_code, status.HTTP_403_FORBIDDEN)

        unsupported = User.objects.create_user(
            username="support_unsupported_role",
            password="test-password-123",
            role="UNKNOWN_ROLE",
        )
        self.client.force_authenticate(unsupported)
        self.assertEqual(self.client.get(self.list_url).status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.operator)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {row["id"] for row in response.data["results"]}
        self.assertIn(self.admin.pk, returned_ids)
        self.assertIn(self.resident.pk, returned_ids)
        self.assertNotIn(self.operator.pk, returned_ids)
        self.assertNotIn(self.superuser.pk, returned_ids)
        self.client.force_authenticate(self.superuser)
        self.assertEqual(self.client.get(self.list_url).status_code, status.HTTP_200_OK)

    def test_operator_has_no_service_record_or_unbounded_account_access(self):
        access = str(RefreshToken.for_user(self.operator).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        for path in (
            "/api/v1/auth/pending-residents/",
            "/api/v1/document-requests/",
            "/api/v1/tickets/",
            "/api/v1/aid-requests/",
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_email_correction_is_audited_revokes_sessions_and_dispatches_after_commit(self):
        session = RefreshSession.objects.create(
            user=self.resident,
            refresh_token_jti=str(uuid4()),
            expires_at=timezone.now() + timedelta(days=1),
        )
        detail_url = reverse("platform-account-support-detail", kwargs={"pk": self.resident.pk})
        payload = {
            "email": "resident-new@example.test",
            "contact_verified": True,
            "reason": "INCORRECT_CONTACT",
        }
        self.client.force_authenticate(self.operator)
        with patch("gridy_auth.views.platform_account_support.send_password_reset_email.delay") as send_email:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.patch(detail_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "resident-new@example.test")
        session.refresh_from_db()
        self.assertTrue(session.is_revoked)
        self.assertTrue(AuditLog.objects.filter(
            action_by=self.operator,
            action_type=AuditLog.ActionType.USER_ACTION,
            description__contains=f"target account ID={self.resident.pk}",
        ).exists())
        send_email.assert_called_once()

    def test_disabling_account_revokes_sessions_and_last_admin_is_protected(self):
        self.client.force_authenticate(self.operator)
        session = RefreshSession.objects.create(
            user=self.resident,
            refresh_token_jti=str(uuid4()),
            expires_at=timezone.now() + timedelta(days=1),
        )
        url = reverse("platform-account-support-set-active", kwargs={"pk": self.resident.pk})
        response = self.client.post(url, {
            "is_active": False,
            "reason": "SECURITY_CONCERN",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        session.refresh_from_db()
        self.assertTrue(session.is_revoked)

        self.other_admin.is_active = False
        self.other_admin.save(update_fields=["is_active"])
        last_admin_url = reverse(
            "platform-account-support-set-active",
            kwargs={"pk": self.admin.pk},
        )
        last_admin_response = self.client.post(last_admin_url, {
            "is_active": False,
            "reason": "STATUS_CORRECTION",
        }, format="json")
        self.assertEqual(last_admin_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_support_endpoint_does_not_offer_account_creation_or_deletion(self):
        self.client.force_authenticate(self.operator)
        self.assertEqual(self.client.post(self.list_url, {}, format="json").status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        detail_url = reverse("platform-account-support-detail", kwargs={"pk": self.resident.pk})
        self.assertEqual(self.client.delete(detail_url).status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
