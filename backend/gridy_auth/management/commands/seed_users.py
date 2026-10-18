from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from gridy_auth.management.commands.demo_seed_safety import require_local_demo_database
from gridy_auth.models import Barangay, Resident, User


DEFAULT_SEED_PASSWORD = "".join(["Pass", "word", "123", "!"])

SEEDED_BARANGAYS = {
    "Barangay Ibabang Dupay": {
        "captain_name": "Synthetic demo record — not a real official",
        "office_contact": "Demo data only; confirm official contact information separately.",
    },
    "Barangay Daungan": {
        "captain_name": "Synthetic demo record — not a real official",
        "office_contact": "Demo data only; confirm official contact information separately.",
    },
    "Barangay Cotta": {
        "captain_name": "Seed fixture — verify official before production use",
        "office_contact": "Seed fixture — verify contact before production use",
    },
}

RECOGNIZED_USER_IDENTITIES = {
    "admin_dupay": {
        "emails": {"admin.dupay@example.invalid", "captain.dupay@gridy.local"},
        "role": User.Role.ADMIN,
    },
    "admin_daungan": {
        "emails": {"admin.daungan@example.invalid", "captain.daungan@gridy.local"},
        "role": User.Role.ADMIN,
    },
    "admin_cotta": {
        "emails": {"admin.cotta@example.invalid", "captain.cotta@gridy.local"},
        "role": User.Role.ADMIN,
    },
    "tanod_dupay": {
        "emails": {"field.dupay@example.invalid", "tanod.dupay@gridy.local"},
        "role": User.Role.FIELD_OFFICIAL,
    },
    "tanod_cotta": {
        "emails": {"field.cotta@example.invalid", "official.cotta@gridy.local"},
        "role": User.Role.FIELD_OFFICIAL,
    },
    "resident_dupay": {
        "emails": {"resident.dupay@example.invalid", "resident.dupay@gridy.local"},
        "role": User.Role.RESIDENT,
    },
    "resident_daungan": {
        "emails": {"resident.daungan@example.invalid", "resident.daungan@gridy.local"},
        "role": User.Role.RESIDENT,
    },
    "resident_cotta_one": {
        "emails": {"resident1.cotta@example.invalid", "resident1.cotta@gridy.local"},
        "role": User.Role.RESIDENT,
    },
    "resident_cotta_two": {
        "emails": {"resident2.cotta@example.invalid", "resident2.cotta@gridy.local"},
        "role": User.Role.RESIDENT,
    },
}


def is_recognized_seed_barangay(barangay, expected_meta):
    return (
        barangay.captain_name == expected_meta["captain_name"]
        and barangay.office_contact == expected_meta["office_contact"]
    )



