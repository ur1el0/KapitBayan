from io import BytesIO
from importlib import import_module
from types import SimpleNamespace
from django.apps import apps
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase
from gridy_audit.models import AuditLog
from gridy_auth.models import Barangay, Resident, User
from gridy_services.models import DocumentRequest, PaymentRecipient


class DocumentPaymentWorkflowTests(APITestCase):
    def setUp(self):
        self.barangay = Barangay.objects.create(name="Payment Workflow Barangay")
        self.resident = User.objects.create_user(
            username="payment_resident",
            password="SecurePassword123!",
            email="payment-resident@example.com",
            role=User.Role.RESIDENT,
            barangay=self.barangay,
        )
        Resident.objects.create(
            user=self.resident,
            full_name="Payment Resident",
            birth_date="1990-01-01",
            is_verified=True,
        )
        self.official = User.objects.create_user(
            username="payment_official",
            password="SecurePassword123!",
            email="payment-official@example.com",
            role=User.Role.ADMIN,
            barangay=self.barangay,
        )
        self.gcash_recipient = PaymentRecipient.objects.create(
            barangay=self.barangay,
            provider=PaymentRecipient.Provider.GCASH,
            display_name="GCash - Barangay Hall",
            recipient_name="Barangay Treasurer",
            recipient_identifier="09170000000",
        )
        image_buffer = BytesIO()
        Image.new("RGB", (20, 20), color="blue").save(image_buffer, format="PNG")
        self.sample_image_bytes = image_buffer.getvalue()

    def _sample_image(self):
        return SimpleUploadedFile(
            "receipt.png",
            self.sample_image_bytes,
            content_type="image/png",
        )

    def make_request(self, **overrides):
        values = {
            "user": self.resident,
            "barangay": self.barangay,
            "document_type": "Barangay Clearance",
            "purpose": "Employment",
            "status": DocumentRequest.Status.READY_FOR_PICKUP,
            "fee_amount": "50.00",
            "fee_assessment_status": DocumentRequest.FeeAssessmentStatus.ASSESSED,
            "payment_status": DocumentRequest.PaymentStatus.UNPAID,
        }
        values.update(overrides)
        return DocumentRequest.objects.create(**values)


    def test_resident_can_list_only_active_payment_recipients_in_own_barangay(self):
        own_recipient = PaymentRecipient.objects.create(
            barangay=self.barangay,
            provider=PaymentRecipient.Provider.MAYA,
            display_name="Maya - Barangay Hall",
            recipient_name="Barangay Mabini Treasurer",
            recipient_identifier="09170000001",
            instructions="Use the clearance request number as the note.",
        )
        PaymentRecipient.objects.create(
            barangay=self.barangay,
            provider=PaymentRecipient.Provider.GCASH,
            display_name="Inactive GCash",
            recipient_name="Barangay Mabini Treasurer",
            recipient_identifier="09170000002",
            is_active=False,
        )
        other_barangay = Barangay.objects.create(name="Other Recipient Tenant")
        PaymentRecipient.objects.create(
            barangay=other_barangay,
            provider=PaymentRecipient.Provider.GCASH,
            display_name="Other Barangay",
            recipient_name="Other Treasurer",
            recipient_identifier="09179999999",
        )
        self.client.force_authenticate(self.resident)

        response = self.client.get(reverse("payment-recipient-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if isinstance(response.data, dict) else response.data
        self.assertCountEqual(
            [item["id"] for item in results],
            [own_recipient.id, self.gcash_recipient.id],
        )
        maya_result = next(item for item in results if item["id"] == own_recipient.id)
        self.assertEqual(maya_result["provider"], PaymentRecipient.Provider.MAYA)
        self.assertEqual(maya_result["recipient_identifier"], "09170000001")

    def test_barangay_admin_can_configure_and_audit_payment_recipient(self):
        self.client.force_authenticate(self.official)

        created = self.client.post(
            reverse("payment-recipient-list"),
            {
                "provider": PaymentRecipient.Provider.MAYA,
                "display_name": "Maya Treasury",
                "recipient_name": "Barangay Treasurer",
                "recipient_identifier": "09170000001",
                "instructions": "Use the request number as the transfer note.",
            },
            format="json",
        )

        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        recipient = PaymentRecipient.objects.get(pk=created.data["id"])
        self.assertEqual(recipient.barangay, self.barangay)
        self.assertTrue(
            AuditLog.objects.filter(
                action_by=self.official,
                action_type=AuditLog.ActionType.USER_ACTION,
                description__contains=f"payment recipient #{recipient.pk}",
            ).exists()
        )
        self.assertFalse(
            AuditLog.objects.filter(description__contains=recipient.recipient_identifier).exists()
        )

        updated = self.client.patch(
            reverse("payment-recipient-detail", args=[recipient.pk]),
            {"is_active": False},
            format="json",
        )

        self.assertEqual(updated.status_code, status.HTTP_200_OK)
        recipient.refresh_from_db()
        self.assertFalse(recipient.is_active)
        self.assertTrue(
            AuditLog.objects.filter(
                action_by=self.official,
                action_type=AuditLog.ActionType.USER_ACTION,
                description__contains=f"payment recipient #{recipient.pk}",
            ).count()
            >= 2
        )

    def test_payment_recipient_rejects_whitespace_only_destination_fields(self):
        self.client.force_authenticate(self.official)

        response = self.client.post(
            reverse("payment-recipient-list"),
            {
                "provider": PaymentRecipient.Provider.GCASH,
                "display_name": "   ",
                "recipient_name": "Barangay Treasurer",
                "recipient_identifier": "09170000001",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(PaymentRecipient.objects.filter(barangay=self.barangay).exclude(pk=self.gcash_recipient.pk).exists())

    def test_payment_recipient_configuration_is_limited_to_own_barangay_admin(self):
        other_barangay = Barangay.objects.create(name="Other Recipient Tenant")
        other_recipient = PaymentRecipient.objects.create(
            barangay=other_barangay,
            provider=PaymentRecipient.Provider.GCASH,
            display_name="Other Barangay",
            recipient_name="Other Treasurer",
            recipient_identifier="09179999999",
        )
        self.client.force_authenticate(self.official)

        response = self.client.patch(
            reverse("payment-recipient-detail", args=[other_recipient.pk]),
            {"is_active": False},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        other_recipient.refresh_from_db()
        self.assertTrue(other_recipient.is_active)

        field_official = User.objects.create_user(
            username="payment_field_official",
            password="SecurePassword123!",
            role=User.Role.FIELD_OFFICIAL,
            barangay=self.barangay,
        )
        self.client.force_authenticate(field_official)
        field_response = self.client.post(
            reverse("payment-recipient-list"),
            {
                "provider": PaymentRecipient.Provider.MAYA,
                "display_name": "Unauthorized Maya",
                "recipient_name": "Barangay Treasurer",
                "recipient_identifier": "09170000002",
            },
            format="json",
        )
        self.assertEqual(field_response.status_code, status.HTTP_403_FORBIDDEN)

        dilg_admin = User.objects.create_user(
            username="recipient_dilg_admin",
            password="SecurePassword123!",
            role="DILG_ADMIN",
            is_staff=True,
        )
        self.client.force_authenticate(dilg_admin)
        dilg_response = self.client.get(reverse("payment-recipient-list"))
        self.assertEqual(dilg_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_legacy_role_cannot_view_another_tenant_document(self):
        document = self.make_request(
            payment_method=DocumentRequest.PaymentMethod.GCASH,
            payment_recipient=self.gcash_recipient,
            payment_recipient_name_snapshot="Barangay Treasurer",
            payment_recipient_identifier_snapshot="09170000000",
            payment_instructions_snapshot="Use the request number.",
        )
        dilg_admin = User.objects.create_user(
            username="payment_dilg_admin",
            password="SecurePassword123!",
            role="DILG_ADMIN",
            is_staff=True,
        )
        self.client.force_authenticate(dilg_admin)

        response = self.client.get(
            reverse("document-request-detail", args=[document.pk])
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_resident_payment_uses_selected_recipient_and_snapshots_details(self):
        recipient = PaymentRecipient.objects.create(
            barangay=self.barangay,
            provider=PaymentRecipient.Provider.MAYA,
            display_name="Maya - Barangay Hall",
            recipient_name="Barangay Mabini Treasurer",
            recipient_identifier="09170000001",
            instructions="Use request number as reference.",
        )
        document = self.make_request()
        self.client.force_authenticate(self.resident)

        response = self.client.post(
            reverse("document-request-payment-reference", args=[document.pk]),
            {
                "payment_recipient_id": recipient.id,
                "payment_reference": " MAYA-REF-2048 ",
                "payment_transacted_at": timezone.now().isoformat(),
                "payment_proof_image": self._sample_image(),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        document.refresh_from_db()
        self.assertEqual(document.payment_method, DocumentRequest.PaymentMethod.MAYA)
        self.assertEqual(document.payment_recipient, recipient)
        self.assertEqual(document.payment_recipient_name_snapshot, "Barangay Mabini Treasurer")
        self.assertEqual(document.payment_recipient_identifier_snapshot, "09170000001")
        self.assertEqual(document.payment_reference, "MAYA-REF-2048")
        self.assertIsNotNone(document.payment_proof_image)
        self.assertIsNotNone(document.payment_transacted_at)

    def test_resident_cannot_submit_recipient_from_another_barangay(self):
        other_barangay = Barangay.objects.create(name="Other Recipient Tenant")
        recipient = PaymentRecipient.objects.create(
            barangay=other_barangay,
            provider=PaymentRecipient.Provider.GCASH,
            display_name="Other Barangay",
            recipient_name="Other Treasurer",
            recipient_identifier="09179999999",
        )
        document = self.make_request()
        self.client.force_authenticate(self.resident)

        response = self.client.post(
            reverse("document-request-payment-reference", args=[document.pk]),
            {
                "payment_recipient_id": recipient.id,
                "payment_reference": "REF-2048",
                "payment_transacted_at": timezone.now().isoformat(),
                "payment_proof_image": self._sample_image(),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        document.refresh_from_db()
        self.assertFalse(document.payment_reference)

    def test_official_can_manually_verify_maya_transfer(self):
        document = self.make_request(
            payment_method=DocumentRequest.PaymentMethod.MAYA,
            payment_reference="MAYA-REF-2048",
            payment_status=DocumentRequest.PaymentStatus.PENDING_VERIFICATION,
        )
        self.client.force_authenticate(self.official)

        response = self.client.patch(
            reverse("document-request-payment-review", args=[document.pk]),
            {"status": DocumentRequest.PaymentStatus.VERIFIED},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        document.refresh_from_db()
        self.assertEqual(document.payment_status, DocumentRequest.PaymentStatus.VERIFIED)

    def test_existing_official_receipts_backfill_as_verified_cash(self):
        paid_document = self.make_request(or_number="OR-LEGACY-100")
        unpaid_document = self.make_request(or_number="")
        migration = import_module(
            "gridy_services.migrations.0011_document_payment_review"
        )

        migration.initialize_existing_payment_status(
            apps,
            SimpleNamespace(connection=connection),
        )

        paid_document.refresh_from_db()
        unpaid_document.refresh_from_db()
        self.assertEqual(paid_document.payment_method, DocumentRequest.PaymentMethod.CASH)
        self.assertEqual(
            paid_document.payment_status,
            DocumentRequest.PaymentStatus.VERIFIED,
        )
        self.assertEqual(
            unpaid_document.payment_status,
            DocumentRequest.PaymentStatus.UNPAID,
        )

    def test_resident_can_submit_gcash_reference_for_own_ready_request(self):
        document = self.make_request()
        self.client.force_login(self.resident)

        response = self.client.post(
            reverse("document-request-payment-reference", args=[document.pk]),
            {
                "payment_recipient_id": self.gcash_recipient.id,
                "payment_reference": " GCASH-REF-2048 ",
                "payment_transacted_at": timezone.now().isoformat(),
                "payment_proof_image": self._sample_image(),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        document.refresh_from_db()
        self.assertEqual(document.payment_method, DocumentRequest.PaymentMethod.GCASH)
        self.assertEqual(document.payment_reference, "GCASH-REF-2048")
        self.assertEqual(
            document.payment_status,
            DocumentRequest.PaymentStatus.PENDING_VERIFICATION,
        )

    def test_resident_cannot_submit_gcash_reference_for_another_resident(self):
        document = self.make_request()
        other_resident = User.objects.create_user(
            username="other_payment_resident",
            password="SecurePassword123!",
            role=User.Role.RESIDENT,
            barangay=self.barangay,
        )
        self.client.force_login(other_resident)

        response = self.client.post(
            reverse("document-request-payment-reference", args=[document.pk]),
            {
                "payment_recipient_id": self.gcash_recipient.id,
                "payment_reference": "GCASH-REF-2048",
                "payment_transacted_at": timezone.now().isoformat(),
                "payment_proof_image": self._sample_image(),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        document.refresh_from_db()
        self.assertFalse(document.payment_reference)

    def test_gcash_reference_requires_a_ready_paid_request(self):
        document = self.make_request(status=DocumentRequest.Status.PROCESSING)
        self.client.force_login(self.resident)

        response = self.client.post(
            reverse("document-request-payment-reference", args=[document.pk]),
            {
                "payment_recipient_id": self.gcash_recipient.id,
                "payment_reference": "GCASH-REF-2048",
                "payment_transacted_at": timezone.now().isoformat(),
                "payment_proof_image": self._sample_image(),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_gcash_review_requires_a_reason_when_rejected(self):
        document = self.make_request(
            payment_method=DocumentRequest.PaymentMethod.GCASH,
            payment_reference="GCASH-REF-2048",
            payment_status=DocumentRequest.PaymentStatus.PENDING_VERIFICATION,
        )
        self.client.force_login(self.official)

        response = self.client.patch(
            reverse("document-request-payment-review", args=[document.pk]),
            {"status": DocumentRequest.PaymentStatus.REJECTED},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        document.refresh_from_db()
        self.assertEqual(
            document.payment_status,
            DocumentRequest.PaymentStatus.PENDING_VERIFICATION,
        )

    def test_official_can_verify_gcash_reference_and_audit_it(self):
        document = self.make_request(
            payment_method=DocumentRequest.PaymentMethod.GCASH,
            payment_reference="GCASH-REF-2048",
            payment_status=DocumentRequest.PaymentStatus.PENDING_VERIFICATION,
        )
        self.client.force_login(self.official)

        response = self.client.patch(
            reverse("document-request-payment-review", args=[document.pk]),
            {"status": DocumentRequest.PaymentStatus.VERIFIED},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        document.refresh_from_db()
        self.assertEqual(
            document.payment_status,
            DocumentRequest.PaymentStatus.VERIFIED,
        )
        self.assertTrue(
            AuditLog.objects.filter(
                action_by=self.official,
                action_type=AuditLog.ActionType.DOCUMENT_ACTION,
                description__icontains=f"#{document.pk}",
            ).exists()
        )

    def test_official_from_another_barangay_cannot_review_gcash_reference(self):
        document = self.make_request(
            payment_method=DocumentRequest.PaymentMethod.GCASH,
            payment_reference="GCASH-REF-2048",
            payment_status=DocumentRequest.PaymentStatus.PENDING_VERIFICATION,
        )
        other_barangay = Barangay.objects.create(name="Other Payment Barangay")
        other_official = User.objects.create_user(
            username="other_payment_official",
            password="SecurePassword123!",
            role=User.Role.ADMIN,
            barangay=other_barangay,
        )
        self.client.force_login(other_official)

        response = self.client.patch(
            reverse("document-request-payment-review", args=[document.pk]),
            {"status": DocumentRequest.PaymentStatus.VERIFIED},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        document.refresh_from_db()
        self.assertEqual(
            document.payment_status,
            DocumentRequest.PaymentStatus.PENDING_VERIFICATION,
        )

    def test_paid_document_cannot_be_released_before_payment_verification(self):
        document = self.make_request(
            payment_method=DocumentRequest.PaymentMethod.GCASH,
            payment_reference="GCASH-REF-2048",
            payment_status=DocumentRequest.PaymentStatus.PENDING_VERIFICATION,
        )
        self.client.force_login(self.official)

        response = self.client.patch(
            reverse("document-request-validate", args=[document.pk]),
            {
                "status": DocumentRequest.Status.RELEASED,
                "or_number": "OR-1001",
                "payment_method": DocumentRequest.PaymentMethod.GCASH,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        document.refresh_from_db()
        self.assertEqual(document.status, DocumentRequest.Status.READY_FOR_PICKUP)

    def test_cash_can_be_recorded_at_release_with_official_receipt(self):
        document = self.make_request()
        self.client.force_login(self.official)

        response = self.client.patch(
            reverse("document-request-validate", args=[document.pk]),
            {
                "status": DocumentRequest.Status.RELEASED,
                "or_number": "OR-1002",
                "payment_method": DocumentRequest.PaymentMethod.CASH,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        document.refresh_from_db()
        self.assertEqual(document.status, DocumentRequest.Status.RELEASED)
        self.assertEqual(
            document.payment_status,
            DocumentRequest.PaymentStatus.VERIFIED,
        )

    def test_exempt_document_release_does_not_require_payment(self):
        document = self.make_request(
            document_type="Certificate of Indigency",
            fee_amount="0.00",
            payment_status=DocumentRequest.PaymentStatus.NOT_REQUIRED,
        )
        self.client.force_login(self.official)

        response = self.client.patch(
            reverse("document-request-validate", args=[document.pk]),
            {"status": DocumentRequest.Status.RELEASED},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        document.refresh_from_db()
        self.assertEqual(
            document.payment_status,
            DocumentRequest.PaymentStatus.NOT_REQUIRED,
        )
