from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from gridy_auth.tasks import (
    send_barangay_approval_email,
    send_password_reset_email,
    send_welcome_email,
)


class EmailBrandingTests(SimpleTestCase):
    @patch("gridy_auth.tasks.send_mail", return_value=1)
    def test_welcome_email_uses_kapitbayan_name(self, mock_send_mail):
        result = send_welcome_email.__wrapped__(
            "resident@example.invalid",
            "Test Resident",
        )

        self.assertEqual(result, 1)
        subject, message = mock_send_mail.call_args.args[:2]
        self.assertEqual(subject, "Welcome to KapitBayan!")
        self.assertIn("Welcome to KapitBayan.", message)

    @override_settings(FRONTEND_URL="https://app.example.test")
    @patch("gridy_auth.tasks.send_mail", return_value=1)
    def test_barangay_approval_email_uses_kapitbayan_name(self, mock_send_mail):
        result = send_barangay_approval_email.__wrapped__(
            "official@example.invalid",
            "Test Official",
            "Barangay Test",
        )

        self.assertEqual(result, 1)
        subject, message = mock_send_mail.call_args.args[:2]
        self.assertEqual(subject, "KapitBayan official account approved")
        self.assertIn("KapitBayan password recovery page", message)
        self.assertIn("KapitBayan staff will never ask", message)

    @patch("gridy_auth.tasks.send_mail", return_value=1)
    def test_password_reset_email_uses_kapitbayan_brand(self, mock_send_mail):
        result = send_password_reset_email.__wrapped__(
            "resident@example.invalid",
            "https://app.example.test/reset-password?uidb64=abc&token=secret",
        )

        self.assertEqual(result, 1)
        self.assertEqual(
            mock_send_mail.call_args.kwargs["subject"],
            "KapitBayan: Password Reset Request",
        )
        self.assertIn(
            "https://app.example.test/reset-password",
            mock_send_mail.call_args.kwargs["message"],
        )
