import logging
from django.conf import settings
from django.core.mail import send_mail
from firebase_admin import messaging

logger = logging.getLogger(__name__)


def send_fcm_notification(token, title, body, data=None):
    """
    Sends a push notification to a specific device registration token.
    """
    
    if not token:
        logger.warning("FCM token is empty, skipping notification.")
        return None
        
    formatted_data = None
    
    if data and isinstance(data, dict):
        formatted_data = {str(k): str(v) for k, v in data.items()}
    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        data=formatted_data,
        token=token
    )
    try:
        response = messaging.send(message)
        logger.info(f"Successfully sent FCM notification: {response}")
        return response
    except Exception as exc:
        logger.error("FCM device notification delivery failed (%s).", type(exc).__name__)
        return None

def send_notification_to_user(user, title, body, data=None):
    """
    Sends a push notification to the user's registered devices when they opted in.
    """

    if not user.push_alerts:
        logger.info("Push notification skipped because the recipient opted out.")
        return []

    devices = user.fcm_devices.all()
    if not devices.exists():
        logger.info("No registered devices for push notification recipient.")
        return []

    responses = []
    for device in devices:
        response = send_fcm_notification(device.token, title, body, data)
        if response:
            responses.append(response)
    return responses


def send_email_notification_to_user(user, title, body):
    """Send a notification email when the user has opted in and has an address."""
    if not user.email_alerts or not user.email:
        return False

    safe_title = " ".join((title or "KapitBayan notification").splitlines())[:150]
    message = (
        f"{body}\n\n"
        "Open the KapitBayan app or website to review the latest information."
    )
    try:
        sent_count = send_mail(
            f"KapitBayan: {safe_title}",
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
    except Exception as exc:
        logger.error("Notification email delivery failed (%s).", type(exc).__name__)
        return False

    if sent_count != 1:
        logger.warning("Email backend did not accept the notification message.")
        return False
    return True
