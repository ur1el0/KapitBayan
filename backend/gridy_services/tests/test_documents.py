from decimal import Decimal
import uuid
from unittest.mock import patch
from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from gridy_audit.models import AuditLog
from gridy_auth.models import Barangay, Resident, User
from gridy_communications.models import ResidentNotification
from gridy_services.models import DocumentRequest, DocumentServiceOffering, QueueTicket
from .base import ServiceAPIBaseTestCase


class DocumentRequestAPITests(ServiceAPIBaseTestCase):
    def _assign_shared_barangay(self):
        barangay = Barangay.objects.create(name="Document API Assigned Barangay")
        self.official.barangay = barangay
        self.official.save(update_fields=["barangay"])
        self.resident.barangay = barangay
        self.resident.save(update_fields=["barangay"])
        return barangay

    def test_resident_can_create_document_request(self):
        self._assign_shared_barangay()
        self.client.force_login(self.resident)
        url = reverse('document-request-list')
        response = self.client.post(
            url,
            {
                "document_type": "Barangay Clearance",
                "status": DocumentRequest.Status.RELEASED,
                "admin_notes": "Forged notes",
                "is_walkin": True,
                "walkin_name": "Forged Walk-in Applicant",
                "walkin_purok": "Purok 99",
                "or_number": "FORGED-OR",
                "fee_amount": "999.00",
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created_request = DocumentRequest.objects.get(pk=response.data["id"])
        self.assertEqual(created_request.user, self.resident)
        self.assertEqual(created_request.status, DocumentRequest.Status.PENDING)
        self.assertEqual(created_request.admin_notes, "")
        self.assertFalse(created_request.is_walkin)
        self.assertFalse(created_request.walkin_name)
        self.assertFalse(created_request.walkin_purok)
        self.assertFalse(created_request.or_number)
        self.assertEqual(str(created_request.fee_amount), "0.00")
        self.assertEqual(
            response.data["system_reference"],
            f"KB-DOC-{created_request.pk:08d}",
        )

    def test_document_submission_key_replays_identical_request_and_rejects_reuse(self):
        self._assign_shared_barangay()
        self.client.force_login(self.resident)
        key = str(uuid.uuid4())
        url = reverse("document-request-list")
        payload = {
            "document_type": "Barangay Clearance",
            "purpose": "Proof of residency",
            "urgency_tag": "REGULAR",
        }

        first = self.client.post(
            url,
            payload,
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
        )
        replay = self.client.post(
            url,
            payload,
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
        )
        conflict = self.client.post(
            url,
            {**payload, "purpose": "Different purpose"},
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
        )

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(replay.status_code, status.HTTP_200_OK)
        self.assertEqual(replay.data["id"], first.data["id"])
        self.assertEqual(conflict.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(DocumentRequest.objects.count(), 1)

    def test_database_rejects_duplicate_barangay_or_ignoring_case_and_outer_space(self):
        barangay = self._assign_shared_barangay()
        DocumentRequest.objects.create(
            user=self.resident,
            barangay=barangay,
            document_type="Barangay Clearance",
            or_number="OR-2030-0042",
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                DocumentRequest.objects.create(
                    user=self.resident,
                    barangay=barangay,
                    document_type="Barangay Clearance",
                    or_number="  or-2030-0042  ",
                )

    def test_official_can_create_walkin_document_request(self):
        barangay = Barangay.objects.create(name="Walk-in Test Barangay")
        self.official.barangay = barangay
        self.official.save(update_fields=["barangay"])
        self.client.force_login(self.official)
        url = reverse('document-request-list')
        response = self.client.post(
            url,
            {
                "document_type": "Barangay Clearance",
                "walkin_name": "Juan Dela Cruz",
                "walkin_purok": "Purok 3",
                "is_walkin": False,
                "status": DocumentRequest.Status.RELEASED,
                "admin_notes": "Forged notes",
                "or_number": "FORGED-OR",
                "fee_amount": "999.00",
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created_request = DocumentRequest.objects.get(pk=response.data["id"])
        self.assertTrue(created_request.is_walkin)
        self.assertEqual(created_request.walkin_name, "Juan Dela Cruz")
        self.assertEqual(created_request.barangay, barangay)
        self.assertIsNone(created_request.user)
        self.assertEqual(created_request.status, DocumentRequest.Status.PENDING)
        self.assertEqual(created_request.admin_notes, "")
        self.assertFalse(created_request.or_number)
        self.assertEqual(str(created_request.fee_amount), "0.00")

    @patch("gridy_services.views.documents.pisa.CreatePDF")
    def test_official_can_generate_walkin_pdf(self, create_pdf):
        barangay = Barangay.objects.create(name="Walk-in PDF Test Barangay")
        self.official.barangay = barangay
        self.official.save(update_fields=["barangay"])
        self.client.force_login(self.official)

        document_request = DocumentRequest.objects.create(
            barangay=barangay,
            is_walkin=True,
            walkin_name="Juan Dela Cruz",
            walkin_purok="Purok Maligaya",
            document_type="Barangay Clearance",
            status=DocumentRequest.Status.RELEASED,
            or_number="OR-WALKIN-1042",
        )
        create_pdf.return_value.err = False

        response = self.client.get(
            reverse(
                "document-request-generate-pdf",
                args=[document_request.pk],
            )
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("OR_OR-WALKIN-1042.pdf", response["Content-Disposition"])
        self.assertEqual(response["Cache-Control"], "private, no-store, max-age=0")

        rendered_html = create_pdf.call_args.args[0]
        self.assertIn("OR-WALKIN-1042", rendered_html)
        self.assertNotIn("JUAN DELA CRUZ", rendered_html)
        self.assertNotIn(barangay.name, rendered_html)
        self.assertNotIn("Purok Maligaya", rendered_html)

    @patch("gridy_services.views.documents.pisa.CreatePDF")
    def test_resident_pdf_preserves_purok_number(self, create_pdf):
        barangay = Barangay.objects.create(name="Resident PDF Test Barangay")
        self.resident.barangay = barangay
        self.resident.save(update_fields=["barangay"])

        resident_profile = self.resident.profile
        resident_profile.purok = "3"
        resident_profile.save(update_fields=["purok"])

        document_request = DocumentRequest.objects.create(
            user=self.resident,
            barangay=barangay,
            document_type="Barangay Clearance",
            status=DocumentRequest.Status.RELEASED,
            or_number="OR-RESIDENT-2042",
        )
        self.client.force_login(self.resident)
        create_pdf.return_value.err = False

        response = self.client.get(
            reverse(
                "document-request-generate-pdf",
                args=[document_request.pk],
            )
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")

        rendered_html = create_pdf.call_args.args[0]
        self.assertIn("OR-RESIDENT-2042", rendered_html)
        self.assertNotIn("Purok 3", rendered_html)

    def test_pdf_is_unavailable_until_released_and_assigned_an_or_number(self):
        document = DocumentRequest.objects.create(
            user=self.resident,
            document_type="Barangay Clearance",
            status=DocumentRequest.Status.READY_FOR_PICKUP,
        )
        self.client.force_login(self.resident)

        response = self.client.get(
            reverse("document-request-generate-pdf", args=[document.pk])
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        document.status = DocumentRequest.Status.RELEASED
        document.save(update_fields=["status"])
        response_without_or = self.client.get(
            reverse("document-request-generate-pdf", args=[document.pk])
        )
        self.assertEqual(response_without_or.status_code, status.HTTP_409_CONFLICT)

    def test_official_creating_walkin_requires_name(self):
        # Walk-in submissions without a resident name are rejected with 400
        self.official.barangay = Barangay.objects.create(
            name="Walk-in Name Test Barangay"
        )
        self.official.save(update_fields=["barangay"])
        self.client.force_login(self.official)

        url = reverse('document-request-list')
        payload = {
            "document_type": "Barangay Clearance"
        }
        response = self.client.post(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_field_official_cannot_create_walkin_document_request(self):
        barangay = Barangay.objects.create(name="Field Official Test Barangay")
        field_official = User.objects.create_user(
            username="field_official_document_test",
            password="SecurePassword123!",
            email="field-doc-test@example.com",
            role=User.Role.FIELD_OFFICIAL,
            barangay=barangay,
        )
        self.client.force_login(field_official)

        response = self.client.post(
            reverse('document-request-list'),
            {
                "document_type": "Barangay Clearance",
                "walkin_name": "Juan Dela Cruz",
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(DocumentRequest.objects.exists())

    def test_retired_role_cannot_create_document_request(self):
        barangay_operator = User.objects.create_user(
            username="barangay_operator_document_test",
            password="SecurePassword123!",
            email="barangay-operator-doc-test@example.com",
            role="BARANGAY_OPERATOR",
        )
        self.client.force_authenticate(barangay_operator)

        response = self.client.post(
            reverse('document-request-list'),
            {"document_type": "Barangay Clearance"},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(DocumentRequest.objects.exists())

    def test_official_without_barangay_cannot_create_walkin(self):
        self.client.force_login(self.official)

        response = self.client.post(
            reverse('document-request-list'),
            {
                "document_type": "Barangay Clearance",
                "walkin_name": "Juan Dela Cruz",
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(DocumentRequest.objects.exists())

    def test_unverified_resident_cannot_create_document_request(self):
        # Residents who have not yet had their identity/residency verified by the barangay are blocked
        unverified_user = User.objects.create_user(
            username="unverified_resident",
            password="SecurePassword123!",
            email="unverified@example.com",
            role=User.Role.RESIDENT
        )
        Resident.objects.create(
            user=unverified_user,
            full_name="Unverified Resident",
            birth_date="1998-08-20",
            is_verified=False
        )
        self.client.force_login(unverified_user)
        url = reverse('document-request-list')
        payload = {"document_type": "Barangay Clearance"}
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_resident_validated_blocked(self):
        self.client.force_login(self.resident)
        doc_req = DocumentRequest.objects.create(
            user=self.resident,
            document_type="Barangay Clearance",
        )
        url = reverse('document-request-validate', args=[doc_req.id])
        payload = {
            "status": "APPROVED"
        }
        response = self.client.patch(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        doc_req.refresh_from_db()
        self.assertEqual(doc_req.status, DocumentRequest.Status.PENDING)

    def test_official_can_validate_document_request(self):
        # 1. Setup: Log in the admin and create a dummy request
        barangay = self._assign_shared_barangay()
        self.client.force_login(self.official)
        doc_req = DocumentRequest.objects.create(
            user=self.resident,
            barangay=barangay,
            document_type="Barangay Clearance",
        )

        # 2. Action: Hit the custom /validate/ endpoint
        url = reverse('document-request-validate', args=[doc_req.id])
        payload = {
            'status': 'PROCESSING',
            'admin_notes': 'Document is now being processed'
        }
        response = self.client.patch(url, payload, format="json")

        # 3. Assertions
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify the database actually updated
        doc_req.refresh_from_db()
        self.assertEqual(doc_req.status, DocumentRequest.Status.PROCESSING)
        notification = ResidentNotification.objects.get(user=self.resident)
        self.assertEqual(notification.notification_type, ResidentNotification.Type.DOCUMENT)
        self.assertIn("PROCESSING", notification.message.upper())
        self.assertEqual(notification.data["document_request_id"], str(doc_req.pk))

        # Verify the audit log was fired
        self.assertEqual(AuditLog.objects.filter(action_type=AuditLog.ActionType.DOCUMENT_ACTION).count(), 1)

    def test_releasing_document_resolves_linked_pickup_queue_ticket(self):
        barangay = self._assign_shared_barangay()
        self.client.force_login(self.official)
        tickets_by_status = {}

        for index, queue_status in enumerate(
            (QueueTicket.Status.WAITING, QueueTicket.Status.SERVING),
            start=1,
        ):
            document = DocumentRequest.objects.create(
                user=self.resident,
                barangay=barangay,
                document_type="Barangay Clearance",
                status=DocumentRequest.Status.READY_FOR_PICKUP,
                fee_amount=Decimal("0.00"),
                fee_assessment_status=DocumentRequest.FeeAssessmentStatus.WAIVED,
                fee_assessed_by=self.official,
                fee_assessed_at=timezone.now(),
                fee_waiver_reason=f"Approved waiver {index}",
                payment_status=DocumentRequest.PaymentStatus.NOT_REQUIRED,
            )
            tickets_by_status[queue_status] = QueueTicket.objects.create(
                user=self.resident,
                barangay=barangay,
                document_request=document,
                service_type="Barangay Clearance",
                status=queue_status,
            )

            response = self.client.patch(
                reverse("document-request-validate", args=[document.pk]),
                {"status": DocumentRequest.Status.RELEASED},
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        tickets_by_status[QueueTicket.Status.WAITING].refresh_from_db()
        tickets_by_status[QueueTicket.Status.SERVING].refresh_from_db()
        self.assertEqual(
            tickets_by_status[QueueTicket.Status.WAITING].status,
            QueueTicket.Status.CANCELLED,
        )
        self.assertEqual(
            tickets_by_status[QueueTicket.Status.SERVING].status,
            QueueTicket.Status.COMPLETED,
        )

    def test_official_can_delete_released_document_request(self):
        barangay = self._assign_shared_barangay()
        self.client.force_login(self.official)
        doc = DocumentRequest.objects.create(
            user=self.resident,
            barangay=barangay,
            document_type="Barangay Clearance",
            status=DocumentRequest.Status.RELEASED
        )
        url = reverse('document-request-detail', args=[doc.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(DocumentRequest.objects.filter(id=doc.id).exists())
        self.assertTrue(AuditLog.objects.filter(action_type=AuditLog.ActionType.DOCUMENT_ACTION, action_by=self.official).exists())

    def test_deleting_legacy_released_request_resolves_linked_queue_ticket(self):
        barangay = self._assign_shared_barangay()
        self.client.force_login(self.official)
        for queue_status, expected_status in (
            (QueueTicket.Status.WAITING, QueueTicket.Status.CANCELLED),
            (QueueTicket.Status.SERVING, QueueTicket.Status.COMPLETED),
        ):
            document = DocumentRequest.objects.create(
                user=self.resident,
                barangay=barangay,
                document_type="Barangay Clearance",
                status=DocumentRequest.Status.RELEASED,
            )
            ticket = QueueTicket.objects.create(
                user=self.resident,
                barangay=barangay,
                document_request=document,
                service_type="Barangay Clearance",
                status=queue_status,
            )

            response = self.client.delete(
                reverse("document-request-detail", args=[document.pk])
            )

            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            ticket.refresh_from_db()
            self.assertEqual(ticket.status, expected_status)
            self.assertIsNone(ticket.document_request_id)

    def test_official_can_delete_rejected_document_request(self):
        barangay = self._assign_shared_barangay()
        self.client.force_login(self.official)
        doc = DocumentRequest.objects.create(
            user=self.resident,
            barangay=barangay,
            document_type="Barangay Clearance",
            status=DocumentRequest.Status.REJECTED
        )
        url = reverse('document-request-detail', args=[doc.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(DocumentRequest.objects.filter(id=doc.id).exists())

    def test_official_cannot_delete_pending_document_request(self):
        barangay = self._assign_shared_barangay()
        self.client.force_login(self.official)
        doc = DocumentRequest.objects.create(
            user=self.resident,
            barangay=barangay,
            document_type="Barangay Clearance",
            status=DocumentRequest.Status.PENDING
        )
        url = reverse('document-request-detail', args=[doc.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(DocumentRequest.objects.filter(id=doc.id).exists())

    def test_resident_can_cancel_pending_document_request(self):
        self.client.force_login(self.resident)
        doc = DocumentRequest.objects.create(
            user=self.resident,
            document_type="Barangay Clearance",
            status=DocumentRequest.Status.PENDING
        )
        url = reverse('document-request-detail', args=[doc.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(DocumentRequest.objects.filter(id=doc.id).exists())
        self.assertTrue(
            AuditLog.objects.filter(
                action_type=AuditLog.ActionType.DOCUMENT_ACTION,
                action_by=self.resident
            ).exists()
        )

    def test_resident_cannot_delete_released_document_request(self):
        self.client.force_login(self.resident)
        doc = DocumentRequest.objects.create(
            user=self.resident,
            document_type="Barangay Clearance",
            status=DocumentRequest.Status.RELEASED
        )
        url = reverse('document-request-detail', args=[doc.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data.get('detail'), "You can only cancel document requests that are still pending review.")
        self.assertTrue(DocumentRequest.objects.filter(id=doc.id).exists())

    def test_resident_cannot_cancel_other_resident_pending_request(self):
        other_resident = User.objects.create_user(
            username="other_resident",
            password="SecurePassword123!",
            email="other@example.com",
            role=User.Role.RESIDENT
        )
        doc = DocumentRequest.objects.create(
            user=other_resident,
            document_type="Barangay Clearance",
            status=DocumentRequest.Status.PENDING
        )
        self.client.force_login(self.resident)
        url = reverse('document-request-detail', args=[doc.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(DocumentRequest.objects.filter(id=doc.id).exists())

    def test_exempt_resident_document_types_are_zero_fee(self):
        self._assign_shared_barangay()
        self.client.force_login(self.resident)
        url = reverse("document-request-list")

        for document_type in (
            "Certificate of Indigency",
            "First Time Job Seeker Certificate",
        ):
            with self.subTest(document_type=document_type):
                response = self.client.post(
                    url,
                    {
                        "document_type": document_type,
                        "fee_amount": "99.00",
                    },
                    format="json",
                )

                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                created_request = DocumentRequest.objects.get(pk=response.data["id"])
                self.assertEqual(str(created_request.fee_amount), "0.00")

    def test_exempt_walkin_document_type_is_zero_fee(self):
        barangay = Barangay.objects.create(name="Exempt Fee Test Barangay")
        self.official.barangay = barangay
        self.official.save(update_fields=["barangay"])
        self.client.force_login(self.official)
        url = reverse("document-request-list")

        response = self.client.post(
            url,
            {
                "document_type": "First Time Job Seeker Certificate",
                "walkin_name": "Juan Dela Cruz",
                "fee_amount": "75.00",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created_request = DocumentRequest.objects.get(pk=response.data["id"])
        self.assertEqual(str(created_request.fee_amount), "0.00")
        self.assertEqual(created_request.status, DocumentRequest.Status.PENDING)

    def test_staff_validation_cannot_add_fee_to_exempt_document(self):
        self._assign_shared_barangay()
        document_request = DocumentRequest.objects.create(
            user=self.resident,
            barangay=self.official.barangay,
            document_type="Certificate of Indigency",
            fee_amount="25.00",
        )
        self.client.force_login(self.official)
        url = reverse("document-request-validate", args=[document_request.pk])

        response = self.client.patch(
            url,
            {
                "status": DocumentRequest.Status.PROCESSING,
                "fee_amount": "100.00",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        document_request.refresh_from_db()
        self.assertEqual(str(document_request.fee_amount), "0.00")

    def test_resident_clearance_request_auto_snapshots_canonical_requirements(self):
        self._assign_shared_barangay()
        self.client.force_login(self.resident)
        url = reverse("document-request-list")

        response = self.client.post(
            url,
            {
                "document_type": "Barangay Clearance",
                "urgency_tag": "REGULAR",
                "purpose": "Employment requirement",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created_request = DocumentRequest.objects.get(pk=response.data["id"])
        self.assertIn("Government ID or proof of residency", created_request.requirements_snapshot)
        self.assertIn("Community Tax Certificate (Cedula)", created_request.requirements_snapshot)
        self.assertEqual(created_request.published_fee_amount_snapshot, Decimal("50.00"))

    def test_resident_request_auto_links_active_offering(self):
        barangay = self._assign_shared_barangay()
        custom_offering = DocumentServiceOffering.objects.create(
            barangay=barangay,
            document_type="Barangay Clearance",
            requirements=["Barangay Voter Certification", "Latest Cedula 2026"],
            published_fee_amount=Decimal("75.00"),
            details="Custom local requirements for Ibabang Dupay.",
            is_active=True,
        )

        self.client.force_login(self.resident)
        url = reverse("document-request-list")

        response = self.client.post(
            url,
            {
                "document_type": "Barangay Clearance",
                "urgency_tag": "REGULAR",
                "purpose": "Local ID",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created_request = DocumentRequest.objects.get(pk=response.data["id"])
        self.assertEqual(created_request.offering, custom_offering)
        self.assertEqual(created_request.requirements_snapshot, ["Barangay Voter Certification", "Latest Cedula 2026"])
        self.assertEqual(created_request.published_fee_amount_snapshot, Decimal("75.00"))
        self.assertEqual(created_request.details_snapshot, "Custom local requirements for Ibabang Dupay.")
