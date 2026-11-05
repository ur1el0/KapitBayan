from django.utils import timezone

from .models import User


def is_adult(birth_date, *, today=None):
    today = today or timezone.localdate()
    return (today.year, today.month, today.day) >= (
        birth_date.year + 18,
        birth_date.month,
        birth_date.day,
    )


def guardian_account_is_eligible(guardian, *, barangay_id, today=None):
    """Whether the linked resident account currently meets the minor-review rules."""
    if guardian is None:
        return False

    guardian_user = getattr(guardian, "user", None)
    return bool(
        guardian_user
        and guardian_user.role == User.Role.RESIDENT
        and guardian_user.is_active
        and guardian.is_verified
        and is_adult(guardian.birth_date, today=today)
        and barangay_id is not None
        and guardian_user.barangay_id == barangay_id
    )
