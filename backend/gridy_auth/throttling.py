"""Database-backed DRF scoped throttling for multi-worker deployments."""

import secrets
from datetime import datetime, timezone as datetime_timezone

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.crypto import salted_hmac
from rest_framework.throttling import ScopedRateThrottle

from gridy_audit.services import get_client_ip
from gridy_auth.models import APIRateLimitWindow


class SharedDatabaseScopedRateThrottle(ScopedRateThrottle):
    """Enforce DRF rolling request budgets across Gunicorn workers.

    A short row lock serializes updates for one hashed scope/client pair. This
    preserves DRF's rolling-window behavior while sharing state through the
    application's existing PostgreSQL database. It is an application abuse
    control, not an edge DDoS defense.
    """

    cleanup_sample_rate = 100
    cleanup_batch_size = 100

    def allow_request(self, request, view):
        self.scope = getattr(view, self.scope_attr, None)
        if not self.scope:
            return True

        self.rate = self.get_rate()
        if self.rate is None:
            return True

        self.num_requests, self.duration = self.parse_rate(self.rate)
        self.now = self.timer()
        now_datetime = datetime.fromtimestamp(self.now, tz=datetime_timezone.utc)
        self.history = []
        key = self.get_cache_key(request, view)

        with transaction.atomic():
            window = self._get_or_create_locked_window(key, now_datetime)
            stored_history = window.history if isinstance(window.history, list) else []
            cutoff = self.now - self.duration
            history = sorted(
                (
                    float(timestamp)
                    for timestamp in stored_history
                    if self._is_timestamp(timestamp) and float(timestamp) > cutoff
                ),
                reverse=True,
            )[: self.num_requests]

            self.history = history
            allowed = len(history) < self.num_requests
            if allowed:
                self.history.insert(0, self.now)

            if allowed or history != stored_history:
                window.history = self.history
                window.expires_at = self._expiration_for(self.history)
                window.save(update_fields=["history", "expires_at"])

        self._prune_expired_windows(now_datetime)
        return allowed

    @staticmethod
    def _is_timestamp(value):
        try:
            float(value)
        except (TypeError, ValueError, OverflowError):
            return False
        return True

    def _expiration_for(self, history):
        if not history:
            return datetime.fromtimestamp(self.now + self.duration, tz=datetime_timezone.utc)
        oldest_request = history[-1]
        return datetime.fromtimestamp(
            oldest_request + self.duration,
            tz=datetime_timezone.utc,
        )

    def _get_or_create_locked_window(self, key, now_datetime):
        try:
            return APIRateLimitWindow.objects.select_for_update().get(pk=key)
        except APIRateLimitWindow.DoesNotExist:
            try:
                # The nested savepoint lets a concurrent insert win safely
                # without leaving the surrounding transaction unusable.
                with transaction.atomic():
                    return APIRateLimitWindow.objects.create(
                        window_key=key,
                        history=[],
                        expires_at=now_datetime,
                    )
            except IntegrityError:
                return APIRateLimitWindow.objects.select_for_update().get(pk=key)

    def get_cache_key(self, request, view):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            identity = f"user:{user.pk}"
        else:
            identity = f"ip:{self.get_ident(request)}"

        scope_and_identity = f"{self.scope}:{identity}"
        return salted_hmac(
            "gridy.api-throttle",
            scope_and_identity,
            secret=settings.SECRET_KEY,
            algorithm="sha256",
        ).hexdigest()

    def get_ident(self, request):
        """Resolve client IP through the shared proxy-trust-aware audit helper."""
        return get_client_ip(request) or request.META.get("REMOTE_ADDR", "")

    def _prune_expired_windows(self, now_datetime):
        if secrets.randbelow(self.cleanup_sample_rate) != 0:
            return

        expired_keys = list(
            APIRateLimitWindow.objects.filter(expires_at__lte=now_datetime)
            .order_by("expires_at")
            .values_list("window_key", flat=True)[: self.cleanup_batch_size]
        )
        if expired_keys:
            APIRateLimitWindow.objects.filter(
                window_key__in=expired_keys,
                expires_at__lte=now_datetime,
            ).delete()
