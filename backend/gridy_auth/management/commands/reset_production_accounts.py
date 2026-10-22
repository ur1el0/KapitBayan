"""Preview and erase production accounts except one explicitly retained operator."""

from hashlib import sha256
import json

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, connections, models, transaction
from django.db.models import Count, Q, Subquery

from gridy_audit.models import AuditLog
from gridy_auth.lifecycle import (
    PRIVATE_MEDIA_STORAGE_MODELS,
    attempt_private_media_cleanup_safely,
    erase_user_account,
    queue_private_media_cleanup,
)
from gridy_auth.models import User


CONFIRMATION_PHRASE = "DELETE ALL OTHER ACCOUNTS AND LINKED SERVICE RECORDS"
SERVICE_USER_RELATIONS = {
    "gridy_auth.BarangayApplication": (
        "applicant_user",
        "created_admin",
        "reviewed_by",
    ),
    "gridy_services.AidRequest": ("requester", "reviewed_by"),
    "gridy_services.DocumentRequest": ("user", "fee_assessed_by"),
    "gridy_services.QueueTicket": ("user",),
    "token_blacklist.OutstandingToken": ("user",),
}
AUDIT_RELATION = ("gridy_audit.AuditLog", "action_by")
SIGNAL_CLEANED_MEDIA_FIELDS = {
    "gridy_services.DocumentRequest": ("payment_proof_image",),
}
SERVICE_DELETE_ORDER = (
    "gridy_services.QueueTicket",
    "gridy_services.DocumentRequest",
    "gridy_services.AidRequest",
    "gridy_auth.BarangayApplication",
    "token_blacklist.OutstandingToken",
)
KNOWN_DELETE_POLICIES = {
    models.CASCADE,
    models.SET_NULL,
    models.SET_DEFAULT,
    models.PROTECT,
    models.RESTRICT,
    models.DO_NOTHING,
}


