from datetime import timedelta
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from gridy_auth.models import Barangay, BarangayApplication, Resident, User
from gridy_services.models import (
    DocumentRequest,
    EquipmentBorrowRequest,
    MANILA_TIME_ZONE,
    QueueTicket,
)
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

    def _future_dates(self, start_offset=1, return_offset=2):
        today = timezone.localtime(timezone.now(), MANILA_TIME_ZONE).date()
        return str(today + timedelta(days=start_offset)), str(today + timedelta(days=return_offset))

    def test_kiosk_equipment_borrow_requires_auth_mode_and_rejects_anonymous(self):
        url = reverse("kiosk-equipment-borrow-request")
        borrow_date, return_date = self._future_dates()
        payload = {
            "barangay_id": self.kiosk_barangay.id,
            "walkin_name": "Anonymous Stranger",
            "walkin_contact": "09181234567",
            "walkin_purok": "Purok 2",
            "borrower_id_type": "Barangay ID",
            "item_type": EquipmentBorrowRequest.ItemType.MONOBLOCK_CHAIRS,
            "quantity": 10,
            "borrow_date": borrow_date,
            "return_date": return_date,
            "purpose": "Barangay community outreach event.",
            "privacy_acknowledged": True,
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("auth_mode", response.data)
        self.assertEqual(EquipmentBorrowRequest.objects.count(), 0)

    def test_kiosk_equipment_borrow_with_verified_resident_credentials_success(self):
        verified_user = User.objects.create_user(
            username="kiosk_verified_res",
            email="kiosk.verified@example.test",
            password="ResidentSecretPassword123!",
            role=User.Role.RESIDENT,
            barangay=self.kiosk_barangay,
        )
        Resident.objects.create(
            user=verified_user,
            full_name="Maria Clara Santos",
            birth_date="1992-08-12",
            is_verified=True,
        )
        url = reverse("kiosk-equipment-borrow-request")
        borrow_date, return_date = self._future_dates()
        payload = {
            "barangay_id": self.kiosk_barangay.id,
            "auth_mode": "resident",
            "resident_username": "kiosk_verified_res",
            "resident_password": "ResidentSecretPassword123!",
            "walkin_contact": "09181234567",
            "walkin_purok": "Purok 3",
            "borrower_id_type": "PhilSys National ID",
            "item_type": EquipmentBorrowRequest.ItemType.MONOBLOCK_CHAIRS,
            "quantity": 50,
            "borrow_date": borrow_date,
            "return_date": return_date,
            "time_slot": "Whole Day",
            "purpose": "Barangay Youth Fellowship Assembly at covered court",
            "privacy_acknowledged": True,
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("reference", response.data)
        self.assertTrue(response.data["reference"].startswith("EQ-"))
        self.assertNotIn("refresh_token", response.cookies)

        borrow = EquipmentBorrowRequest.objects.filter(
            barangay=self.kiosk_barangay,
            resident=verified_user,
        ).first()
        self.assertIsNotNone(borrow)
        self.assertFalse(borrow.is_walkin)
        self.assertEqual(borrow.walkin_name, "Maria Clara Santos")
        self.assertEqual(borrow.walkin_purok, "Purok 3")
        self.assertEqual(borrow.borrower_id_type, "PhilSys National ID")
        self.assertEqual(borrow.kiosk_auth_method, "RESIDENT_VERIFIED")
        self.assertEqual(borrow.quantity, 50)

    def test_kiosk_equipment_borrow_rejects_unverified_or_wrong_barangay_resident(self):
        unverified_user = User.objects.create_user(
            username="kiosk_unverified_res",
            password="ResidentSecretPassword123!",
            role=User.Role.RESIDENT,
            barangay=self.kiosk_barangay,
        )
        Resident.objects.create(
            user=unverified_user,
            full_name="Unverified Resident",
            birth_date="1995-01-01",
            is_verified=False,
        )
        url = reverse("kiosk-equipment-borrow-request")
        borrow_date, return_date = self._future_dates()
        base_payload = {
            "barangay_id": self.kiosk_barangay.id,
            "auth_mode": "resident",
            "resident_username": "kiosk_unverified_res",
            "resident_password": "ResidentSecretPassword123!",
            "walkin_contact": "09181234567",
            "walkin_purok": "Purok 1",
            "borrower_id_type": "Barangay ID",
            "item_type": EquipmentBorrowRequest.ItemType.TABLES,
            "quantity": 2,
            "borrow_date": borrow_date,
            "return_date": return_date,
            "purpose": "Neighborhood meeting at chapel grounds",
            "privacy_acknowledged": True,
        }
        res_unverified = self.client.post(url, base_payload, format="json")
        self.assertEqual(res_unverified.status_code, status.HTTP_400_BAD_REQUEST)

        res_bad_pass = self.client.post(
            url,
            {**base_payload, "resident_password": "WrongPassword123!"},
            format="json",
        )
        self.assertEqual(res_bad_pass.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(EquipmentBorrowRequest.objects.count(), 0)

    def test_kiosk_equipment_borrow_with_staff_pin_and_validation(self):
        url = reverse("kiosk-equipment-borrow-request")
        borrow_date, return_date = self._future_dates()
        payload = {
            "barangay_id": self.kiosk_barangay.id,
            "auth_mode": "staff_pin",
            "staff_kiosk_pin": "4321",
            "walkin_name": "Elena Ramos",
            "walkin_contact": "09181234567",
            "walkin_purok": "Purok 4",
            "borrower_id_type": "Barangay ID",
            "item_type": EquipmentBorrowRequest.ItemType.TENT_CANOPY,
            "quantity": 2,
            "borrow_date": borrow_date,
            "return_date": return_date,
            "purpose": "Family medical outreach gathering in Purok 4",
            "privacy_acknowledged": True,
        }
        # Fails closed when Barangay has no Staff Kiosk PIN configured yet
        no_pin_resp = self.client.post(url, payload, format="json")
        self.assertEqual(no_pin_resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("staff_kiosk_pin", no_pin_resp.data)

        # Configure hashed PIN on Barangay
        self.kiosk_barangay.set_kiosk_staff_pin("4321")
        self.kiosk_barangay.save(update_fields=["kiosk_staff_pin_hash"])

        wrong_pin_resp = self.client.post(
            url,
            {**payload, "staff_kiosk_pin": "9999"},
            format="json",
        )
        self.assertEqual(wrong_pin_resp.status_code, status.HTTP_400_BAD_REQUEST)

        # Rejects past borrow date
        past_date = str(timezone.localtime(timezone.now(), MANILA_TIME_ZONE).date() - timedelta(days=1))
        past_resp = self.client.post(
            url,
            {**payload, "borrow_date": past_date},
            format="json",
        )
        self.assertEqual(past_resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("borrow_date", past_resp.data)

        # Rejects return date earlier than borrow date
        bad_return_resp = self.client.post(
            url,
            {**payload, "return_date": past_date},
            format="json",
        )
        self.assertEqual(bad_return_resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("return_date", bad_return_resp.data)

        # Valid PIN + valid borrower fields succeeds
        ok_resp = self.client.post(url, payload, format="json")
        self.assertEqual(ok_resp.status_code, status.HTTP_201_CREATED)
        borrow = EquipmentBorrowRequest.objects.filter(walkin_name="Elena Ramos").first()
        self.assertIsNotNone(borrow)
        self.assertTrue(borrow.is_walkin)
        self.assertIsNone(borrow.resident)
        self.assertEqual(borrow.kiosk_auth_method, "STAFF_PIN")
        self.assertEqual(borrow.walkin_purok, "Purok 4")
        self.assertEqual(borrow.borrower_id_type, "Barangay ID")

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
