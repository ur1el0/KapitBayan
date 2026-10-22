from datetime import date, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from gridy_auth.management.commands.demo_seed_safety import require_local_demo_database
from gridy_auth.models import User, Barangay, Resident, BarangayApplication
from gridy_communications.models import Announcement, ActivitySchedule
from gridy_services.models import DocumentRequest, DocumentServiceOffering, QueueTicket


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

        # Ensure approved onboarding application records exist for partner barangays
        for b_inst, admin_inst, official_name, email, phone in [
            (dupay, admin_dupay, "Demo Official Dupay", "admin.dupay@example.invalid", "09170000001"),
            (daungan, admin_daungan, "Demo Official Daungan", "admin.daungan@example.invalid", "09170000002"),
            (cotta, admin_cotta, "Cotta Seed Admin", "captain.cotta@gridy.local", "09170000003"),
        ]:
            BarangayApplication.objects.get_or_create(
                created_barangay=b_inst,
                defaults={
                    "name": b_inst.name,
                    "municipality": b_inst.municipality or "Lucena City",
                    "province": b_inst.province or "Quezon",
                    "applicant_name": official_name,
                    "applicant_position": "Punong Barangay",
                    "applicant_email": email,
                    "applicant_phone": phone,
                    "status": BarangayApplication.Status.APPROVED,
                    "created_admin": admin_inst,
                    "review_verified": True,
                    "proof_reviewed": True,
                    "reviewed_at": timezone.now(),
                },
            )

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
        # 5. Document Service Offerings (Published Catalog & Requirements)
        # ---------------------------------------------------------------------
        standard_offerings = [
            {
                "document_type": "Barangay Clearance",
                "requirements": [
                    "Government ID or proof of residency",
                    "Community Tax Certificate (Cedula)",
                ],
                "published_fee_amount": Decimal("50.00"),
                "details": "Standard clearance for employment, identification, and official transactions.",
            },
            {
                "document_type": "Certificate of Indigency",
                "requirements": [
                    "Government ID or proof of residency",
                    "Proof of indigent status or declaration of low income",
                ],
                "published_fee_amount": Decimal("0.00"),
                "details": "Statutory fee-exempt certificate for social welfare, medical, and legal assistance.",
            },
            {
                "document_type": "Certificate of Residency",
                "requirements": [
                    "Government ID",
                    "Proof of address (utility bill, lease contract, or voter certification)",
                ],
                "published_fee_amount": Decimal("50.00"),
                "details": "Official certification verifying residency address within the Barangay.",
            },
            {
                "document_type": "Barangay Business Clearance",
                "requirements": [
                    "Government ID of owner or representative",
                    "DTI or SEC Certificate of Registration",
                    "Contract of lease or proof of property ownership",
                ],
                "published_fee_amount": Decimal("200.00"),
                "details": "Clearance required for new business registration or annual business permit renewal.",
            },
        ]

        offering_lookup = {}
        for b_target in [dupay, daungan, cotta]:
            for off_def in standard_offerings:
                offering_obj, _ = DocumentServiceOffering.objects.update_or_create(
                    barangay=b_target,
                    document_type=off_def["document_type"],
                    defaults={
                        "requirements": off_def["requirements"],
                        "published_fee_amount": off_def["published_fee_amount"],
                        "details": off_def["details"],
                        "is_active": True,
                    },
                )
                offering_lookup[(b_target.id, off_def["document_type"])] = offering_obj
        self.stdout.write(self.style.SUCCESS("Provisioned standard document service offerings and requirements."))

        # ---------------------------------------------------------------------
        # 6. Synthetic Document Requests
        # ---------------------------------------------------------------------
        dupay_clearance = offering_lookup.get((dupay.id, "Barangay Clearance"))
        DocumentRequest.objects.get_or_create(
            user=resident_dupay,
            document_type="Barangay Clearance",
            defaults={
                "barangay": dupay,
                "offering": dupay_clearance,
                "requirements_snapshot": list(dupay_clearance.requirements) if dupay_clearance else [],
                "published_fee_amount_snapshot": dupay_clearance.published_fee_amount if dupay_clearance else Decimal("50.00"),
                "details_snapshot": dupay_clearance.details if dupay_clearance else "",
                "purpose": "Synthetic demonstration request",
                "urgency_tag": DocumentRequest.UrgencyTag.REGULAR,
                "status": DocumentRequest.Status.READY_FOR_PICKUP,
                "fee_amount": 50.00,
                "or_number": "DEMO-OR-001",
                "admin_notes": "Synthetic presentation record; not an official receipt.",
            }
        )

        daungan_indigency = offering_lookup.get((daungan.id, "Certificate of Indigency"))
        DocumentRequest.objects.get_or_create(
            user=resident_daungan,
            document_type="Certificate of Indigency",
            defaults={
                "barangay": daungan,
                "offering": daungan_indigency,
                "requirements_snapshot": list(daungan_indigency.requirements) if daungan_indigency else [],
                "published_fee_amount_snapshot": daungan_indigency.published_fee_amount if daungan_indigency else Decimal("0.00"),
                "details_snapshot": daungan_indigency.details if daungan_indigency else "",
                "purpose": "Synthetic demonstration request",
                "urgency_tag": DocumentRequest.UrgencyTag.URGENT,
                "status": DocumentRequest.Status.RELEASED,
                "fee_amount": 0.00,
                "or_number": "EXEMPT",
                "admin_notes": "Synthetic presentation record; not an eligibility decision.",
            }
        )

        cotta_indigency = offering_lookup.get((cotta.id, "Certificate of Indigency"))
        DocumentRequest.objects.get_or_create(
            user=resident_cotta_one,
            document_type="Certificate of Indigency",
            defaults={
                "barangay": cotta,
                "offering": cotta_indigency,
                "requirements_snapshot": list(cotta_indigency.requirements) if cotta_indigency else [],
                "published_fee_amount_snapshot": cotta_indigency.published_fee_amount if cotta_indigency else Decimal("0.00"),
                "details_snapshot": cotta_indigency.details if cotta_indigency else "",
                "purpose": "Synthetic presentation record",
                "urgency_tag": DocumentRequest.UrgencyTag.REGULAR,
                "status": DocumentRequest.Status.PENDING,
                "fee_amount": 0.00,
                "admin_notes": "Synthetic fixture; verify statutory fee rules.",
            }
        )

        cotta_clearance = offering_lookup.get((cotta.id, "Barangay Clearance"))
        DocumentRequest.objects.get_or_create(
            user=resident_cotta_two,
            document_type="Barangay Clearance",
            defaults={
                "barangay": cotta,
                "offering": cotta_clearance,
                "requirements_snapshot": list(cotta_clearance.requirements) if cotta_clearance else [],
                "published_fee_amount_snapshot": cotta_clearance.published_fee_amount if cotta_clearance else Decimal("50.00"),
                "details_snapshot": cotta_clearance.details if cotta_clearance else "",
                "purpose": "Synthetic presentation record; local fee not verified",
                "urgency_tag": DocumentRequest.UrgencyTag.REGULAR,
                "status": DocumentRequest.Status.PENDING,
                "fee_amount": 0.00,
                "admin_notes": "Synthetic fixture; configure fees from the local ordinance.",
            }
        )

        # Backfill existing document requests that have empty snapshots
        for doc_req in DocumentRequest.objects.filter(requirements_snapshot=[]):
            matched_offering = None
            if doc_req.barangay_id:
                matched_offering = DocumentServiceOffering.objects.filter(
                    barangay_id=doc_req.barangay_id,
                    document_type__iexact=doc_req.document_type.strip(),
                ).first()
            if matched_offering:
                doc_req.offering = matched_offering
                doc_req.requirements_snapshot = list(matched_offering.requirements)
                doc_req.published_fee_amount_snapshot = matched_offering.published_fee_amount
                doc_req.details_snapshot = matched_offering.details
                doc_req.save(update_fields=[
                    "offering",
                    "requirements_snapshot",
                    "published_fee_amount_snapshot",
                    "details_snapshot",
                ])

        # ---------------------------------------------------------------------
        # 7. Live Queue Tickets
        # ---------------------------------------------------------------------
        if not QueueTicket.objects.filter(barangay=dupay, ticket_number="T001").exists():
            QueueTicket.objects.create(
                barangay=dupay,
                ticket_number="T001",
                user=resident_dupay,
                service_type="Document Pickup",
                status=QueueTicket.Status.SERVING,
                priority_status=QueueTicket.Priority.REGULAR,
            )

        if not QueueTicket.objects.filter(barangay=daungan, ticket_number="T002").exists():
            QueueTicket.objects.create(
                barangay=daungan,
                ticket_number="T002",
                user=resident_daungan,
                service_type="Indigency Assessment",
                status=QueueTicket.Status.WAITING,
                priority_status=QueueTicket.Priority.REGULAR,
            )

        if not QueueTicket.objects.filter(barangay=cotta, ticket_number="COTTA-T001").exists():
            QueueTicket.objects.create(
                barangay=cotta,
                ticket_number="COTTA-T001",
                user=resident_cotta_one,
                service_type="Document Application",
                status=QueueTicket.Status.WAITING,
                priority_status=QueueTicket.Priority.REGULAR,
            )

        if not QueueTicket.objects.filter(barangay=cotta, ticket_number="COTTA-T002").exists():
            QueueTicket.objects.create(
                barangay=cotta,
                ticket_number="COTTA-T002",
                user=resident_cotta_two,
                service_type="Document Pickup",
                status=QueueTicket.Status.WAITING,
                priority_status=QueueTicket.Priority.REGULAR,
            )
        
        self.stdout.write(self.style.SUCCESS("Successfully seeded local synthetic barangay fixtures."))
