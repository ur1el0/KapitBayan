from importlib import import_module
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from django.apps import apps
from django.db import connection
from django.core.management import call_command, CommandError
from django.test import TestCase, override_settings

from gridy_auth.models import Barangay, Resident, User
from gridy_auth.management.commands.seed_users import DEFAULT_SEED_PASSWORD
from gridy_services.models import AidRequest, DocumentRequest, QueueTicket


class DemoAnalyticsSeedTests(TestCase):
    @override_settings(DEBUG=True)
    def test_seed_is_synthetic_idempotent_and_accounts_have_unusable_passwords(self):
        call_command("seed_demo_analytics", confirm_demo_only=True, stdout=StringIO())
        first_counts = self._counts()

        call_command("seed_demo_analytics", confirm_demo_only=True, stdout=StringIO())

        self.assertEqual(self._counts(), first_counts)
        self.assertEqual(Barangay.objects.filter(name__startswith="KapitBayan Demo Barangay").count(), 3)
        self.assertEqual(Resident.objects.filter(user__username__startswith="gridy_demo_").count(), 12)
        self.assertTrue(
            all(
                not user.has_usable_password()
                for user in User.objects.filter(username__startswith="gridy_demo_")
            )
        )
        self.assertGreater(QueueTicket.objects.filter(barangay__name__startswith="KapitBayan Demo").count(), 0)
        self.assertGreater(DocumentRequest.objects.filter(purpose__startswith="KapitBayan Demo").count(), 0)
        self.assertGreater(AidRequest.objects.filter(reason__startswith="Synthetic presentation").count(), 0)

    @override_settings(DEBUG=False)
    def test_refuses_to_seed_when_debug_is_disabled(self):
        with self.assertRaises(CommandError):
            call_command("seed_demo_analytics", confirm_demo_only=True, stdout=StringIO())

    @override_settings(DEBUG=True)
    def test_refuses_to_seed_remote_database_hosts_even_with_confirmation_flag(self):
        with patch(
            "gridy_auth.management.commands.demo_seed_safety.connection.settings_dict",
            {"HOST": "ep-demo.ap-southeast-1.aws.neon.tech"},
        ), self.assertRaises(CommandError):
            call_command("seed_demo_analytics", confirm_demo_only=True, stdout=StringIO())

    @override_settings(DEBUG=True)
    def test_requires_explicit_confirmation(self):
        with self.assertRaises(CommandError):
            call_command("seed_demo_analytics", stdout=StringIO())

    def _counts(self):
        return {
            "barangays": Barangay.objects.filter(name__startswith="KapitBayan Demo Barangay").count(),
            "users": User.objects.filter(username__startswith="gridy_demo_").count(),
            "residents": Resident.objects.filter(user__username__startswith="gridy_demo_").count(),
            "documents": DocumentRequest.objects.filter(purpose__startswith="KapitBayan Demo").count(),
            "tickets": QueueTicket.objects.filter(barangay__name__startswith="KapitBayan Demo").count(),
            "aid_requests": AidRequest.objects.filter(reason__startswith="Synthetic presentation").count(),
        }


class BarangaySeedTests(TestCase):
    @override_settings(DEBUG=True)
    def test_seed_barangays_does_not_create_platform_or_government_wide_accounts(self):
        call_command("seed_barangays", confirm_demo_only=True, stdout=StringIO())
        self.assertFalse(User.objects.filter(username="dilg_admin").exists())


class LegacyDemoCredentialMigrationTests(TestCase):
    def test_migration_disables_only_exact_legacy_demo_accounts(self):
        seeded_user = User.objects.create_user(
            username="admin_dupay",
            email="captain.dupay@gridy.local",
            password="seeded",
        )
        same_username_user = User.objects.create_user(
            username="admin_dupay_lookalike",
            email="captain.dupay@another.example",
            password="normal",
        )
        same_email_user = User.objects.create_user(
            username="another_lookalike",
            email="captain.dupay@gridy.local",
            password="normal",
        )
        ordinary_user = User.objects.create_user(
            username="presentation_operator",
            password="normal",
        )
        migration = import_module(
            "gridy_auth.migrations.0014_revoke_seeded_demo_passwords"
        )

        migration.revoke_seeded_demo_passwords(
            apps,
            SimpleNamespace(connection=connection),
        )

        seeded_user.refresh_from_db()
        same_username_user.refresh_from_db()
        same_email_user.refresh_from_db()
        ordinary_user.refresh_from_db()
        self.assertFalse(seeded_user.has_usable_password())
        self.assertTrue(same_username_user.has_usable_password())
        self.assertTrue(same_email_user.has_usable_password())
        self.assertTrue(ordinary_user.has_usable_password())


