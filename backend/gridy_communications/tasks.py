import logging
from gridy_auth.tasks import async_task
from .services import (
    send_email_notification_to_user,
    send_notification_to_user,
)

logger = logging.getLogger(__name__)

@async_task
def send_notification_to_user_task(user_id, title, body, data=None):
    """
    Background task to send a push notification to a specific user without Celery.
    """
    from gridy_auth.models import User
    try:
        user = User.objects.get(id=user_id)
        push_responses = send_notification_to_user(user, title, body, data)
        email_sent = send_email_notification_to_user(user, title, body)
        if not user.email_alerts:
            logger.info("Notification email skipped because the recipient opted out.")
        elif not user.email:
            logger.info("Notification email skipped because the recipient has no address.")
        elif email_sent:
            logger.info("Notification email accepted by the configured backend.")
        else:
            logger.warning("Notification email was not accepted by the configured backend.")
        return {
            "status": "success",
            "push_sent": len(push_responses),
            "email_sent": email_sent,
        }
    except User.DoesNotExist:
        logger.warning("Push notification recipient no longer exists.")
        return {"status": "error", "error": "User not found"}
    except Exception as exc:
        logger.error("Background user notification failed (%s).", type(exc).__name__)
        return {"status": "error", "error": "Notification delivery failed"}


@async_task
def send_announcement_notification_task(barangay_id, announcement_id, title):
    """Fan out an announcement to opted-in residents of its own barangay."""
    from gridy_auth.models import User

    recipients = User.objects.filter(
        role=User.Role.RESIDENT,
        barangay_id=barangay_id,
        push_alerts=True,
    ).prefetch_related("fcm_devices")

    try:
        for user in recipients.iterator(chunk_size=100):
            send_notification_to_user(
                user,
                title="Barangay Announcement",
                body=title,
                data={
                    "type": "announcement",
                    "announcement_id": str(announcement_id),
                },
            )
    except Exception as exc:
        logger.error(
            "Barangay announcement push fanout failed (%s).",
            type(exc).__name__,
        )
