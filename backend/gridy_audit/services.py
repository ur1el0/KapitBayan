import ipaddress

from django.conf import settings

from .models import AuditLog


def _validated_ip(value):
    if not value:
        return None
    try:
        return str(ipaddress.ip_address(value.strip()))
    except (AttributeError, ValueError):
        return None


def get_client_ip(request):
    """
    Return a syntactically valid client IP respecting configured proxy trust.

    When TRUST_X_FORWARDED_FOR is enabled:
    - TRUSTED_PROXY_COUNT == 0 preserves Render's overwritten leftmost client IP.
    - TRUSTED_PROXY_COUNT > 0 reads N hops from the right to ignore spoofed prefixes.
    """
    if getattr(settings, "TRUST_X_FORWARDED_FOR", True):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            entries = [part.strip() for part in x_forwarded_for.split(",") if part.strip()]
            if entries:
                try:
                    trusted_proxy_count = max(
                        int(getattr(settings, "TRUSTED_PROXY_COUNT", 0) or 0),
                        0,
                    )
                except (TypeError, ValueError):
                    trusted_proxy_count = 0
                if trusted_proxy_count > 0:
                    candidate = (
                        entries[-trusted_proxy_count]
                        if len(entries) >= trusted_proxy_count
                        else entries[0]
                    )
                else:
                    candidate = entries[0]
                forwarded_ip = _validated_ip(candidate)
                if forwarded_ip:
                    return forwarded_ip
    return _validated_ip(request.META.get("REMOTE_ADDR"))


def log_action(user, action_type, description, request=None):
    """
    Writes a security/administrative action history record to the database
    """
    ip_address = None
    if request:
        ip_address = get_client_ip(request)

    return AuditLog.objects.create(
        action_by=user,
        action_type=action_type,
        description=description,
        ip_address=ip_address
    )
