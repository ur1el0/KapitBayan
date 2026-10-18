from django.db import transaction
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .models import IssueReport
from gridy_communications.tasks import send_notification_to_user_task

@receiver(pre_save, sender=IssueReport)
def capture_old_status(sender, instance, **kwargs):
    """
    Captures the previous status before the save happends to detect changes.
    """
    if instance.pk:
        try:
            instance._old_status = IssueReport.objects.get(pk=instance.pk).status
        except IssueReport.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None

@receiver(post_save, sender=IssueReport)
def notify_issue_update(sender, instance, created, **kwargs):
    """
    Fires a Push Notification if the status was changed by an admin.
    """
    old_status = getattr(instance, '_old_status', None)

    if old_status != instance.status and  not created:

        reporter_id = instance.reporter_id
        title = "Issue Report Update"
        body = f"Your issue report '{instance.title}' has been marked as {instance.get_status_display()}."
        data = {"type": "issue", "report_id": str(instance.pk)}
        transaction.on_commit(
            lambda: send_notification_to_user_task.delay(
                user_id=reporter_id,
                title=title,
                body=body,
                data=data,
            )
        )
