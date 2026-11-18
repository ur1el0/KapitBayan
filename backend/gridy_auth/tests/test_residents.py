from unittest.mock import patch

from django.urls import reverse
from rest_framework import status

from gridy_audit.models import AuditLog
from gridy_auth.models import Barangay, Resident, User
from .base import IsolatedAuthAPITestCase


class ResidentEmailUpdateAPITests(IsolatedAuthAPITestCase):
    def setUp(self):
        self.barangay = Barangay.objects.create(name="Resident Email Barangay")
        self.other_barangay = Barangay.objects.create(name="Other Email Barangay")

        self.admin = User.objects.create_user(
            username="resident_email_admin",
            email="resident-email-admin@example.com",
            password=None,
            role=User.Role.ADMIN,
            barangay=self.barangay,
        )
        self.resident_user = User.objects.create_user(
            username="offline_resident",
            email="",
            password=None,
            role=User.Role.RESIDENT,
            barangay=self.barangay,
        )
        self.resident = Resident.objects.create(
            user=self.resident_user,
            full_name="Offline Resident",
            birth_date="1990-01-15",
            is_verified=True,
        )

        self.other_resident_user = User.objects.create_user(
            username="other_barangay_resident",
            email="",
            password=None,
            role=User.Role.RESIDENT,
            barangay=self.other_barangay,
        )
        self.other_resident = Resident.objects.create(
            user=self.other_resident_user,
            full_name="Resident From Other Barangay",
            birth_date="1992-03-20",
            is_verified=True,
        )

        self.client.force_authenticate(user=self.admin)

    def test_official_can_add_email_to_local_resident_and_audit_it(self):
        response = self.client.patch(
            reverse("resident-detail", args=[self.resident.pk]),
            {"email": "offline.resident@example.com"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.resident_user.refresh_from_db()
        self.assertEqual(
            self.resident_user.email,
            "offline.resident@example.com",
        )

        audit_entry = AuditLog.objects.get(
            action_by=self.admin,
            action_type=AuditLog.ActionType.USER_ACTION,
        )
        self.assertIn(str(self.resident.pk), audit_entry.description)
        self.assertNotIn(
            "offline.resident@example.com",
            audit_entry.description,
        )

    def test_official_cannot_add_email_to_resident_from_another_barangay(self):
        response = self.client.patch(
            reverse("resident-detail", args=[self.other_resident.pk]),
            {"email": "foreign.resident@example.com"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.other_resident_user.refresh_from_db()
        self.assertEqual(self.other_resident_user.email, "")

    def test_official_cannot_assign_email_already_used_by_another_account(self):
        User.objects.create_user(
            username="existing_email_owner",
            email="already.used@example.com",
            password="StrongTestPassword123!",
            role=User.Role.RESIDENT,
            barangay=self.barangay,
        )

        response = self.client.patch(
            reverse("resident-detail", args=[self.resident.pk]),
            {"email": "ALREADY.USED@example.com"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.resident_user.refresh_from_db()
        self.assertEqual(self.resident_user.email, "")

    @patch("gridy_auth.views.password_reset.send_password_reset_email.delay")
    def test_password_reset_is_not_sent_when_email_is_shared(self, mock_dispatch):
        shared_email = "shared.resident@example.com"
        self.resident_user.email = shared_email
        self.resident_user.save(update_fields=["email"])

        User.objects.create_user(
            username="shared_email_resident",
            email=shared_email,
            password=None,
            role=User.Role.RESIDENT,
            barangay=self.barangay,
        )

        self.client.force_authenticate(user=None)
        response = self.client.post(
            reverse("password_reset_request"),
            {"email": shared_email},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_dispatch.assert_not_called()

    @patch("gridy_auth.views.password_reset.send_password_reset_email.delay")
    def test_password_reset_email_is_dispatched(self, mock_dispatch):
        self.resident_user.email = "reset.resident@example.com"
        self.resident_user.save(update_fields=["email"])
        self.client.force_authenticate(user=None)

        response = self.client.post(
            reverse("password_reset_request"),
            {"email": self.resident_user.email},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_dispatch.assert_called_once()
        recipient, reset_link = mock_dispatch.call_args.args
        self.assertEqual(recipient, self.resident_user.email)
        self.assertIn("/reset-password?uidb64=", reset_link)

    def test_resident_cannot_use_directory_endpoint_to_set_email(self):
        self.client.force_authenticate(user=self.resident_user)

        response = self.client.patch(
            reverse("resident-detail", args=[self.resident.pk]),
            {"email": "resident-chosen@example.com"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.resident_user.refresh_from_db()
        self.assertEqual(self.resident_user.email, "")

    def test_official_cannot_use_directory_endpoint_to_post_resident_create(self):
        initial_resident_count = Resident.objects.count()
        response = self.client.post(
            reverse("resident-list"),
            {
                "full_name": "Direct Post Resident",
                "birth_date": "1998-08-08",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        self.assertEqual(Resident.objects.count(), initial_resident_count)

    def test_non_integer_resident_pk_returns_not_found_instead_of_server_error(self):
        self.assertEqual(
            self.client.get("/api/v1/auth/resident/id/").status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.patch(
                "/api/v1/auth/resident/id/",
                {"email": "invalid@example.com"},
                format="json",
            ).status_code,
            status.HTTP_404_NOT_FOUND,
        )
