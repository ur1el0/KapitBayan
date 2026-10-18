"""Authentication guards for production-only blocked demo accounts."""

from django.conf import settings
from django.contrib.auth.backends import ModelBackend
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import (
    JWTAuthentication,
    default_user_authentication_rule,
)


_RESERVED_DEMO_EMAIL_DOMAINS = ("gridy.local", "example.invalid")


def is_production_test_account(user):
    """Return whether ``user`` is explicitly reserved as a test identity.

    This policy is disabled in debug mode so local seed accounts and test
    fixtures remain usable. Production-only accounts are configured through
    ``BLOCKED_PRODUCTION_LOGIN_USERNAMES``; credentials are never embedded in
    application code.
    """
    if settings.DEBUG or user is None:
        return False

    username = (getattr(user, "username", "") or "").strip().casefold()
    blocked_usernames = {
        str(value).strip().casefold()
        for value in getattr(settings, "BLOCKED_PRODUCTION_LOGIN_USERNAMES", ())
        if str(value).strip()
    }
    if username and username in blocked_usernames:
        return True

    email = (getattr(user, "email", "") or "").strip().casefold()
    domain = email.rsplit("@", 1)[-1] if "@" in email else ""
    return any(
        domain == reserved_domain or domain.endswith(f".{reserved_domain}")
        for reserved_domain in _RESERVED_DEMO_EMAIL_DOMAINS
    )


def production_user_authentication_rule(user):
    """Reject inactive, test, and retired-role users at token issuance."""
    return (
        default_user_authentication_rule(user)
        and not is_production_test_account(user)
        and getattr(user, "role", None) in {"ADMIN", "RESIDENT", "FIELD_OFFICIAL"}
    )


class ProductionSafeModelBackend(ModelBackend):
    """Apply the same production test-account rule to Django session logins."""

    def user_can_authenticate(self, user):
        return (
            super().user_can_authenticate(user)
            and not is_production_test_account(user)
            and getattr(user, "role", None) in {"ADMIN", "RESIDENT", "FIELD_OFFICIAL"}
        )


class ProductionSafeJWTAuthentication(JWTAuthentication):
    """Reject previously issued access tokens for production test accounts."""

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if (
            is_production_test_account(user)
            or user.role not in {"ADMIN", "RESIDENT", "FIELD_OFFICIAL"}
        ):
            raise AuthenticationFailed(
                "User is inactive or deleted.",
                code="user_inactive",
            )
        return user
