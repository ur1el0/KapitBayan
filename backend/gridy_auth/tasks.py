import threading
import functools
import logging
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)

def async_task(func):
    """
    Decorator that executes a function in a background daemon thread,
    providing .delay() compatibility so call sites work seamlessly without Celery or Redis.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=func, args=args, kwargs=kwargs, daemon=True)
        try:
            thread.start()
        except Exception as exc:
            logger.error(
                "Could not start background task %s (%s).",
                func.__name__,
                type(exc).__name__,
            )
            return None
        return thread
    
    wrapper.delay = wrapper
    return wrapper

@async_task
def send_welcome_email(user_email, full_name):
    """
    Sends a welcome email to newly registered users in a non-blocking background thread.
    """
    try:
        subject = "Welcome to KapitBayan!"
        message = f"Hello {full_name}, \n\nWelcome to KapitBayan. We are excited to have you on board!"
        sent_count = send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user_email],
            fail_silently=False,
        )
        if sent_count != 1:
            logger.error("Email backend did not accept the welcome message.")
        return sent_count
    except Exception as exc:
        logger.error("Welcome email delivery failed (%s).", type(exc).__name__)

@async_task
def send_barangay_approval_email(user_email, applicant_name, barangay_name):
    """Tell the verified first official how to establish their login password."""
    try:
        reset_page = f"{settings.FRONTEND_URL.rstrip('/')}/forgot-password"
        subject = "KapitBayan official account approved"
        message = (
            f"Hello {applicant_name},\n\n"
            f"Your official account for {barangay_name} was approved and is ready. "
            "No password was created for you. Visit the KapitBayan "
            f"password recovery page ({reset_page}) and request a private reset "
            "link using this email address to set your password.\n\n"
            "KapitBayan staff will never ask you to send your password or payment-account credentials."
        )
        sent_count = send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user_email],
            fail_silently=False,
        )
    except Exception as exc:
        logger.error("Barangay approval email delivery failed (%s).", type(exc).__name__)
        return

    if sent_count != 1:
        logger.error("Email backend did not accept the barangay approval message.")
    return sent_count


@async_task
def send_field_official_setup_email(user_email, full_name, barangay_name, setup_link):
    """Send a private one-time password setup link to a new Field Official."""
    try:
        subject = "KapitBayan Field Official account setup"
        message = (
            f"Hello {full_name},\n\n"
            f"A Field Official account was created for you by Barangay {barangay_name}. "
            "Set your password using the private link below:\n\n"
            f"{setup_link}\n\n"
            "This link expires and can be used once. If it expires or you did not request "
            "this account, contact your Barangay Admin. Do not share the link or your password."
        )
        sent_count = send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user_email],
            fail_silently=False,
        )
    except Exception as exc:
        logger.error("Field official setup email delivery failed (%s).", type(exc).__name__)
        return

    if sent_count != 1:
        logger.error("Email backend did not accept the field official setup message.")
    return sent_count


@async_task
def send_barangay_admin_setup_email(user_email, full_name, barangay_name, setup_link):
    """Send a private one-time password setup link to a new Barangay Admin."""
    try:
        subject = "KapitBayan Barangay Admin account setup"
        message = (
            f"Hello {full_name},\n\n"
            f"A Barangay Admin account for Barangay {barangay_name} is ready. "
            "Set your password using the private link below:\n\n"
            f"{setup_link}\n\n"
            "This link expires and can be used once. If it expires or you did not request "
            "this account, contact your Barangay Admin. Do not share the link or your password."
        )
        sent_count = send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user_email],
            fail_silently=False,
        )
    except Exception as exc:
        logger.error("Barangay Admin setup email delivery failed (%s).", type(exc).__name__)
        return

    if sent_count != 1:
        logger.error("Email backend did not accept the Barangay Admin setup message.")
    return sent_count


@async_task
def send_barangay_application_verification_email(
    user_email, applicant_name, barangay_name, verification_link
):
    """Send the one-time email-ownership link for a pending Barangay application."""
    try:
        sent_count = send_mail(
            subject="Verify your official email for KapitBayan",
            message=(
                f"Hello {applicant_name},\n\n"
                f"A first Admin application was submitted for Barangay {barangay_name} "
                "using this email address. Confirm that you can receive mail here by "
                "opening the link and selecting Verify email:\n\n"
                f"{verification_link}\n\n"
                "This link expires after the configured password-reset timeout and can "
                "verify this application only once. Email verification does not approve "
                "the Barangay Admin account; DILG must still review the application. "
                "If you did not submit this request, ignore this email."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            fail_silently=False,
        )
    except Exception as exc:
        logger.error(
            "Barangay application verification email delivery failed (%s).",
            type(exc).__name__,
        )
        return None

    if sent_count != 1:
        logger.error("Email backend did not accept the Barangay application verification message.")
    return sent_count


@async_task
def send_password_reset_email(user_email, reset_link):
    """
    Sends password reset email in a non-blocking background thread.
    Avoids logging recipient email addresses or sensitive reset tokens.
    """
    try:
        subject = "KapitBayan: Password Reset Request"
        message = (
            f"Hello,\n\n"
            f"You requested a password reset. Click the link below to set a new password:\n\n"
            f"{reset_link}\n\n"
            f"If you did not request this, please ignore this email."
        )
        sent_count = send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            fail_silently=False,
        )
        if sent_count != 1:
            logger.error("Email backend did not accept the password reset message.")
        return sent_count
    except Exception as exc:
        logger.error("Password reset email delivery failed (%s).", type(exc).__name__)
        return None
