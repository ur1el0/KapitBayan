"""Persistent, barangay-scoped in-app alerts for active Barangay Admins."""

from gridy_auth.models import User
from gridy_communications.models import AdminNotification


EVENT_COPY = {
    AdminNotification.Type.QUEUE: (
        "New queue ticket",
        "A resident has requested a queue ticket.",
    ),
    AdminNotification.Type.DOCUMENT: (
        "New document request",
        "A resident submitted a document request.",
    ),
    AdminNotification.Type.REPORT: (
        "New issue report",
        "A resident submitted an issue report.",
    ),
    AdminNotification.Type.REGISTRATION: (
        "Resident registration pending review",
        "A new resident account is pending verification.",
    ),
}


def notify_barangay_admins(*, barangay_id, notification_type, source='resident'):
    """Create an in-app event for active Admins assigned to one Barangay.

    Call this inside the same transaction as the event being recorded. Messages
    intentionally omit resident names, contact information, and report content.
    """
    if not barangay_id or notification_type not in EVENT_COPY:
        return 0

    title, message = EVENT_COPY[notification_type]
    if source == 'kiosk':
        message = message.replace('A resident ', 'A walk-in visitor ')
    admin_ids = User.objects.filter(
        role=User.Role.ADMIN,
        barangay_id=barangay_id,
        is_active=True,
    ).values_list('id', flat=True)
    created = AdminNotification.objects.bulk_create([
        AdminNotification(
            user_id=admin_id,
            notification_type=notification_type,
            title=title,
            message=message,
        )
        for admin_id in admin_ids
    ])
    return len(created)
