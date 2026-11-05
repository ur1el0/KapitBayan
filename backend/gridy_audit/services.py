import ipaddress

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
    Return a syntactically valid forwarded or direct IP address.

    Deployments must ensure the trusted ingress overwrites forwarded headers;
    this value is an audit hint, not proof of a user's physical location.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        forwarded_ip = _validated_ip(x_forwarded_for.split(',', 1)[0])
        if forwarded_ip:
            return forwarded_ip
    return _validated_ip(request.META.get('REMOTE_ADDR'))


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
