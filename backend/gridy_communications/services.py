import logging

import firebase_admin
from django.conf import settings
from django.core.mail import send_mail
from firebase_admin import messaging

logger = logging.getLogger(__name__)


def send_fcm_notification(device, title, body, data=None):
    """Send a push notification to one registered device."""
    token = device.token
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
    except messaging.UnregisteredError:
        # FCM has permanently invalidated this registration token; remove only
        # the corresponding device so future notifications do not retry it.
        try:
            device.delete()
        except Exception as cleanup_exc:
            logger.error(
                "Could not remove an unregistered FCM device token (%s).",
                type(cleanup_exc).__name__,
            )
        else:
            logger.warning("Removed an unregistered FCM device token.")
        return None
    except messaging.SenderIdMismatchError:
        # This can indicate either a stale token or a server/client project
        # mismatch. Keep the record until the active server project is verified.
        try:
            server_project = firebase_admin.get_app().project_id or "unknown"
        except Exception:
            server_project = "unknown"
        logger.error(
            "FCM device notification delivery failed (SenderIdMismatchError; "
            "server_project=%s). Verify the server and mobile Firebase projects.",
            server_project,
        )
        return None
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
        response = send_fcm_notification(device, title, body, data)
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
