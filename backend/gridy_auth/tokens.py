from django.contrib.auth.tokens import PasswordResetTokenGenerator


class BarangayApplicationEmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """Single-use verification tokens tied to one pending application email."""

    key_salt = "gridy_auth.tokens.BarangayApplicationEmailVerificationTokenGenerator"

    @staticmethod
    def _pending_application(user):
        from gridy_auth.models import BarangayApplication

        return BarangayApplication.objects.filter(
            applicant_user=user,
            status=BarangayApplication.Status.PENDING,
            email_verified_at__isnull=True,
        ).exclude(proof_of_authority="").first()

    def make_token(self, user):
        if self._pending_application(user) is None:
            return ""
        return super().make_token(user)

    def check_token(self, user, token):
        if not token or self._pending_application(user) is None:
            return False
        return super().check_token(user, token)

    def _make_hash_value(self, user, timestamp):
        application = self._pending_application(user)
        if application is None:
            return ""

        base_value = super()._make_hash_value(user, timestamp)
        sent_at = application.email_verification_sent_at
        return (
            f"{base_value}{application.pk}{application.status}"
            f"{application.applicant_email.casefold()}"
            f"{sent_at.isoformat() if sent_at else ''}"
        )


barangay_application_email_token_generator = BarangayApplicationEmailVerificationTokenGenerator()