class Command(BaseCommand):
    help = (
        "Preview or explicitly erase production user accounts and linked service "
        "records except one named Barangay Operator. Preview is the default."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--preserve-email",
            help="Email of the unique global operator account to retain.",
        )
        parser.add_argument(
            "--execute",
            action="store_true",
            help="Perform the reset after all confirmations and the preview token match.",
        )
        parser.add_argument(
            "--confirm-preserve-email",
            help="Repeat the exact global operator email shown in the reviewed preview.",
        )
        parser.add_argument(
            "--confirm-database",
            help="Exact database name printed by the preview.",
        )
        parser.add_argument(
            "--confirm-host",
            help="Exact PostgreSQL host printed by the preview.",
        )
        parser.add_argument(
            "--backup-reference",
            help="Name or identifier of the verified pre-reset Neon snapshot.",
        )
        parser.add_argument(
            "--expected-plan",
            help="Plan token printed by a preview; execution stops if counts changed.",
        )
        parser.add_argument(
            "--confirm-all-data",
            help=(
                "Must exactly equal: "
                "DELETE ALL OTHER ACCOUNTS AND LINKED SERVICE RECORDS."
            ),
        )
        parser.add_argument(
            "--accept-remaining-media",
            action="store_true",
            help=(
                "Acknowledge that external uploaded files listed in the preview remain "
                "in storage."
            ),
        )

    @staticmethod
    def _host_name(connection):
        value = connection.settings_dict.get("HOST") or ""
        if not isinstance(value, str):
            return ""
        return value.strip().lower().rstrip(".")

    @staticmethod
    def _preserved_operator(email):
        email = str(email or "").strip()
        if not email:
            raise CommandError(
                "--preserve-email is required; specify the global operator account to keep."
            )
        matches = (
            User.objects.using(DEFAULT_DB_ALIAS)
            .filter(email__iexact=email)
        )
        if matches.count() != 1:
            raise CommandError(
                "--preserve-email must match exactly one account in this database."
            )
        operator = matches.first()
        if operator.role != User.Role.BARANGAY_OPERATOR:
            raise CommandError(
                "The account selected with --preserve-email must have the "
                "BARANGAY_OPERATOR global operator role; barangay admin accounts "
                "are not eligible to be preserved."
            )
        return operator

    @staticmethod
    def _related_queryset(relation, users_to_erase):
        model = relation.related_model
        field = relation.field
        user_ids = Subquery(users_to_erase.values("pk"))
        return model._base_manager.using(DEFAULT_DB_ALIAS).filter(
            **{f"{field.name}__in": user_ids}
        )

    @staticmethod
    def _service_delete_querysets(users_to_erase):
        user_ids = Subquery(users_to_erase.values("pk"))
        querysets = {}

        for model_label, field_names in SERVICE_USER_RELATIONS.items():
            model = apps.get_model(model_label)
            condition = Q()
            for field_name in field_names:
                condition |= Q(**{f"{field_name}__in": user_ids})
            querysets[model_label] = model._base_manager.using(
                DEFAULT_DB_ALIAS
            ).filter(condition)

        document_requests = querysets["gridy_services.DocumentRequest"]
        document_request_ids = Subquery(document_requests.values("pk"))
        queue_model = apps.get_model("gridy_services.QueueTicket")
        querysets["gridy_services.QueueTicket"] = (
            queue_model._base_manager.using(DEFAULT_DB_ALIAS)
            .filter(
                Q(user__in=user_ids)
                | Q(document_request__in=document_request_ids)
            )
        )

        outstanding_tokens = querysets["token_blacklist.OutstandingToken"]
        blacklisted_model = apps.get_model("token_blacklist.BlacklistedToken")
        querysets["token_blacklist.BlacklistedToken"] = (
            blacklisted_model._base_manager.using(DEFAULT_DB_ALIAS)
            .filter(token__in=Subquery(outstanding_tokens.values("pk")))
        )
        return querysets

    @staticmethod
    def _file_count(queryset, field_name):
        return (
            queryset.exclude(**{field_name: ""})
            .exclude(**{f"{field_name}__isnull": True})
            .values(field_name)
            .distinct()
            .count()
        )

    @staticmethod
    def _collect_file_counts(queryset, model, media_cleanup, media_remaining):
        model_label = model._meta.label
        private_fields = PRIVATE_MEDIA_STORAGE_MODELS.get(model_label, ())
        signal_fields = SIGNAL_CLEANED_MEDIA_FIELDS.get(model_label, ())
        for field in model._meta.get_fields():
            if not isinstance(field, models.FileField):
                continue
            count = Command._file_count(queryset, field.name)
            if not count:
                continue
            key = f"{model_label}.{field.name}"
            if field.name in private_fields or field.name in signal_fields:
                media_cleanup[key] = count
            else:
                media_remaining[key] = count

    @staticmethod
    def _queue_private_media_cleanup(queryset, model_label):
        for field_name in PRIVATE_MEDIA_STORAGE_MODELS.get(model_label, ()):
            file_names = (
                queryset.exclude(**{field_name: ""})
                .exclude(**{f"{field_name}__isnull": True})
                .values_list(field_name, flat=True)
                .distinct()
            )
            for file_name in file_names:
                cleanup = queue_private_media_cleanup(
                    model_label, field_name, file_name
                )
                transaction.on_commit(
                    lambda cleanup_id=cleanup.pk: attempt_private_media_cleanup_safely(
                        cleanup_id
                    ),
                    using=DEFAULT_DB_ALIAS,
                )

    def _build_plan(self, connection, preserve_email):
        preserved_operator = self._preserved_operator(preserve_email)
        all_users = User.objects.using(DEFAULT_DB_ALIAS)
        user_queryset = all_users.exclude(pk=preserved_operator.pk)
        role_counts = {
            row["role"] or "(blank)": row["total"]
            for row in user_queryset.values("role")
            .annotate(total=Count("pk"))
            .order_by("role")
        }
        account_summary = {
            "total": user_queryset.count(),
            "roles": role_counts,
            "superusers": user_queryset.filter(is_superuser=True).count(),
            "staff": user_queryset.filter(is_staff=True).count(),
            "inactive": user_queryset.filter(is_active=False).count(),
        }
        preserved_summary = {
            "id": preserved_operator.pk,
            "email": preserved_operator.email,
            "role": preserved_operator.role,
            "is_active": preserved_operator.is_active,
            "is_staff": preserved_operator.is_staff,
            "is_superuser": preserved_operator.is_superuser,
        }

        cascades = {}
        linked_service_deletes = {}
        retained_links = {}
        blocking_links = {}
        media_files = {}
        media_cleanup = {}
        service_delete_querysets = self._service_delete_querysets(user_queryset)
        service_relation_identities = {
            (model_label, field_name)
            for model_label, field_names in SERVICE_USER_RELATIONS.items()
            for field_name in field_names
        }

        for model_label, queryset in service_delete_querysets.items():
            linked_service_deletes[model_label] = queryset.count()
            model = queryset.model
            self._collect_file_counts(
                queryset, model, media_cleanup, media_files
            )

        profile_picture_count = self._file_count(user_queryset, "profile_picture")
        if profile_picture_count:
            media_cleanup["gridy_auth.User.profile_picture"] = profile_picture_count

        seen_relations = set()

        for relation in User._meta.related_objects:
            if relation.many_to_many:
                continue

            related_model = relation.related_model
            field = relation.field
            label = f"{related_model._meta.label}.{field.name}"
            identity = (related_model._meta.label, field.name)
            if identity in seen_relations:
                continue
            seen_relations.add(identity)

            related_rows = self._related_queryset(relation, user_queryset)
            count = related_rows.count()
            if not count:
                continue

            policy = relation.on_delete
            if policy is models.CASCADE:
                cascades[label] = count
                self._collect_file_counts(
                    related_rows, related_model, media_cleanup, media_files
                )
            elif identity in service_relation_identities:
                continue
            elif identity == AUDIT_RELATION:
                retained_links[label] = count
            elif policy in {models.SET_NULL, models.SET_DEFAULT}:
                blocking_links[f"{label} [unreviewed retained relation]"] = count
            else:
                policy_name = getattr(policy, "__name__", repr(policy))
                if policy not in KNOWN_DELETE_POLICIES:
                    policy_name = f"unreviewed:{policy_name}"
                blocking_links[f"{label} [{policy_name}]"] = count

        db_name = str(connection.settings_dict.get("NAME") or "")
        db_host = self._host_name(connection)
        token_payload = {
            "database": db_name,
            "host": db_host,
            "accounts": account_summary,
            "preserved_operator": preserved_summary,
            "cascade": cascades,
            "service_deletes": linked_service_deletes,
            "retained": retained_links,
            "blocking": blocking_links,
            "media": media_files,
            "media_cleanup": media_cleanup,
        }
        encoded = json.dumps(token_payload, sort_keys=True, separators=(",", ":"))
        plan_token = sha256(encoded.encode("utf-8")).hexdigest()[:20]

        return {
            "database": db_name,
            "host": db_host,
            "accounts": account_summary,
            "preserved_operator": preserved_summary,
            "cascade": cascades,
            "service_deletes": linked_service_deletes,
            "retained": retained_links,
            "blocking": blocking_links,
            "media": media_files,
            "media_cleanup": media_cleanup,
            "token": plan_token,
        }

    def _print_plan(self, plan, connection):
        self.stdout.write(f"Database engine: {connection.vendor}")
        self.stdout.write(f"Database name: {plan['database'] or '(unset)'}")
        self.stdout.write(f"Database host: {plan['host'] or '(unset)'}")
        account_summary = plan["accounts"]
        operator = plan["preserved_operator"]
        self.stdout.write(
            "Global operator account preserved: "
            f"email={operator['email']}, id={operator['id']}, "
            f"role={operator['role']}, active={operator['is_active']}, "
            f"staff={operator['is_staff']}, superuser={operator['is_superuser']}"
        )
        self.stdout.write(f"Accounts to erase: {account_summary['total']}")
        self.stdout.write(
            "Accounts by role: "
            + (
                ", ".join(
                    f"{role}={count}"
                    for role, count in sorted(account_summary["roles"].items())
                )
                or "none"
            )
        )
        self.stdout.write(
            "Account flags: "
            f"superusers={account_summary['superusers']}, "
            f"staff={account_summary['staff']}, inactive={account_summary['inactive']}"
        )
        self._print_counts("Direct related rows deleted by CASCADE", plan["cascade"])
        self._print_counts(
            "Linked service and authentication rows deleted by reset",
            plan["service_deletes"],
        )
        self._print_counts(
            "Audit and other approved records retained with user link removed",
            plan["retained"],
        )
        self._print_counts(
            "Files scheduled for cleanup after database commit", plan["media_cleanup"]
        )
        self._print_counts(
            "External file objects left in storage", plan["media"]
        )
        self._print_counts(
            "Relationships requiring manual review", plan["blocking"]
        )
        self.stdout.write(f"Plan token: {plan['token']}")

    def _print_counts(self, title, counts):
        self.stdout.write(f"{title}:")
        if not counts:
            self.stdout.write("  (none)")
            return
        for label, count in sorted(counts.items()):
            self.stdout.write(f"  {label}: {count}")

    def _validate_execution(self, plan, connection, options):
        if settings.DEBUG:
            raise CommandError("Production account reset is disabled while DEBUG=True.")
        if connection.vendor != "postgresql":
            raise CommandError("Production account reset requires PostgreSQL.")
        if not plan["database"] or not plan["host"]:
            raise CommandError(
                "Database name and PostgreSQL host must both be configured."
            )
        if options["confirm_database"] != plan["database"]:
            raise CommandError(
                "--confirm-database must exactly match the database name printed above."
            )
        confirmed_host = str(options["confirm_host"] or "").strip().lower().rstrip(".")
        if confirmed_host != plan["host"]:
            raise CommandError(
                "--confirm-host must exactly match the PostgreSQL host printed above."
            )
        backup_reference = str(options["backup_reference"] or "").strip()
        if not backup_reference:
            raise CommandError(
                "--backup-reference is required; create and verify a pre-reset snapshot first."
            )
        if len(backup_reference) > 255 or any(ord(char) < 32 for char in backup_reference):
            raise CommandError("--backup-reference must be at most 255 printable characters.")
        if options["confirm_all_data"] != CONFIRMATION_PHRASE:
            raise CommandError(
                "--confirm-all-data must exactly equal: " + CONFIRMATION_PHRASE
            )
        if options["confirm_preserve_email"] != plan["preserved_operator"]["email"]:
            raise CommandError(
                "--confirm-preserve-email must exactly match the operator "
                "shown in the preview."
            )
        if not options["expected_plan"]:
            raise CommandError(
                "--expected-plan is required; copy the token from a reviewed preview."
            )
        if options["expected_plan"] != plan["token"]:
            raise CommandError(
                "The current plan differs from --expected-plan. Review a new preview first."
            )
        if plan["blocking"]:
            raise CommandError(
                "One or more user relations require manual review; no records were changed."
            )
        if plan["media"] and not options["accept_remaining_media"]:
            raise CommandError(
                "The preview found uploaded files that this command cannot remove. "
                "Remove them separately or pass --accept-remaining-media after reviewing "
                "the listed files."
            )
        if plan["accounts"]["total"] == 0:
            raise CommandError("No user accounts exist; no records were changed.")

    def handle(self, *args, **options):
        connection = connections[DEFAULT_DB_ALIAS]
        plan = self._build_plan(connection, options["preserve_email"])
        self._print_plan(plan, connection)

        if not options["execute"]:
            self.stdout.write("Preview only. No database rows were changed.")
            return

        self._validate_execution(plan, connection, options)

        erased_count = 0
        table_name = connection.ops.quote_name(User._meta.db_table)
        with transaction.atomic(using=DEFAULT_DB_ALIAS):
            # Block concurrent logins, registrations, and user-linked writes while
            # the count is rechecked and the one-transaction reset is performed.
            with connection.cursor() as cursor:
                cursor.execute(f"LOCK TABLE {table_name} IN ACCESS EXCLUSIVE MODE")

            current_plan = self._build_plan(connection, options["preserve_email"])
            self._print_plan(current_plan, connection)
            self._validate_execution(current_plan, connection, options)

            AuditLog.objects.create(
                action_by=None,
                action_type=AuditLog.ActionType.USER_ACTION,
                description=(
                    "Production bulk account reset completed; retained operator "
                    f"ID={current_plan['preserved_operator']['id']}; "
                    f"backup reference={str(options['backup_reference']).strip()}; "
                    f"plan token={current_plan['token']}; "
                    f"account count={current_plan['accounts']['total']}."
                ),
            )

            preserved_operator_id = current_plan["preserved_operator"]["id"]
            users_to_erase = User.objects.using(DEFAULT_DB_ALIAS).exclude(
                pk=preserved_operator_id
            )
            service_delete_querysets = self._service_delete_querysets(users_to_erase)
            for model_label in SERVICE_DELETE_ORDER:
                queryset = service_delete_querysets[model_label]
                self._queue_private_media_cleanup(queryset, model_label)
                queryset.delete()

            while True:
                user = (
                    User.objects.using(DEFAULT_DB_ALIAS)
                    .exclude(pk=preserved_operator_id)
                    .order_by("pk")
                    .first()
                )
                if user is None:
                    break
                account_id = user.pk
                erase_user_account(
                    user,
                    reason=(
                        "Production account reset: account and linked service rows erased; "
                        f"target account ID={account_id}; "
                        f"backup reference={str(options['backup_reference']).strip()}."
                    ),
                    actor=user,
                )
                erased_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Erased {erased_count} user accounts in one transaction.")
        )
        self.stdout.write(
            "The selected global operator account remains. All other user accounts were "
            "erased; verify operator access before ending maintenance."
        )
        if plan["media"]:
            self.stdout.write(
                self.style.WARNING(
                    "External file objects listed in the preview remain in storage; "
                    "see the preview counts for exact models and fields."
                )
            )
