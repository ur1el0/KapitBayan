from collections import Counter

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from gridy_auth.lifecycle import erase_user_account
from gridy_auth.management.commands.demo_seed_safety import (
    require_local_demo_database,
)
from gridy_auth.models import User


class Command(BaseCommand):
    help = (
        "Preview or erase every local user account using the existing erasure lifecycle. "
        "This command is disabled outside local DEBUG databases."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--execute",
            action="store_true",
            help="Erase all user accounts. Without this flag, only show a preview.",
        )
        parser.add_argument(
            "--confirm-database",
            help="Exact database name shown by the preview; required with --execute.",
        )

    def handle(self, *args, **options):
        database_name = str(connection.settings_dict.get("NAME") or "")
        users = User.objects.all()
        account_count = users.count()
        roles = Counter(users.values_list("role", flat=True))
        role_summary = ", ".join(
            f"{role}={count}" for role, count in sorted(roles.items())
        ) or "none"

        self.stdout.write(f"Database: {database_name or '(unnamed)'}")
        self.stdout.write(f"Database engine: {connection.vendor}")
        self.stdout.write(f"Accounts to erase: {account_count} ({role_summary})")
        self.stdout.write(
            "Service document and aid history is retained by the account-erasure workflow."
        )

        if not options["execute"]:
            self.stdout.write("Preview only. No database rows were changed.")
            return

        require_local_demo_database(confirmed=True)
        if not options["confirm_database"]:
            raise CommandError(
                "Pass --confirm-database with the exact database name printed above."
            )
        if options["confirm_database"] != database_name:
            raise CommandError(
                "Database confirmation does not match the configured database name."
            )

        erased_count = 0
        with transaction.atomic():
            # Select one account at a time so the command does not load the full
            # user table into memory. The lifecycle helper handles dependent data.
            while True:
                user = User.objects.order_by("pk").first()
                if user is None:
                    break
                account_id = user.pk
                erase_user_account(
                    user,
                    reason=(
                        "Local account reset command: account erased; "
                        f"target account ID={account_id}."
                    ),
                    actor=user,
                )
                erased_count += 1

        self.stdout.write(self.style.SUCCESS(f"Erased {erased_count} user accounts."))
