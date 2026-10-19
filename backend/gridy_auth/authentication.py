"""Authentication guards for production-only blocked demo accounts."""

import re

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
        and getattr(user, "role", None) in {"ADMIN", "RESIDENT", "FIELD_OFFICIAL", "BARANGAY_OPERATOR"}
    )


class ProductionSafeModelBackend(ModelBackend):
    """Apply production demo-account and supported-role checks to Django auth."""

    def user_can_authenticate(self, user):
        return (
            super().user_can_authenticate(user)
            and not is_production_test_account(user)
            and getattr(user, "role", None) in {"ADMIN", "RESIDENT", "FIELD_OFFICIAL", "BARANGAY_OPERATOR"}
        )

class ProductionSafeJWTAuthentication(JWTAuthentication):
    """Reject test accounts and confine operator tokens to platform support."""

    _OPERATOR_READ_PATHS = {
        "/api/v1/auth/me",
        "/api/v1/auth/sessions",
        "/api/v1/auth/platform/barangay-applications",
        "/api/v1/auth/platform/accounts",
    }
    _OPERATOR_POST_PATHS = {
        "/api/v1/auth/logout",
        "/api/v1/auth/platform/barangay-applications",
    }

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None

        user, _token = result
        if user.role == "BARANGAY_OPERATOR":
            path = request.path_info.rstrip("/") or "/"
            method = request.method.upper()
            application_base = "/api/v1/auth/platform/barangay-applications"
            account_base = "/api/v1/auth/platform/accounts"
            is_application_detail_route = bool(
                re.fullmatch(rf"{re.escape(application_base)}/[0-9]+", path)
            )
            is_application_proof_route = bool(
                re.fullmatch(rf"{re.escape(application_base)}/[0-9]+/proof", path)
            )
            is_application_decision_route = bool(
                re.fullmatch(rf"{re.escape(application_base)}/[0-9]+/(approve|reject)", path)
            )
            is_account_detail_route = bool(re.fullmatch(rf"{re.escape(account_base)}/\d+", path))
            is_account_action_route = bool(re.fullmatch(
                rf"{re.escape(account_base)}/\d+/(send-password-link|set-active)", path
            ))
            allowed = (
                (path in self._OPERATOR_READ_PATHS and method in {"GET", "HEAD", "OPTIONS"})
                or (path in self._OPERATOR_POST_PATHS and method == "POST")
                or (is_application_detail_route and method in {"GET", "HEAD", "OPTIONS"})
                or (is_application_proof_route and method in {"GET", "HEAD", "OPTIONS"})
                or (is_application_decision_route and method in {"POST", "OPTIONS"})
                or (is_account_detail_route and method in {"GET", "HEAD", "OPTIONS", "PATCH"})
                or (is_account_action_route and method in {"POST", "OPTIONS"})
            )
            if not allowed:
                raise AuthenticationFailed(
                    "Barangay Operator accounts are limited to onboarding and account support.",
                    code="barangay_operator_scope_limited",
                )
        return result

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if (
            is_production_test_account(user)
            or user.role not in {"ADMIN", "RESIDENT", "FIELD_OFFICIAL", "BARANGAY_OPERATOR"}
        ):
            raise AuthenticationFailed(
                "User is inactive or deleted.",
                code="user_inactive",
            )
        return user
