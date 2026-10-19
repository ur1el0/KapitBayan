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
    """Reject inactive, test, and unsupported-role users at token issuance."""
    return (
        default_user_authentication_rule(user)
        and not is_production_test_account(user)
        and getattr(user, "role", None) in {"ADMIN", "RESIDENT", "FIELD_OFFICIAL", "DILG_ADMIN"}
    )


class ProductionSafeModelBackend(ModelBackend):
    """Guard official accounts and keep non-superusers on the API token flow."""

    def authenticate(self, request=None, **credentials):
        user = super().authenticate(request, **credentials)
        if (
            user
            and not user.is_superuser
            and user.role in {"ADMIN", "FIELD_OFFICIAL", "DILG_ADMIN"}
        ):
            path = getattr(request, "path_info", "").rstrip("/")
            if path != "/api/v1/auth/login":
                return None
        return user

    def user_can_authenticate(self, user):
        return (
            super().user_can_authenticate(user)
            and not is_production_test_account(user)
            and getattr(user, "role", None) in {"ADMIN", "RESIDENT", "FIELD_OFFICIAL", "DILG_ADMIN"}
        )

    def get_user(self, user_id):
        # Official accounts use the email-aware API flow, never Django sessions.
        user = super().get_user(user_id)
        if (
            user
            and not user.is_superuser
            and user.role in {"ADMIN", "FIELD_OFFICIAL", "DILG_ADMIN"}
        ):
            return None
        return user


class ProductionSafeJWTAuthentication(JWTAuthentication):
    """Reject test accounts and confine DILG tokens to onboarding review."""

    _DILG_READ_PATHS = {
        "/api/v1/auth/me",
        "/api/v1/auth/sessions",
        "/api/v1/auth/platform/barangay-applications",
    }
    _DILG_POST_PATHS = {
        "/api/v1/auth/logout",
        "/api/v1/auth/platform/barangay-applications",
    }

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None

        user, _token = result
        if user.role == "DILG_ADMIN":
            path = request.path_info.rstrip("/") or "/"
            method = request.method.upper()
            is_application_route = path.startswith(
                "/api/v1/auth/platform/barangay-applications/"
            )
            allowed = (
                (path in self._DILG_READ_PATHS and method in {"GET", "HEAD", "OPTIONS"})
                or (path in self._DILG_POST_PATHS and method == "POST")
                or (is_application_route and method in {"GET", "HEAD", "OPTIONS", "POST"})
            )
            if not allowed:
                raise AuthenticationFailed(
                    "DILG accounts are limited to Barangay onboarding review.",
                    code="dilg_scope_limited",
                )
        return result

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if (
            is_production_test_account(user)
            or user.role not in {"ADMIN", "RESIDENT", "FIELD_OFFICIAL", "DILG_ADMIN"}
        ):
            raise AuthenticationFailed(
                "User is inactive or deleted.",
                code="user_inactive",
            )
        return user
