from datetime import date

from django.urls import reverse
from rest_framework import status

from gridy_auth.models import (
    Barangay,
    BarangayApplication,
    LoginEvent,
    Resident,
    ResidentTransferRequest,
    User,
)
from gridy_services.models import DocumentRequest, QueueTicket
from .base import IsolatedAuthAPITestCase


class LoginEventScopeAPITests(IsolatedAuthAPITestCase):
    def setUp(self):
        self.barangay = Barangay.objects.create(name="Login Event Test Barangay")
        self.other_barangay = Barangay.objects.create(name="Other Login Event Barangay")
        self.admin = User.objects.create_user(
            username="login_event_admin",
            password="SecurePassword123!",
            role=User.Role.ADMIN,
            barangay=self.barangay,
        )
        self.staff = User.objects.create_user(
            username="login_event_staff",
            password="SecurePassword123!",
            role=User.Role.FIELD_OFFICIAL,
            barangay=self.barangay,
        )
        self.other_staff = User.objects.create_user(
            username="other_login_event_staff",
            password="SecurePassword123!",
            role=User.Role.FIELD_OFFICIAL,
            barangay=self.other_barangay,
        )
        self.resident = User.objects.create_user(
            username="login_event_resident",
            password="SecurePassword123!",
            role=User.Role.RESIDENT,
            barangay=self.barangay,
        )
        for user in (self.admin, self.staff, self.other_staff, self.resident):
            LoginEvent.objects.create(
                user=user,
                ip_address="192.0.2.10",
                user_agent="Test Browser",
            )

    def test_admin_sees_own_and_only_same_barangay_field_staff_events(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(reverse("auth-login-events"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rows = response.data["results"] if isinstance(response.data, dict) else response.data
        self.assertEqual(
            {row["username"] for row in rows},
            {self.admin.username, self.staff.username},
        )

    def test_resident_or_field_staff_sees_only_own_events(self):
        self.client.force_authenticate(user=self.staff)

        response = self.client.get(reverse("auth-login-events"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rows = response.data["results"] if isinstance(response.data, dict) else response.data
        self.assertEqual({row["username"] for row in rows}, {self.staff.username})


class ResidentTransferAPITests(IsolatedAuthAPITestCase):
    def setUp(self):
        self.source = Barangay.objects.create(name="Transfer Source Barangay")
        self.destination = Barangay.objects.create(name="Transfer Destination Barangay")
        self.other = Barangay.objects.create(name="Transfer Other Barangay")
        for number, barangay in enumerate((self.source, self.destination, self.other), start=1):
            BarangayApplication.objects.create(
                name=barangay.name,
                municipality="Test City",
                province="Test Province",
                applicant_name=f"Applicant {number}",
                applicant_position="Secretary",
                applicant_email=f"applicant-{number}@example.test",
                applicant_phone="09123456789",
                status=BarangayApplication.Status.APPROVED,
                created_barangay=barangay,
                review_verified=True,
            )
        self.resident = User.objects.create_user(
            username="transfer_resident",
            password="SecurePassword123!",
            email="transfer-resident@example.test",
            role=User.Role.RESIDENT,
            barangay=self.source,
        )
        Resident.objects.create(
            user=self.resident,
            full_name="Transfer Resident",
            birth_date=date(1990, 1, 1),
            is_verified=True,
        )
        self.destination_admin = User.objects.create_user(
            username="transfer_destination_admin",
            password="SecurePassword123!",
            role=User.Role.ADMIN,
            barangay=self.destination,
        )
        self.other_admin = User.objects.create_user(
            username="transfer_other_admin",
            password="SecurePassword123!",
            role=User.Role.ADMIN,
            barangay=self.other,
        )
        self.client.force_authenticate(user=self.resident)

    def _create_transfer(self):
        return self.client.post(
            reverse("resident-transfer-list"),
            {
                "destination_barangay_id": self.destination.pk,
                "reason": "I moved to this Barangay.",
            },
            format="json",
        )

    def test_resident_can_submit_one_pending_transfer_and_only_see_their_own(self):
        response = self._create_transfer()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], ResidentTransferRequest.Status.PENDING)
        self.assertEqual(response.data["source_barangay_name"], self.source.name)
        duplicate_response = self._create_transfer()
        self.assertEqual(duplicate_response.status_code, status.HTTP_400_BAD_REQUEST)

        self.client.force_authenticate(user=self.other_admin)
        list_response = self.client.get(reverse("resident-transfer-list"))
        rows = list_response.data["results"] if isinstance(list_response.data, dict) else list_response.data
        self.assertEqual(rows, [])

    def test_only_receiving_admin_can_review_and_must_confirm_independent_verification(self):
        create_response = self._create_transfer()
        transfer_id = create_response.data["id"]
        approve_url = reverse("resident-transfer-approve", args=[transfer_id])

        self.client.force_authenticate(user=self.other_admin)
        denied = self.client.post(approve_url, {"residency_confirmed": True}, format="json")
        self.assertEqual(denied.status_code, status.HTTP_404_NOT_FOUND)

        self.client.force_authenticate(user=self.destination_admin)
        missing_confirmation = self.client.post(approve_url, {}, format="json")
        self.assertEqual(missing_confirmation.status_code, status.HTTP_400_BAD_REQUEST)
        transfer = ResidentTransferRequest.objects.get(pk=transfer_id)
        self.assertEqual(transfer.status, ResidentTransferRequest.Status.PENDING)

    def test_approval_moves_resident_and_pins_legacy_records_to_source_barangay(self):
        document = DocumentRequest.objects.create(
            user=self.resident,
            barangay=None,
            document_type="Barangay Clearance",
        )
        ticket = QueueTicket.objects.create(
            user=self.resident,
            barangay=None,
            ticket_number="T099",
            service_type="Barangay Clearance",
            status=QueueTicket.Status.WAITING,
            document_request=document,
        )
        create_response = self._create_transfer()
        transfer_id = create_response.data["id"]

        self.client.force_authenticate(user=self.destination_admin)
        response = self.client.post(
            reverse("resident-transfer-approve", args=[transfer_id]),
            {"residency_confirmed": True},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.resident.refresh_from_db()
        document.refresh_from_db()
        ticket.refresh_from_db()
        self.assertEqual(self.resident.barangay_id, self.destination.pk)
        self.assertEqual(document.barangay_id, self.source.pk)
        self.assertEqual(ticket.barangay_id, self.source.pk)
        transfer = ResidentTransferRequest.objects.get(pk=transfer_id)
        self.assertTrue(transfer.residency_confirmed)
        self.assertEqual(transfer.status, ResidentTransferRequest.Status.APPROVED)

    def test_rejection_requires_a_reason(self):
        create_response = self._create_transfer()
        self.client.force_authenticate(user=self.destination_admin)

        response = self.client.post(
            reverse("resident-transfer-reject", args=[create_response.data["id"]]),
            {"review_note": "  "},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
