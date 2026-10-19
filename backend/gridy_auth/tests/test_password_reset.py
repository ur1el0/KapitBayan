import logging
from unittest.mock import patch
from django.conf import settings
from django.urls import reverse
from rest_framework import status

from gridy_auth.models import Barangay, User
from gridy_auth.tasks import send_password_reset_email
from .base import IsolatedAuthAPITestCase


class PasswordResetTests(IsolatedAuthAPITestCase):
    def setUp(self):
        self.barangay = Barangay.objects.create(name="Password Reset Barangay")
        self.user = User.objects.create_user(
            username="reset_resident",
            email="resident_reset@example.com",
            password="InitialPassword123!",
            role=User.Role.RESIDENT,
            barangay=self.barangay,
        )

    def test_password_reset_request_dispatches_async_task_and_returns_generic_200(self):
        with patch('gridy_auth.views.password_reset.send_password_reset_email.delay') as mock_task:
            response = self.client.post(
                reverse("password_reset_request"),
                {"email": self.user.email},
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                response.data["detail"],
                "If your email is registered, a reset link has been sent.",
            )
            mock_task.assert_called_once()
            call_args = mock_task.call_args[0]
            self.assertEqual(call_args[0], self.user.email)
            self.assertIn("reset-password?uidb64=", call_args[1])

    def test_password_reset_ignores_inactive_duplicate_email(self):
        User.objects.create_user(
            username="inactive_admin_same_email",
            email=self.user.email,
            password="OldPassword123!",
            role=User.Role.ADMIN,
            is_active=False,
        )

        with patch('gridy_auth.views.password_reset.send_password_reset_email.delay') as mock_task:
            response = self.client.post(
                reverse("password_reset_request"),
                {"email": self.user.email},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_task.assert_called_once()
        self.assertEqual(mock_task.call_args.args[0], self.user.email)

    def test_password_reset_request_unmatched_email_does_not_dispatch_task(self):
        with patch('gridy_auth.views.password_reset.send_password_reset_email.delay') as mock_task:
            response = self.client.post(
                reverse("password_reset_request"),
                {"email": "unregistered@example.com"},
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                response.data["detail"],
                "If your email is registered, a reset link has been sent.",
            )
            mock_task.assert_not_called()

    def test_password_reset_request_survives_dispatch_exception_without_logging_secrets(self):
        with patch(
            'gridy_auth.views.password_reset.send_password_reset_email.delay',
            side_effect=Exception("Task worker pool error"),
        ):
            with self.assertLogs('gridy_auth.views.password_reset', level=logging.ERROR) as cm:
                response = self.client.post(
                    reverse("password_reset_request"),
                    {"email": self.user.email},
                    format="json",
                )
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(
                    response.data["detail"],
                    "If your email is registered, a reset link has been sent.",
                )
                self.assertTrue(any("Password reset dispatch failed (Exception)." in log for log in cm.output))
                for log in cm.output:
                    self.assertNotIn(self.user.email, log)

    def test_send_password_reset_email_task_uses_default_from_email(self):
        with patch('gridy_auth.tasks.send_mail', return_value=1) as mock_send_mail:
            result = send_password_reset_email.__wrapped__(
                "test@example.com",
                "https://example.com/reset-password?uidb64=abc&token=xyz",
            )
            self.assertEqual(result, 1)
            mock_send_mail.assert_called_once()
            call_kwargs = mock_send_mail.call_args.kwargs
            self.assertEqual(call_kwargs.get("from_email"), settings.DEFAULT_FROM_EMAIL)
            self.assertEqual(call_kwargs.get("recipient_list"), ["test@example.com"])
            self.assertIn("copy the complete link", call_kwargs.get("message", ""))
            self.assertIn("Password Recovery", call_kwargs.get("message", ""))

    def test_send_password_reset_email_task_survives_exception_without_logging_secrets(self):
        with patch('gridy_auth.tasks.send_mail', side_effect=Exception("SMTP connection timeout")):
            with self.assertLogs('gridy_auth.tasks', level=logging.ERROR) as cm:
                result = send_password_reset_email.__wrapped__(
                    "secret_user@example.com",
                    "https://example.com/reset-password?uidb64=abc&token=secret-token-123",
                )
                self.assertIsNone(result)
                self.assertTrue(any("Password reset email delivery failed (Exception)." in log for log in cm.output))
                for log in cm.output:
                    self.assertNotIn("secret_user@example.com", log)
                    self.assertNotIn("secret-token-123", log)