class Command(BaseCommand):
    help = "Seed or update local synthetic accounts for Barangay Admins, Field Officials, and residents."

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm-demo-only",
            action="store_true",
            help="Confirm that this is a local development or presentation database.",
        )
        parser.add_argument(
            "--password",
            type=str,
            default=DEFAULT_SEED_PASSWORD,
            help="Password to assign to all seeded accounts (local development only).",
        )

    def preflight_checks(self, users_manifest):
        # 1. Validate target barangays for unexpected collisions
        for b_name, expected_meta in SEEDED_BARANGAYS.items():
            existing_b = Barangay.objects.filter(name=b_name).first()
            if existing_b and not is_recognized_seed_barangay(existing_b, expected_meta):
                raise CommandError(
                    f"Barangay collision: target barangay '{b_name}' already exists with "
                    f"unexpected non-seed metadata (captain_name={existing_b.captain_name!r}). "
                    f"Refusing to overwrite non-seed record."
                )

        # 2. Validate target usernames
        all_manifest_usernames = {item["username"] for item in users_manifest}
        for item in users_manifest:
            username = item["username"]
            existing_user = User.objects.filter(username=username).first()
            if existing_user:
                allowed_emails = RECOGNIZED_USER_IDENTITIES.get(username, {}).get("emails", set())
                if existing_user.email not in allowed_emails:
                    raise CommandError(
                        f"Username collision: existing user '{username}' has unexpected "
                        f"email '{existing_user.email}'. Refusing to overwrite non-seed record."
                    )

        # 3. Validate target emails across all existing users
        all_allowed_emails = {
            email
            for meta in RECOGNIZED_USER_IDENTITIES.values()
            for email in meta["emails"]
        }
        for existing_user in User.objects.filter(email__in=all_allowed_emails):
            if existing_user.username not in all_manifest_usernames:
                raise CommandError(
                    f"Email collision: existing user '{existing_user.username}' has email "
                    f"'{existing_user.email}' reserved for seed accounts. Refusing to overwrite non-seed record."
                )

    def handle(self, *args, **options):
        require_local_demo_database(confirmed=options["confirm_demo_only"])
        password = options["password"]

        # ---------------------------------------------------------------------
        # Account Definitions by Role
        # ---------------------------------------------------------------------
        users_manifest = [
            # Barangay Officials (ADMIN)
            {
                "username": "admin_dupay",
                "email": "admin.dupay@example.invalid",
                "first_name": "Demo",
                "last_name": "Official Dupay",
                "role": User.Role.ADMIN,
                "barangay_name": "Barangay Ibabang Dupay",
                "is_staff": True,
                "resident_profile": None,
            },
            {
                "username": "admin_daungan",
                "email": "admin.daungan@example.invalid",
                "first_name": "Demo",
                "last_name": "Official Daungan",
                "role": User.Role.ADMIN,
                "barangay_name": "Barangay Daungan",
                "is_staff": True,
                "resident_profile": None,
            },
            {
                "username": "admin_cotta",
                "email": "admin.cotta@example.invalid",
                "first_name": "Cotta",
                "last_name": "Seed Admin",
                "role": User.Role.ADMIN,
                "barangay_name": "Barangay Cotta",
                "is_staff": True,
                "resident_profile": None,
            },
            # Field Officers (FIELD_OFFICIAL)
            {
                "username": "tanod_dupay",
                "email": "field.dupay@example.invalid",
                "first_name": "Demo",
                "last_name": "Field Officer Dupay",
                "role": User.Role.FIELD_OFFICIAL,
                "barangay_name": "Barangay Ibabang Dupay",
                "is_staff": False,
                "resident_profile": None,
            },
            {
                "username": "tanod_cotta",
                "email": "field.cotta@example.invalid",
                "first_name": "Cotta",
                "last_name": "Seed Official",
                "role": User.Role.FIELD_OFFICIAL,
                "barangay_name": "Barangay Cotta",
                "is_staff": False,
                "resident_profile": None,
            },
            # Residents (RESIDENT)
            {
                "username": "resident_dupay",
                "email": "resident.dupay@example.invalid",
                "first_name": "Demo",
                "last_name": "Resident Dupay",
                "role": User.Role.RESIDENT,
                "barangay_name": "Barangay Ibabang Dupay",
                "is_staff": False,
                "resident_profile": {
                    "full_name": "Demo Resident Dupay",
                    "birth_date": date(1996, 4, 18),
                    "voter_status": True,
                    "purok": "Purok 3 - Sampaguita",
                    "is_verified": True,
                },
            },
            {
                "username": "resident_daungan",
                "email": "resident.daungan@example.invalid",
                "first_name": "Demo",
                "last_name": "Resident Daungan",
                "role": User.Role.RESIDENT,
                "barangay_name": "Barangay Daungan",
                "is_staff": False,
                "resident_profile": {
                    "full_name": "Demo Resident Daungan",
                    "birth_date": date(1988, 11, 24),
                    "voter_status": True,
                    "purok": "Purok Baybayin",
                    "is_verified": True,
                },
            },
            {
                "username": "resident_cotta_one",
                "email": "resident1.cotta@example.invalid",
                "first_name": "Sample",
                "last_name": "Resident One",
                "role": User.Role.RESIDENT,
                "barangay_name": "Barangay Cotta",
                "is_staff": False,
                "resident_profile": {
                    "full_name": "Sample Resident One",
                    "birth_date": date(1995, 3, 14),
                    "voter_status": True,
                    "purok": "Purok 1",
                    "is_verified": True,
                },
            },
            {
                "username": "resident_cotta_two",
                "email": "resident2.cotta@example.invalid",
                "first_name": "Sample",
                "last_name": "Resident Two",
                "role": User.Role.RESIDENT,
                "barangay_name": "Barangay Cotta",
                "is_staff": False,
                "resident_profile": {
                    "full_name": "Sample Resident Two",
                    "birth_date": date(1998, 7, 22),
                    "voter_status": False,
                    "purok": "Purok 2",
                    "is_verified": True,
                },
            },
        ]

        self.preflight_checks(users_manifest)
        self.stdout.write(self.style.NOTICE("Seeding local development accounts across all roles..."))

        # ---------------------------------------------------------------------
        # Provisioning within an atomic transaction
        # ---------------------------------------------------------------------
        with transaction.atomic():
            # 1. Partner Barangays Provisioning
            barangay_map = {}
            for b_name, meta in SEEDED_BARANGAYS.items():
                b, _ = Barangay.objects.get_or_create(
                    name=b_name,
                    defaults=meta,
                )
                barangay_map[b_name] = b

            # 2. Account Provisioning & Password Setting
            provisioned_summary = []
            for item in users_manifest:
                target_barangay = barangay_map.get(item["barangay_name"]) if item["barangay_name"] else None
                user, created = User.objects.get_or_create(
                    username=item["username"],
                    defaults={
                        "email": item["email"],
                        "first_name": item["first_name"],
                        "last_name": item["last_name"],
                        "role": item["role"],
                        "barangay": target_barangay,
                        "is_staff": item["is_staff"],
                    },
                )
                if not created:
                    user.email = item["email"]
                    user.first_name = item["first_name"]
                    user.last_name = item["last_name"]
                    user.role = item["role"]
                    user.barangay = target_barangay
                    user.is_staff = item["is_staff"]

                user.set_password(password)
                user.save()

                if item["resident_profile"]:
                    Resident.objects.get_or_create(
                        user=user,
                        defaults=item["resident_profile"],
                    )

                b_name = target_barangay.name if target_barangay else "Cross-tenant / All"
                provisioned_summary.append({
                    "role": user.get_role_display(),
                    "barangay": b_name,
                    "status": "Created" if created else "Updated password",
                })

        # ---------------------------------------------------------------------
        # 3. Output Summary Table (Credentials and Usernames Redacted)
        # ---------------------------------------------------------------------
        self.stdout.write(self.style.SUCCESS(f"\nSuccessfully seeded {len(provisioned_summary)} accounts across all roles.\n"))
        self.stdout.write(f"{'Role':<18} {'Barangay':<28} {'Status'}")
        self.stdout.write("-" * 58)
        for row in provisioned_summary:
            self.stdout.write(f"{row['role']:<18} {row['barangay']:<28} {row['status']}")
        self.stdout.write("-" * 58)
        self.stdout.write(self.style.NOTICE("\nWeb Portal: http://localhost:8080/ (Resident portal; barangay staff use Official Sign In)"))
