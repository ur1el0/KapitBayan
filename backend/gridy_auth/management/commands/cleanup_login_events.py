from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.utils import timezone

from gridy_auth.models import LoginEvent


class Command(BaseCommand):
    help = "Delete successful sign-in history older than the configured retention period."

    def handle(self, *args, **options):
        if connection.vendor != "postgresql":
            raise CommandError("Login-event retention cleanup requires PostgreSQL.")

        if LoginEvent._meta.db_table not in connection.introspection.table_names():
            raise CommandError(
                "LoginEvent table is missing. Apply the gridy_auth login-event migration first."
            )

        retention_days = settings.LOGIN_EVENT_RETENTION_DAYS
        cutoff = timezone.now() - timedelta(days=retention_days)
        deleted_count, _ = LoginEvent.objects.filter(created_at__lt=cutoff).delete()
        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {deleted_count} expired login-history record(s) "
                f"older than {retention_days} days."
            )
        )
