from datetime import datetime, timezone as datetime_timezone
from unittest.mock import patch
from django.urls import reverse
from rest_framework import status
from gridy_audit.models import AuditLog
from gridy_auth.models import Barangay, User
from gridy_services.models import QueueTicket
from .base import ServiceAPIBaseTestCase


class QueueTicketAPITests(ServiceAPIBaseTestCase):
    def test_field_official_cannot_create_queue_ticket(self):
        # Field officials monitor ticker and call next ticket, but cannot take tickets for themselves
        field_official = User.objects.create_user(
            username="tanod_test",
            password="SecurePassword123!",
            email="tanod@example.com",
            role=User.Role.FIELD_OFFICIAL
        )
        self.client.force_login(field_official)
        url = reverse('ticket-list')
        payload = {
            "service_type": "DOCUMENT"
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_resident_cannot_self_assign_priority_on_queue_ticket(self):
        barangay = Barangay.objects.create(name="Resident Priority Claim Barangay")
        self.resident.barangay = barangay
        self.resident.save(update_fields=["barangay"])
        self.client.force_login(self.resident)

        response = self.client.post(
            reverse("ticket-list"),
            {"service_type": "DOCUMENT", "is_priority": True},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(QueueTicket.objects.count(), 0)
        self.assertFalse(
            AuditLog.objects.filter(
                action_type=AuditLog.ActionType.QUEUE_ACTION
            ).exists()
        )

    def test_admin_priority_ticket_creation_requires_reason_and_is_audited(self):
        barangay = Barangay.objects.create(name="Admin Priority Creation Barangay")
        self.official.barangay = barangay
        self.official.save(update_fields=["barangay"])
        self.client.force_login(self.official)
        url = reverse("ticket-list")
        payload = {
            "walkin_name": "Priority Walk-in",
            "service_type": "DOCUMENT",
            "priority_status": QueueTicket.Priority.PRIORITY,
            "is_priority": True,
        }

        missing_reason_response = self.client.post(url, payload, format="json")
        self.assertEqual(missing_reason_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(QueueTicket.objects.count(), 0)

        payload["priority_reason"] = "Eligibility checked at the service desk"
        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        ticket = QueueTicket.objects.get()
        self.assertTrue(ticket.is_priority)
        self.assertEqual(ticket.priority_status, QueueTicket.Priority.PRIORITY)
        self.assertFalse(response.data.get("priority_reason"))
        audit_log = AuditLog.objects.get(
            action_type=AuditLog.ActionType.QUEUE_ACTION,
            action_by=self.official,
        )
        self.assertIn("Eligibility checked at the service desk", audit_log.description)
        self.assertIn(ticket.ticket_number, audit_log.description)
        self.assertIn(barangay.name, audit_log.description)

    def test_admin_can_change_waiting_ticket_priority_with_audit_reason(self):
        barangay = Barangay.objects.create(name="Queue Priority Update Barangay")
        self.official.barangay = barangay
        self.official.save(update_fields=["barangay"])
        self.client.force_login(self.official)
        ticket = QueueTicket.objects.create(
            barangay=barangay,
            ticket_number="T014",
            service_type="DOCUMENT",
        )
        url = reverse("ticket-set-priority", args=[ticket.pk])

        response = self.client.post(
            url,
            {
                "priority_status": QueueTicket.Priority.PRIORITY,
                "reason": "Eligibility document checked at the desk",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ticket.refresh_from_db()
        self.assertTrue(ticket.is_priority)
        self.assertEqual(ticket.priority_status, QueueTicket.Priority.PRIORITY)
        audit_log = AuditLog.objects.get(
            action_type=AuditLog.ActionType.QUEUE_ACTION,
            action_by=self.official,
        )
        self.assertIn("regular to priority", audit_log.description)
        self.assertIn(barangay.name, audit_log.description)
        self.assertIn("Eligibility document checked at the desk", audit_log.description)

        response = self.client.post(
            url,
            {
                "priority_status": QueueTicket.Priority.REGULAR,
                "reason": "Priority eligibility was not confirmed",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ticket.refresh_from_db()
        self.assertFalse(ticket.is_priority)
        self.assertEqual(ticket.priority_status, QueueTicket.Priority.REGULAR)
        self.assertEqual(
            AuditLog.objects.filter(
                action_type=AuditLog.ActionType.QUEUE_ACTION,
                action_by=self.official,
            ).count(),
            2,
        )

    def test_field_official_cannot_change_ticket_priority(self):
        barangay = Barangay.objects.create(name="Field Official Priority Barangay")
        field_official = User.objects.create_user(
            username="priority_field_official",
            password="SecurePassword123!",
            email="priority-field@example.com",
            role=User.Role.FIELD_OFFICIAL,
            barangay=barangay,
        )
        ticket = QueueTicket.objects.create(
            barangay=barangay,
            ticket_number="T015",
            service_type="DOCUMENT",
        )
        self.client.force_login(field_official)

        response = self.client.post(
            reverse("ticket-set-priority", args=[ticket.pk]),
            {
                "priority_status": QueueTicket.Priority.PRIORITY,
                "reason": "Eligibility document checked at the desk",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        ticket.refresh_from_db()
        self.assertFalse(ticket.is_priority)
        self.assertEqual(ticket.priority_status, QueueTicket.Priority.REGULAR)
        self.assertFalse(
            AuditLog.objects.filter(
                action_type=AuditLog.ActionType.QUEUE_ACTION
            ).exists()
        )

    def test_ticket_priority_cannot_be_changed_through_generic_update(self):
        barangay = Barangay.objects.create(name="Generic Priority Update Barangay")
        self.official.barangay = barangay
        self.official.save(update_fields=["barangay"])
        self.client.force_login(self.official)
        ticket = QueueTicket.objects.create(
            barangay=barangay,
            ticket_number="T016",
            service_type="DOCUMENT",
        )

        response = self.client.patch(
            reverse("ticket-detail", args=[ticket.pk]),
            {
                "is_priority": True,
                "priority_status": QueueTicket.Priority.PRIORITY,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        ticket.refresh_from_db()
        self.assertFalse(ticket.is_priority)
        self.assertEqual(ticket.priority_status, QueueTicket.Priority.REGULAR)

    def test_priority_cannot_be_changed_after_ticket_starts_serving(self):
        barangay = Barangay.objects.create(name="Serving Priority Update Barangay")
        self.official.barangay = barangay
        self.official.save(update_fields=["barangay"])
        self.client.force_login(self.official)
        ticket = QueueTicket.objects.create(
            barangay=barangay,
            ticket_number="T017",
            service_type="DOCUMENT",
            status=QueueTicket.Status.SERVING,
        )

        response = self.client.post(
            reverse("ticket-set-priority", args=[ticket.pk]),
            {
                "priority_status": QueueTicket.Priority.PRIORITY,
                "reason": "Eligibility document checked at the desk",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        ticket.refresh_from_db()
        self.assertFalse(ticket.is_priority)
        self.assertFalse(
            AuditLog.objects.filter(
                action_type=AuditLog.ActionType.QUEUE_ACTION
            ).exists()
        )

    def test_resident_can_create_queue_ticket(self):
        barangay = Barangay.objects.create(name="Resident Queue Creation Barangay")
        self.resident.barangay = barangay
        self.resident.save(update_fields=["barangay"])
        self.client.force_login(self.resident)
        url = reverse('ticket-list')
        payload = {
            "service_type": "DOCUMENT",
            "is_priority": False,
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(QueueTicket.objects.count(), 1)
        ticket = QueueTicket.objects.first()
        self.assertEqual(ticket.ticket_number, 'T001')
        self.assertFalse(ticket.is_priority)
        self.assertEqual(ticket.priority_status, QueueTicket.Priority.REGULAR)

    def test_resident_without_barangay_cannot_create_queue_ticket(self):
        self.client.force_login(self.resident)
        response = self.client.post(
            reverse("ticket-list"),
            {"service_type": "DOCUMENT"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(QueueTicket.objects.count(), 0)

    def test_resident_cannot_advance_queue(self):
        self.client.force_login(self.resident)
        url = reverse('ticket-next-ticket')
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_official_without_barangay_cannot_advance_queue(self):
        ticket = QueueTicket.objects.create(
            ticket_number="T099",
            service_type="DOCUMENT",
            status=QueueTicket.Status.WAITING,
        )
        self.client.force_login(self.official)

        response = self.client.post(reverse("ticket-next-ticket"))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, QueueTicket.Status.WAITING)

    def test_official_can_advance(self):
        barangay = Barangay.objects.create(name="Official Queue Test Barangay")
        self.official.barangay = barangay
        self.official.save(update_fields=["barangay"])
        self.client.force_login(self.official)

        previous_ticket = QueueTicket.objects.create(
            barangay=barangay,
            status=QueueTicket.Status.SERVING,
            ticket_number="T000",
            service_type="DOCUMENT",
        )
        ticket = QueueTicket.objects.create(
            barangay=barangay,
            status="WAITING",
            ticket_number="T001",
            service_type="DOCUMENT",
        )
        response = self.client.post(reverse("ticket-next-ticket"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        previous_ticket.refresh_from_db()
        self.assertEqual(previous_ticket.status, QueueTicket.Status.COMPLETED)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, "SERVING")
        self.assertEqual(
            AuditLog.objects.filter(
                action_type=AuditLog.ActionType.QUEUE_ACTION
            ).count(),
            1,
        )

    def test_queue_ticket_sequencing_isolated_by_barangay(self):
        barangay_a = Barangay.objects.create(name="Barangay A")
        barangay_b = Barangay.objects.create(name="Barangay B")

        # First ticket in Barangay A should start at T001
        ticket_a1 = QueueTicket.objects.create(barangay=barangay_a, service_type="Clearance")
        self.assertEqual(ticket_a1.ticket_number, "T001")

        # First ticket in Barangay B should also start at T001 independently
        ticket_b1 = QueueTicket.objects.create(barangay=barangay_b, service_type="Clearance")
        self.assertEqual(ticket_b1.ticket_number, "T001")

        # Second ticket in Barangay A increments to T002
        ticket_a2 = QueueTicket.objects.create(barangay=barangay_a, service_type="Clearance")
        self.assertEqual(ticket_a2.ticket_number, "T002")

    def test_queue_ticket_sequence_resets_at_manila_midnight(self):
        barangay = Barangay.objects.create(name="Manila Midnight Test Barangay")

        with patch("gridy_services.models.timezone.now") as mocked_now:
            mocked_now.return_value = datetime(
                2026, 1, 1, 15, 59, tzinfo=datetime_timezone.utc
            )
            before_midnight = QueueTicket.objects.create(
                barangay=barangay,
                service_type="Clearance",
            )

            mocked_now.return_value = datetime(
                2026, 1, 1, 16, 0, tzinfo=datetime_timezone.utc
            )
            after_midnight = QueueTicket.objects.create(
                barangay=barangay,
                service_type="Clearance",
            )

        self.assertEqual(before_midnight.ticket_number, "T001")
        self.assertEqual(after_midnight.ticket_number, "T001")

    def test_resident_can_cancel_own_waiting_queue_ticket(self):
        barangay = Barangay.objects.create(name="Resident Queue Cancel Test Barangay")
        self.resident.barangay = barangay
        self.resident.save(update_fields=["barangay"])
        self.client.force_login(self.resident)
        ticket = QueueTicket.objects.create(
            user=self.resident,
            barangay=self.resident.barangay,
            service_type="Clearance",
            status=QueueTicket.Status.WAITING
        )
        url = reverse('ticket-cancel-ticket', args=[ticket.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, QueueTicket.Status.CANCELLED)
        self.assertTrue(
            AuditLog.objects.filter(
                action_type=AuditLog.ActionType.QUEUE_ACTION,
                action_by=self.resident
            ).exists()
        )

    def test_resident_without_barangay_cannot_cancel_queue_ticket(self):
        ticket = QueueTicket.objects.create(
            user=self.resident,
            ticket_number="T098",
            service_type="DOCUMENT",
            status=QueueTicket.Status.WAITING,
        )
        self.client.force_login(self.resident)

        response = self.client.post(
            reverse("ticket-cancel-ticket", args=[ticket.id])
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, QueueTicket.Status.WAITING)

    def test_resident_cannot_cancel_serving_or_completed_queue_ticket(self):
        barangay = Barangay.objects.create(name="Resident Serving Queue Test Barangay")
        self.resident.barangay = barangay
        self.resident.save(update_fields=["barangay"])
        self.client.force_login(self.resident)
        ticket = QueueTicket.objects.create(
            user=self.resident,
            barangay=self.resident.barangay,
            service_type="Clearance",
            status=QueueTicket.Status.SERVING
        )
        url = reverse('ticket-cancel-ticket', args=[ticket.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, QueueTicket.Status.SERVING)

    def test_resident_cannot_cancel_other_resident_queue_ticket(self):
        barangay = Barangay.objects.create(name="Other Resident Queue Test Barangay")
        self.resident.barangay = barangay
        self.resident.save(update_fields=["barangay"])
        other_resident = User.objects.create_user(
            username="other_queue_resident",
            password="SecurePassword123!",
            email="other_queue@example.com",
            role=User.Role.RESIDENT,
            barangay=barangay,
        )
        ticket = QueueTicket.objects.create(
            user=other_resident,
            barangay=barangay,
            service_type="Clearance",
            status=QueueTicket.Status.WAITING
        )
        self.client.force_login(self.resident)
        url = reverse('ticket-cancel-ticket', args=[ticket.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, QueueTicket.Status.WAITING)

    def test_legacy_role_cannot_cancel_queue_ticket(self):
        barangay = Barangay.objects.create(
            name="DILG Queue Isolation Test Barangay"
        )
        ticket = QueueTicket.objects.create(
            barangay=barangay,
            service_type="Clearance",
            status=QueueTicket.Status.WAITING,
        )
        dilg_admin = User.objects.create_user(
            username="dilg_queue_test",
            password="SecurePassword123!",
            email="dilg-queue-test@example.com",
            role="DILG_ADMIN",
        )

        self.client.force_authenticate(dilg_admin)
        response = self.client.post(
            reverse("ticket-cancel-ticket", args=[ticket.id])
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, QueueTicket.Status.WAITING)
