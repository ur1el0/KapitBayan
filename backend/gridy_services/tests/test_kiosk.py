from django.urls import reverse
from rest_framework import status
from gridy_auth.models import Barangay, BarangayApplication
from gridy_services.models import DocumentRequest, EquipmentBorrowRequest, QueueTicket
from gridy_reports.models import IssueReport
from .base import ServiceAPIBaseTestCase


class KioskAPITests(ServiceAPIBaseTestCase):
    def setUp(self):
        super().setUp()
        self.kiosk_barangay = Barangay.objects.create(
            name="Kiosk Test Barangay",
        )
        BarangayApplication.objects.create(
            name=self.kiosk_barangay.name,
            applicant_name="Official Kiosk",
            applicant_position="Secretary",
            applicant_email="kiosk.official@example.test",
            applicant_phone="09123456781",
            status=BarangayApplication.Status.APPROVED,
            created_barangay=self.kiosk_barangay,
            review_verified=True,
        )

    def test_kiosk_queue_ticket_creation_success(self):
        url = reverse("kiosk-queue-ticket")
        payload = {
            "barangay_id": self.kiosk_barangay.id,
            "walkin_name": "Juan Dela Cruz",
            "service_type": "Document Processing & Clearances",
            "privacy_acknowledged": True,
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("reference", response.data)
        self.assertEqual(response.data["status"], QueueTicket.Status.WAITING)

        # Confirm saved in database as walk-in waiting ticket
        ticket = QueueTicket.objects.filter(
            barangay=self.kiosk_barangay,
            walkin_name="Juan Dela Cruz",
        ).first()
        self.assertIsNotNone(ticket)
        self.assertEqual(ticket.status, QueueTicket.Status.WAITING)
        self.assertIsNone(ticket.user)
        self.assertEqual(ticket.privacy_notice_version, "kiosk-v1")
        self.assertIsNotNone(ticket.privacy_acknowledged_at)

    def test_kiosk_queue_ticket_requires_privacy_acknowledgement(self):
        url = reverse("kiosk-queue-ticket")
        payload = {
            "barangay_id": self.kiosk_barangay.id,
            "walkin_name": "Maria Santos",
            "service_type": "Barangay ID Application",
            "privacy_acknowledged": False,
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("privacy_acknowledged", response.data)

    def test_kiosk_document_request_creation_success(self):
        url = reverse("kiosk-document-request")
        payload = {
            "barangay_id": self.kiosk_barangay.id,
            "walkin_name": "Pedro Penduko",
            "walkin_purok": "Purok 1",
            "document_type": "Barangay Clearance",
            "purpose": "Employment Requirement",
            "privacy_acknowledged": True,
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("reference", response.data)
        self.assertEqual(response.data["status"], DocumentRequest.Status.PENDING)

        doc = DocumentRequest.objects.filter(
            barangay=self.kiosk_barangay,
            walkin_name="Pedro Penduko",
        ).first()
        self.assertIsNotNone(doc)
        self.assertTrue(doc.is_walkin)
        self.assertEqual(doc.status, DocumentRequest.Status.PENDING)
        self.assertEqual(doc.privacy_notice_version, "kiosk-v1")

    def test_kiosk_issue_report_creation_success(self):
        url = reverse("kiosk-issue-report")
        payload = {
            "barangay_id": self.kiosk_barangay.id,
            "walkin_name": "Concerned Resident",
            "category": IssueReport.Category.INFRASTRUCTURE,
            "title": "Damaged streetlight near bridge",
            "description": "The streetlight pole is broken and flickering dangerously.",
            "location": "Bridge corner Purok 2",
            "privacy_acknowledged": True,
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("reference", response.data)

        report = IssueReport.objects.filter(
            barangay=self.kiosk_barangay,
            title="Damaged streetlight near bridge",
        ).first()
        self.assertIsNotNone(report)
        self.assertEqual(report.status, IssueReport.Status.PENDING)
        self.assertEqual(report.privacy_notice_version, "kiosk-v1")

    def test_kiosk_rejects_inactive_or_unapproved_barangay(self):
        inactive_bgy = Barangay.objects.create(
            name="Inactive Barangay",
        )
        url = reverse("kiosk-queue-ticket")
        payload = {
            "barangay_id": inactive_bgy.id,
            "walkin_name": "Juan Dela Cruz",
            "service_type": "Document Processing & Clearances",
            "privacy_acknowledged": True,
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("barangay_id", response.data)

    def test_kiosk_equipment_borrow_request_success(self):
        url = reverse("kiosk-equipment-borrow-request")
        payload = {
            "barangay_id": self.kiosk_barangay.id,
            "walkin_name": "Elena Ramos",
            "walkin_contact": "09181234567",
            "item_type": EquipmentBorrowRequest.ItemType.MONOBLOCK_CHAIRS,
            "quantity": 50,
            "borrow_date": "2026-11-20",
            "return_date": "2026-11-21",
            "time_slot": "Whole Day",
            "purpose": "Barangay Youth Fellowship Assembly",
            "privacy_acknowledged": True,
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("reference", response.data)
        self.assertTrue(response.data["reference"].startswith("EQ-"))
        self.assertEqual(response.data["status"], EquipmentBorrowRequest.Status.PENDING)

        borrow = EquipmentBorrowRequest.objects.filter(
            barangay=self.kiosk_barangay,
            walkin_name="Elena Ramos",
        ).first()
        self.assertIsNotNone(borrow)
        self.assertTrue(borrow.is_walkin)
        self.assertIsNone(borrow.resident)
        self.assertEqual(borrow.quantity, 50)
        self.assertEqual(borrow.status, EquipmentBorrowRequest.Status.PENDING)

    def test_kiosk_equipment_borrow_date_validation(self):
        url = reverse("kiosk-equipment-borrow-request")
        payload = {
            "barangay_id": self.kiosk_barangay.id,
            "walkin_name": "Elena Ramos",
            "item_type": EquipmentBorrowRequest.ItemType.TENT_CANOPY,
            "quantity": 2,
            "borrow_date": "2026-11-22",
            "return_date": "2026-11-20",  # Invalid: earlier than borrow_date
            "purpose": "Family gathering",
            "privacy_acknowledged": True,
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("return_date", response.data)

    def test_kiosk_queue_ticket_with_equipment_service_type(self):
        url = reverse("kiosk-queue-ticket")
        payload = {
            "barangay_id": self.kiosk_barangay.id,
            "walkin_name": "Rosa Martinez",
            "service_type": "Equipment & Facility Borrowing",
            "privacy_acknowledged": True,
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("reference", response.data)
        self.assertEqual(response.data["status"], QueueTicket.Status.WAITING)
