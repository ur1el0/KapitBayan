from datetime import date
from io import BytesIO
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image
from rest_framework import status

from gridy_auth.models import (
    Barangay,
    BarangayApplication,
    LoginEvent,
    Resident,
    ResidentTransferRequest,
    User,
)
from gridy_communications.models import ResidentNotification
from gridy_services.models import DocumentRequest, QueueTicket
from .base import IsolatedAuthAPITestCase


def create_test_image_upload(name="residency-proof.png", *, size=(1, 1), image_format="PNG"):
    image_data = BytesIO()
    Image.new("RGB", size, color="white").save(image_data, format=image_format)
    content_type = Image.MIME[image_format]
    return SimpleUploadedFile(name, image_data.getvalue(), content_type=content_type)


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
        self.profile = Resident.objects.create(
            user=self.resident,
            full_name="Transfer Resident",
            birth_date=date(1990, 1, 1),
            purok="Old Purok 1",
            address_details="Old Street 1",
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

    def _create_transfer(self, **overrides):
        payload = {
            "destination_barangay_id": self.destination.pk,
            "reason": "I moved to this Barangay.",
            "purok": "Purok 4",
            "address_details": "123 Mango Street",
            "proof_of_residency": create_test_image_upload("residency_proof.png"),
        }
        payload.update(overrides)
        storage = ResidentTransferRequest._meta.get_field("proof_of_residency").storage
        with patch.object(
            storage,
            "save",
            side_effect=lambda name, content, max_length=None: name,
        ):
            return self.client.post(
                reverse("resident-transfer-list"),
                payload,
                format="multipart",
            )

    def test_resident_can_submit_one_pending_transfer_and_only_see_their_own(self):
        response = self._create_transfer()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], ResidentTransferRequest.Status.PENDING)
        self.assertEqual(response.data["source_barangay_name"], self.source.name)
        self.assertEqual(response.data["purok"], "Purok 4")
        self.assertEqual(response.data["address_details"], "123 Mango Street")
        self.assertTrue(response.data["has_proof_of_residency"])

        duplicate_response = self._create_transfer()
        self.assertEqual(duplicate_response.status_code, status.HTTP_400_BAD_REQUEST)

        self.client.force_authenticate(user=self.other_admin)
        list_response = self.client.get(reverse("resident-transfer-list"))
        rows = list_response.data["results"] if isinstance(list_response.data, dict) else list_response.data
        self.assertEqual(rows, [])

    def test_submission_requires_proof_of_residency(self):
        response = self.client.post(
            reverse("resident-transfer-list"),
            {
                "destination_barangay_id": self.destination.pk,
                "reason": "I moved here.",
                "purok": "Purok 1",
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("proof_of_residency", response.data)

    def test_proof_media_access_control(self):
        create_response = self._create_transfer()
        transfer_id = create_response.data["id"]
        proof_url = reverse("resident-transfer-proof", args=[transfer_id])

        test_image = BytesIO()
        Image.new("RGB", (10, 10), color="blue").save(test_image, format="PNG")
        raw_bytes = test_image.getvalue()

        storage = ResidentTransferRequest._meta.get_field("proof_of_residency").storage
        with patch.object(
            storage,
            "open_private_media",
            side_effect=lambda name, mode="rb": BytesIO(raw_bytes),
        ), patch.object(
            storage,
            "open",
            side_effect=lambda name, mode="rb": BytesIO(raw_bytes),
        ):
            # 1. Resident owner can download their own proof
            resident_proof_resp = self.client.get(proof_url)
            self.assertEqual(resident_proof_resp.status_code, status.HTTP_200_OK)
            self.assertEqual(resident_proof_resp["Cache-Control"], "private, no-store, max-age=0")

            # 2. Destination Admin can inspect applicant's proof
            self.client.force_authenticate(user=self.destination_admin)
            admin_proof_resp = self.client.get(proof_url)
            self.assertEqual(admin_proof_resp.status_code, status.HTTP_200_OK)

        # 3. Non-destination Admin is forbidden (404)
        self.client.force_authenticate(user=self.other_admin)
        other_admin_resp = self.client.get(proof_url)
        self.assertEqual(other_admin_resp.status_code, status.HTTP_404_NOT_FOUND)

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

    @patch("gridy_communications.services.send_mail", return_value=1)
    def test_approval_moves_resident_updates_profile_and_pins_legacy_records(self, mock_send_mail):
        document = DocumentRequest.objects.create(
            user=self.resident,
            barangay=None,
            document_type="Barangay Clearance",
            status=DocumentRequest.Status.RELEASED,
        )
        ticket = QueueTicket.objects.create(
            user=self.resident,
            barangay=None,
            ticket_number="T099",
            service_type="Barangay Clearance",
            status=QueueTicket.Status.WAITING,
            document_request=document,
        )
        blocked_transfer = self._create_transfer()
        self.assertEqual(blocked_transfer.status_code, status.HTTP_400_BAD_REQUEST)

        ticket.status = QueueTicket.Status.COMPLETED
        ticket.save(update_fields=["status", "updated_at"])
        create_response = self._create_transfer()
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        transfer_id = create_response.data["id"]

        self.client.force_authenticate(user=self.destination_admin)
        response = self.client.post(
            reverse("resident-transfer-approve", args=[transfer_id]),
            {"residency_confirmed": True},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.resident.refresh_from_db()
        self.profile.refresh_from_db()
        document.refresh_from_db()
        ticket.refresh_from_db()

        # Account moved to destination Barangay
        self.assertEqual(self.resident.barangay_id, self.destination.pk)
        # Residence profile updated to destination Purok and address
        self.assertEqual(self.profile.purok, "Purok 4")
        self.assertEqual(self.profile.address_details, "123 Mango Street")
        # Historical records remain pinned to original source Barangay
        self.assertEqual(document.barangay_id, self.source.pk)
        self.assertEqual(ticket.barangay_id, self.source.pk)

        transfer = ResidentTransferRequest.objects.get(pk=transfer_id)
        self.assertTrue(transfer.residency_confirmed)
        self.assertEqual(transfer.status, ResidentTransferRequest.Status.APPROVED)

        # Resident notified
        mock_send_mail.assert_called()
        self.assertTrue(
            ResidentNotification.objects.filter(
                user=self.resident,
                data__status="APPROVED",
            ).exists()
        )

    def test_transfer_approval_is_blocked_if_open_work_arrives_after_request(self):
        create_response = self._create_transfer()
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        transfer_id = create_response.data["id"]
        DocumentRequest.objects.create(
            user=self.resident,
            barangay=self.source,
            document_type="Certificate of Residency",
            status=DocumentRequest.Status.PENDING,
        )

        self.client.force_authenticate(user=self.destination_admin)
        response = self.client.post(
            reverse("resident-transfer-approve", args=[transfer_id]),
            {"residency_confirmed": True},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.resident.refresh_from_db()
        self.assertEqual(self.resident.barangay_id, self.source.pk)

    @patch("gridy_communications.services.send_mail", return_value=1)
    def test_rejection_requires_a_reason_and_notifies_resident(self, mock_send_mail):
        create_response = self._create_transfer()
        self.client.force_authenticate(user=self.destination_admin)

        # 1. Blank rejection reason fails
        blank_resp = self.client.post(
            reverse("resident-transfer-reject", args=[create_response.data["id"]]),
            {"review_note": "  "},
            format="json",
        )
        self.assertEqual(blank_resp.status_code, status.HTTP_400_BAD_REQUEST)

        # 2. Valid rejection succeeds and sends notification
        reject_resp = self.client.post(
            reverse("resident-transfer-reject", args=[create_response.data["id"]]),
            {"review_note": "Incomplete address details."},
            format="json",
        )
        self.assertEqual(reject_resp.status_code, status.HTTP_200_OK)
        mock_send_mail.assert_called()
        self.assertTrue(
            ResidentNotification.objects.filter(
                user=self.resident,
                data__status="REJECTED",
            ).exists()
        )