class SeedUsersCommandTests(TestCase):
    @override_settings(DEBUG=True)
    def test_seed_users_provisions_only_barangay_roles_with_default_password(self):
        call_command("seed_users", confirm_demo_only=True, stdout=StringIO())

        self.assertEqual(User.objects.filter(role=User.Role.ADMIN).count(), 3)
        self.assertEqual(User.objects.filter(role=User.Role.FIELD_OFFICIAL).count(), 2)
        self.assertEqual(User.objects.filter(role=User.Role.RESIDENT).count(), 4)

        self.assertTrue(User.objects.get(username="admin_dupay").check_password(DEFAULT_SEED_PASSWORD))
        self.assertTrue(User.objects.get(username="tanod_dupay").check_password(DEFAULT_SEED_PASSWORD))
        self.assertTrue(User.objects.get(username="resident_dupay").check_password(DEFAULT_SEED_PASSWORD))
        self.assertFalse(User.objects.filter(username="dilg_admin").exists())

        resident = Resident.objects.get(user__username="resident_dupay")
        self.assertTrue(resident.is_verified)
        self.assertEqual(resident.purok, "Purok 3 - Sampaguita")

    @override_settings(DEBUG=True)
    def test_seed_users_supports_custom_password_and_is_idempotent(self):
        custom_password = "".join(["Dev", "Custom", "Pass", "2026", "!"])
        call_command("seed_users", confirm_demo_only=True, password=custom_password, stdout=StringIO())
        first_count = User.objects.count()

        call_command("seed_users", confirm_demo_only=True, password=custom_password, stdout=StringIO())
        self.assertEqual(User.objects.count(), first_count)
        self.assertTrue(User.objects.get(username="admin_dupay").check_password(custom_password))
        self.assertFalse(User.objects.filter(username="dilg_admin").exists())

    @override_settings(DEBUG=False)
    def test_seed_users_refuses_when_debug_is_disabled(self):
        with self.assertRaises(CommandError):
            call_command("seed_users", confirm_demo_only=True, stdout=StringIO())

    @override_settings(DEBUG=True)
    def test_seed_users_requires_explicit_confirmation(self):
        with self.assertRaises(CommandError):
            call_command("seed_users", stdout=StringIO())

    @override_settings(DEBUG=True)
    def test_seed_users_refuses_remote_database_hosts(self):
        with patch(
            "gridy_auth.management.commands.demo_seed_safety.connection.settings_dict",
            {"HOST": "ep-demo.ap-southeast-1.aws.neon.tech"},
        ), self.assertRaises(CommandError):
            call_command("seed_users", confirm_demo_only=True, stdout=StringIO())

    @override_settings(DEBUG=True)
    def test_seed_users_refuses_unexpected_username_collision_without_mutating_record(self):
        existing_user = User.objects.create_user(
            username="admin_dupay",
            email="unexpected.admin@example.org",
            first_name="Real",
            last_name="Official",
            role=User.Role.RESIDENT,
            is_staff=False,
        )
        out = StringIO()
        with self.assertRaises(CommandError) as ctx:
            call_command("seed_users", confirm_demo_only=True, stdout=out)

        self.assertIn("collision", str(ctx.exception).lower())
        existing_user.refresh_from_db()
        self.assertEqual(existing_user.email, "unexpected.admin@example.org")
        self.assertEqual(existing_user.first_name, "Real")
        self.assertEqual(existing_user.last_name, "Official")
        self.assertEqual(existing_user.role, User.Role.RESIDENT)
        self.assertFalse(existing_user.is_staff)

    @override_settings(DEBUG=True)
    def test_seed_users_refuses_unexpected_barangay_collision_without_mutating_record(self):
        existing_barangay = Barangay.objects.create(
            name="Barangay Ibabang Dupay",
            captain_name="Hon. Real Local Leader",
            office_contact="Real Official Office Contact",
        )
        out = StringIO()
        with self.assertRaises(CommandError) as ctx:
            call_command("seed_users", confirm_demo_only=True, stdout=out)

        self.assertIn("collision", str(ctx.exception).lower())
        existing_barangay.refresh_from_db()
        self.assertEqual(existing_barangay.captain_name, "Hon. Real Local Leader")
        self.assertEqual(existing_barangay.office_contact, "Real Official Office Contact")
        self.assertEqual(User.objects.count(), 0)

    @override_settings(DEBUG=True)
    def test_seed_users_does_not_leak_password_in_output(self):
        custom_password = "".join(["Secret", "Pass", "2026", "!"])
        out = StringIO()
        call_command(
            "seed_users",
            confirm_demo_only=True,
            password=custom_password,
            stdout=out,
        )
        output = out.getvalue()
        self.assertNotIn(custom_password, output)
        self.assertNotIn(DEFAULT_SEED_PASSWORD, output)

    @override_settings(DEBUG=True)
    def test_seed_users_rolls_back_atomically_on_failure(self):
        original_save = User.save
        call_count = 0

        def failing_save(user_self, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count >= 3:
                raise RuntimeError("Simulated transient write failure")
            return original_save(user_self, *args, **kwargs)

        with patch.object(User, "save", failing_save):
            with self.assertRaises(RuntimeError):
                call_command("seed_users", confirm_demo_only=True, stdout=StringIO())

        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(Barangay.objects.count(), 0)

    @override_settings(DEBUG=True)
    def test_seed_users_refuses_unexpected_email_collision_without_mutating_record(self):
        unexpected_user = User.objects.create_user(
            username="unrelated_operator",
            email="admin.dupay@example.invalid",
            first_name="Unrelated",
            last_name="Operator",
        )
        out = StringIO()
        with self.assertRaises(CommandError) as ctx:
            call_command("seed_users", confirm_demo_only=True, stdout=out)

        self.assertIn("collision", str(ctx.exception).lower())
        unexpected_user.refresh_from_db()
        self.assertEqual(unexpected_user.username, "unrelated_operator")
        self.assertEqual(unexpected_user.email, "admin.dupay@example.invalid")
        self.assertFalse(User.objects.filter(username="admin_dupay").exists())

    @override_settings(DEBUG=True)
    def test_seed_users_preserves_existing_resident_evidence_fields_on_rerun(self):
        call_command("seed_users", confirm_demo_only=True, stdout=StringIO())
        resident = Resident.objects.get(user__username="resident_dupay")
        resident.philsys_id_number = "1234-5678-9012"
        resident.save(update_fields=["philsys_id_number"])

        call_command("seed_users", confirm_demo_only=True, stdout=StringIO())
        resident.refresh_from_db()
        self.assertEqual(resident.philsys_id_number, "1234-5678-9012")
        self.assertTrue(resident.is_verified)
        self.assertEqual(resident.purok, "Purok 3 - Sampaguita")

    @override_settings(DEBUG=True)
    def test_seed_users_supports_recognized_legacy_seed_identities(self):
        cotta = Barangay.objects.create(
            name="Barangay Cotta",
            captain_name="Seed fixture — verify official before production use",
            office_contact="Seed fixture — verify contact before production use",
        )
        legacy_cotta_admin = User.objects.create_user(
            username="admin_cotta",
            email="captain.cotta@gridy.local",
            role=User.Role.ADMIN,
            barangay=cotta,
            is_staff=True,
        )

        call_command("seed_users", confirm_demo_only=True, stdout=StringIO())

        legacy_cotta_admin.refresh_from_db()
        self.assertEqual(legacy_cotta_admin.email, "admin.cotta@example.invalid")
        self.assertTrue(legacy_cotta_admin.check_password(DEFAULT_SEED_PASSWORD))

    @override_settings(DEBUG=True)
    def test_seed_users_preserves_existing_resident_profile_rows_on_rerun(self):
        call_command("seed_users", confirm_demo_only=True, stdout=StringIO())
        resident = Resident.objects.get(user__username="resident_dupay")
        resident.full_name = "Custom Name That Should Not Be Overwritten"
        resident.purok = "Purok Custom"
        resident.is_verified = False
        resident.save()

        call_command("seed_users", confirm_demo_only=True, stdout=StringIO())

        resident.refresh_from_db()
        self.assertEqual(resident.full_name, "Custom Name That Should Not Be Overwritten")
        self.assertEqual(resident.purok, "Purok Custom")
        self.assertFalse(resident.is_verified)

    @override_settings(DEBUG=True)
    def test_seed_users_refuses_barangay_with_partial_or_loose_marker_collision(self):
        existing_barangay = Barangay.objects.create(
            name="Barangay Ibabang Dupay",
            captain_name="Synthetic demo record — customized by tester",
            office_contact="Different contact info",
        )
        out = StringIO()
        with self.assertRaises(CommandError) as ctx:
            call_command("seed_users", confirm_demo_only=True, stdout=out)

        self.assertIn("collision", str(ctx.exception).lower())
        existing_barangay.refresh_from_db()
        self.assertEqual(existing_barangay.captain_name, "Synthetic demo record — customized by tester")
        self.assertEqual(existing_barangay.office_contact, "Different contact info")
        self.assertEqual(User.objects.count(), 0)

    @override_settings(DEBUG=True)
    def test_seed_users_does_not_disclose_usernames_in_output(self):
        out = StringIO()
        call_command("seed_users", confirm_demo_only=True, stdout=out)
        output = out.getvalue()
        seed_usernames = [
            "admin_dupay",
            "admin_daungan",
            "admin_cotta",
            "tanod_dupay",
            "tanod_cotta",
            "resident_dupay",
            "resident_daungan",
            "resident_cotta_one",
            "resident_cotta_two",
        ]
        for username in seed_usernames:
            self.assertNotIn(username, output)
