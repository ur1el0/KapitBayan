from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from gridy_auth.management.commands.demo_seed_safety import require_local_demo_database
from gridy_auth.models import User, Barangay, Resident
from gridy_communications.models import Announcement, ActivitySchedule
from gridy_services.models import DocumentRequest, QueueTicket


class Command(BaseCommand):
    help = "Seed local synthetic barangay accounts and starter records for development."

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm-demo-only",
            action="store_true",
            help="Confirm that this is a local development or presentation database.",
        )

    def handle(self, *args, **options):
        require_local_demo_database(confirmed=options["confirm_demo_only"])
        self.stdout.write(self.style.NOTICE("Seeding local synthetic barangay fixtures..."))

        # ---------------------------------------------------------------------
        # 1. Partner Barangays Provisioning
        # ---------------------------------------------------------------------
        dupay, _ = Barangay.objects.get_or_create(
            name="Barangay Ibabang Dupay",
            defaults={
                "captain_name": "Synthetic demo record — not a real official",
                "office_contact": "Demo data only; confirm official contact information separately.",
            }
        )
        self.stdout.write(self.style.SUCCESS(f"Provisioned: {dupay.name}"))

        daungan, _ = Barangay.objects.get_or_create(
            name="Barangay Daungan",
            defaults={
                "captain_name": "Synthetic demo record — not a real official",
                "office_contact": "Demo data only; confirm official contact information separately.",
            }
        )
        self.stdout.write(self.style.SUCCESS(f"Provisioned: {daungan.name}"))
        cotta, _ = Barangay.objects.get_or_create(
            name="Barangay Cotta",
            defaults={
                "captain_name": "Seed fixture — verify official before production use",
                "office_contact": "Seed fixture — verify contact before production use",
            }
        )
        self.stdout.write(self.style.SUCCESS(f"Provisioned: {cotta.name}"))

        # ---------------------------------------------------------------------
        # 2. Users & Resident Profiles
        # ---------------------------------------------------------------------
        # A. Ibabang Dupay Users
        admin_dupay, created = User.objects.get_or_create(
            username="admin_dupay",
            defaults={
                "email": "admin.dupay@example.invalid",
                "first_name": "Demo",
                "last_name": "Official Dupay",
                "role": User.Role.ADMIN,
                "barangay": dupay,
                "is_staff": True,
            }
        )
        if created:
            admin_dupay.set_unusable_password()
            admin_dupay.save()

        tanod_dupay, created = User.objects.get_or_create(
            username="tanod_dupay",
            defaults={
                "email": "field.dupay@example.invalid",
                "first_name": "Demo",
                "last_name": "Field Officer Dupay",
                "role": User.Role.FIELD_OFFICIAL,
                "barangay": dupay,
            }
        )
        if created:
            tanod_dupay.set_unusable_password()
            tanod_dupay.save()

        resident_dupay, created = User.objects.get_or_create(
            username="resident_dupay",
            defaults={
                "email": "resident.dupay@example.invalid",
                "first_name": "Demo",
                "last_name": "Resident Dupay",
                "role": User.Role.RESIDENT,
                "barangay": dupay,
            }
        )
        if created:
            resident_dupay.set_unusable_password()
            resident_dupay.save()
            Resident.objects.get_or_create(
                user=resident_dupay,
                defaults={
                    "full_name": "Demo Resident Dupay",
                    "birth_date": date(1996, 4, 18),
                    "voter_status": True,
                    "contact_number": "",
                    "purok": "Purok 3 - Sampaguita",
                    "is_verified": True,
                }
            )

        # B. Daungan Users
        admin_daungan, created = User.objects.get_or_create(
            username="admin_daungan",
            defaults={
                "email": "admin.daungan@example.invalid",
                "first_name": "Demo",
                "last_name": "Official Daungan",
                "role": User.Role.ADMIN,
                "barangay": daungan,
                "is_staff": True,
            }
        )
        if created:
            admin_daungan.set_unusable_password()
            admin_daungan.save()

        resident_daungan, created = User.objects.get_or_create(
            username="resident_daungan",
            defaults={
                "email": "resident.daungan@example.invalid",
                "first_name": "Demo",
                "last_name": "Resident Daungan",
                "role": User.Role.RESIDENT,
                "barangay": daungan,
            }
        )
        if created:
            resident_daungan.set_unusable_password()
            resident_daungan.save()
            Resident.objects.get_or_create(
                user=resident_daungan,
                defaults={
                    "full_name": "Demo Resident Daungan",
                    "birth_date": date(1988, 11, 24),
                    "voter_status": True,
                    "contact_number": "",
                    "purok": "Purok Baybayin",
                    "is_verified": True,
                }
            )

        # Demo accounts have no usable password. Set local credentials interactively
        # with `manage.py changepassword` when a presentation login is needed.
        def get_demo_user(username, defaults):
            user, created = User.objects.get_or_create(
                username=username,
                defaults=defaults,
            )
            if created:
                user.set_unusable_password()
                user.save(update_fields=["password"])
            return user

        # C. Barangay Cotta seed users
        admin_cotta = get_demo_user(
            "admin_cotta",
            {
                "email": "captain.cotta@gridy.local",
                "first_name": "Cotta",
                "last_name": "Seed Admin",
                "role": User.Role.ADMIN,
                "barangay": cotta,
                "is_staff": True,
            },
        )

        get_demo_user(
            "tanod_cotta",
            {
                "email": "official.cotta@gridy.local",
                "first_name": "Cotta",
                "last_name": "Seed Official",
                "role": User.Role.FIELD_OFFICIAL,
                "barangay": cotta,
            },
        )

        resident_cotta_one = get_demo_user(
            "resident_cotta_one",
            {
                "email": "resident1.cotta@gridy.local",
                "first_name": "Sample",
                "last_name": "Resident One",
                "role": User.Role.RESIDENT,
                "barangay": cotta,
            },
        )
        Resident.objects.get_or_create(
            user=resident_cotta_one,
            defaults={
                "full_name": "Sample Resident One",
                "birth_date": date(1995, 3, 14),
                "voter_status": True,
                "purok": "Purok 1",
                "is_verified": True,
            },
        )

        resident_cotta_two = get_demo_user(
            "resident_cotta_two",
            {
                "email": "resident2.cotta@gridy.local",
                "first_name": "Sample",
                "last_name": "Resident Two",
                "role": User.Role.RESIDENT,
                "barangay": cotta,
            },
        )
        Resident.objects.get_or_create(
            user=resident_cotta_two,
            defaults={
                "full_name": "Sample Resident Two",
                "birth_date": date(1998, 7, 22),
                "voter_status": False,
                "purok": "Purok 2",
                "is_verified": True,
            },
        )
        self.stdout.write(self.style.SUCCESS("Provisioned administrative and resident users."))

        # ---------------------------------------------------------------------
        # 3. Community Announcements
        # ---------------------------------------------------------------------
        Announcement.objects.get_or_create(
            title="DEMO: Community Assembly and Financial Report",
            defaults={
                "content": "Synthetic presentation announcement. Replace with a verified barangay notice before publication.",
                "is_pinned": True,
                "created_by": admin_dupay,
            }
        )

        Announcement.objects.get_or_create(
            title="DEMO: Coastal Community Services Notice",
            defaults={
                "content": "Synthetic presentation announcement. Replace with a verified barangay notice before publication.",
                "is_pinned": True,
                "created_by": admin_daungan,
            }
        )

        # ---------------------------------------------------------------------
        # 4. Activity Schedules
        # ---------------------------------------------------------------------
        ActivitySchedule.objects.get_or_create(
            title="DEMO: Community Pet Health Activity",
            defaults={
                "description": "Synthetic presentation activity. Confirm the schedule and service provider before publication.",
                "event_datetime": timezone.now() + timedelta(days=5),
                "location": "Ibabang Dupay Multi-Purpose Covered Court",
                "created_by": admin_dupay,
            }
        )

        ActivitySchedule.objects.get_or_create(
            title="DEMO: Community Coastal Activity",
            defaults={
                "description": "Synthetic presentation activity. Confirm the schedule and partners before publication.",
                "event_datetime": timezone.now() + timedelta(days=7),
                "location": "Daungan Coastal Shoreline Zone",
                "created_by": admin_daungan,
            }
        )

        # ---------------------------------------------------------------------
        # 5. Synthetic Document Requests
        # ---------------------------------------------------------------------
        DocumentRequest.objects.get_or_create(
            user=resident_dupay,
            document_type="Barangay Clearance",
            defaults={
                "barangay": dupay,
                "purpose": "Synthetic demonstration request",
                "urgency_tag": DocumentRequest.UrgencyTag.REGULAR,
                "status": DocumentRequest.Status.READY_FOR_PICKUP,
                "fee_amount": 50.00,
                "or_number": "DEMO-OR-001",
                "admin_notes": "Synthetic presentation record; not an official receipt.",
            }
        )

        DocumentRequest.objects.get_or_create(
            user=resident_daungan,
            document_type="Certificate of Indigency",
            defaults={
                "barangay": daungan,
                "purpose": "Synthetic demonstration request",
                "urgency_tag": DocumentRequest.UrgencyTag.URGENT,
                "status": DocumentRequest.Status.RELEASED,
                "fee_amount": 0.00,
                "or_number": "EXEMPT",
                "admin_notes": "Synthetic presentation record; not an eligibility decision.",
            }
        )

        DocumentRequest.objects.get_or_create(
            user=resident_cotta_one,
            document_type="Certificate of Indigency",
            defaults={
                "barangay": cotta,
                "purpose": "Synthetic presentation record",
                "urgency_tag": DocumentRequest.UrgencyTag.REGULAR,
                "status": DocumentRequest.Status.PENDING,
                "fee_amount": 0.00,
                "admin_notes": "Synthetic fixture; verify statutory fee rules.",
            }
        )

        DocumentRequest.objects.get_or_create(
            user=resident_cotta_two,
            document_type="Barangay Clearance",
            defaults={
                "barangay": cotta,
                "purpose": "Synthetic presentation record; local fee not verified",
                "urgency_tag": DocumentRequest.UrgencyTag.REGULAR,
                "status": DocumentRequest.Status.PENDING,
                "fee_amount": 0.00,
                "admin_notes": "Synthetic fixture; configure fees from the local ordinance.",
            }
        )

        # ---------------------------------------------------------------------
        # 6. Live Queue Tickets
        # ---------------------------------------------------------------------
        QueueTicket.objects.get_or_create(
            ticket_number="T001",
            defaults={
                "user": resident_dupay,
                "barangay": dupay,
                "service_type": "Document Pickup",
                "status": QueueTicket.Status.SERVING,
                "priority_status": QueueTicket.Priority.REGULAR,
            }
        )

        QueueTicket.objects.get_or_create(
            ticket_number="T002",
            defaults={
                "user": resident_daungan,
                "barangay": daungan,
                "service_type": "Indigency Assessment",
                "status": QueueTicket.Status.WAITING,
                "priority_status": QueueTicket.Priority.REGULAR,
            }
        )


        QueueTicket.objects.get_or_create(
            ticket_number="COTTA-T001",
            defaults={
                "user": resident_cotta_one,
                "barangay": cotta,
                "service_type": "Document Application",
                "status": QueueTicket.Status.WAITING,
                "priority_status": QueueTicket.Priority.REGULAR,
            }
        )

        QueueTicket.objects.get_or_create(
            ticket_number="COTTA-T002",
            defaults={
                "user": resident_cotta_two,
                "barangay": cotta,
                "service_type": "Document Pickup",
                "status": QueueTicket.Status.WAITING,
                "priority_status": QueueTicket.Priority.REGULAR,
            }
        )
        
        self.stdout.write(self.style.SUCCESS("Successfully seeded local synthetic barangay fixtures."))
