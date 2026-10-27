import datetime
from io import BytesIO
import tempfile
from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import DatabaseError, transaction
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from gridy_audit.models import AuditLog
from gridy_auth.models import Barangay, Resident, User
from gridy_services.models import DocumentRequest, PaymentRecipient
from gridy_services.serializers.documents import DocumentRequestReviewSerializer


class PaymentProofStorageAndEndpointTests(APITestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.barangay = Barangay.objects.create(name="Barangay Proof Central")
        self.other_barangay = Barangay.objects.create(name="Barangay Foreign")

        # Owner resident
        self.resident = User.objects.create_user(
            username="proof_owner",
            password="SecurePassword123!",
            email="owner@test.ph",
            role=User.Role.RESIDENT,
            barangay=self.barangay,
        )
        Resident.objects.create(
            user=self.resident,
            full_name="Owner Resident",
            birth_date="1990-01-01",
            is_verified=True,
        )

        # Other resident
        self.other_resident = User.objects.create_user(
            username="other_resident",
            password="SecurePassword123!",
            email="other@test.ph",
            role=User.Role.RESIDENT,
            barangay=self.barangay,
        )

        # Staff users
        self.admin = User.objects.create_user(
            username="barangay_admin",
            password="SecurePassword123!",
            email="admin@test.ph",
            role=User.Role.ADMIN,
            barangay=self.barangay,
        )
        self.field_official = User.objects.create_user(
            username="barangay_tanod",
            password="SecurePassword123!",
            email="tanod@test.ph",
            role=User.Role.FIELD_OFFICIAL,
            barangay=self.barangay,
        )
        self.foreign_admin = User.objects.create_user(
            username="foreign_admin",
            password="SecurePassword123!",
            email="foreign_admin@test.ph",
            role=User.Role.ADMIN,
            barangay=self.other_barangay,
        )
        self.foreign_field_official = User.objects.create_user(
            username="foreign_tanod",
            password="SecurePassword123!",
            email="foreign_tanod@test.ph",
            role=User.Role.FIELD_OFFICIAL,
            barangay=self.other_barangay,
        )
        self.unassigned_official = User.objects.create_user(
            username="unassigned_official",
            password="SecurePassword123!",
            email="unassigned@test.ph",
            role=User.Role.FIELD_OFFICIAL,
            barangay=None,
        )
        self.barangay_operator = User.objects.create_user(
            username="barangay_operator",
            password="SecurePassword123!",
            email="operator@test.ph",
            role="BARANGAY_OPERATOR",
        )

        # Generate sample image bytes
        image_buffer = BytesIO()
        Image.new("RGB", (20, 20), color="blue").save(image_buffer, format="PNG")
        self.sample_image_bytes = image_buffer.getvalue()

        # Create a ready document request with proof image
        self.document = DocumentRequest.objects.create(
            user=self.resident,
            barangay=self.barangay,
            document_type="Barangay Clearance",
            status=DocumentRequest.Status.READY_FOR_PICKUP,
            fee_amount=50.00,
            fee_assessment_status=DocumentRequest.FeeAssessmentStatus.ASSESSED,
            payment_method=DocumentRequest.PaymentMethod.GCASH,
            payment_status=DocumentRequest.PaymentStatus.PENDING_VERIFICATION,
            payment_reference="GCASH-123456",
            payment_proof_image=SimpleUploadedFile(
                "receipt.png", self.sample_image_bytes, content_type="image/png"
            ),
        )

    def tearDown(self):
        # Cleanup any generated files
        if self.document.payment_proof_image:
            self.document.payment_proof_image.delete(save=False)

    def test_cloudinary_storage_protects_payment_proofs_directory(self):
        with patch.dict(
            "os.environ",
            {
                "CLOUDINARY_CLOUD_NAME": "test_cloud",
                "CLOUDINARY_API_KEY": "test_key",
                "CLOUDINARY_API_SECRET": "test_secret",
            },
        ):
            with patch.object(
                settings,
                "CLOUDINARY_STORAGE",
                {
                    "CLOUD_NAME": "test_cloud",
                    "API_KEY": "test_key",
                    "API_SECRET": "test_secret",
                },
                create=True,
            ):
                from config.private_media_storage import ResidentAwareCloudinaryStorage
                self.assertTrue(
                    ResidentAwareCloudinaryStorage.is_private_resident_media("payment_proofs/receipt-1.png")
                )
                storage = ResidentAwareCloudinaryStorage()
                with self.assertRaisesMessage(
                    ImproperlyConfigured,
                    "Private evidence must be served through an authorized media endpoint.",
                ):
                    storage.url("payment_proofs/receipt-1.png")

    def test_direct_media_view_denies_payment_proofs_access(self):
        response = self.client.get(f"/media/{self.document.payment_proof_image.name}")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_request_to_proof_endpoint_returns_401(self):
        # Canonical route
        res1 = self.client.get(f"/api/v1/document-requests/{self.document.id}/payment-proof/")
        self.assertEqual(res1.status_code, status.HTTP_401_UNAUTHORIZED)

        # Alias route
        res2 = self.client.get(f"/api/v1/documents/{self.document.id}/payment-proof/")
        self.assertEqual(res2.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_owner_resident_can_stream_proof_image_with_security_headers(self):
        self.client.force_authenticate(user=self.resident)

        # Canonical route
        canonical_resp = self.client.get(
            f"/api/v1/document-requests/{self.document.id}/payment-proof/"
        )
        self.assertEqual(canonical_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(canonical_resp["Cache-Control"], "private, no-store, max-age=0")
        self.assertEqual(canonical_resp["X-Content-Type-Options"], "nosniff")
        self.assertIn("image/", canonical_resp["Content-Type"])

        # Alias route
        alias_resp = self.client.get(f"/api/v1/documents/{self.document.id}/payment-proof/")
        self.assertEqual(alias_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(alias_resp["Cache-Control"], "private, no-store, max-age=0")
        self.assertEqual(alias_resp["X-Content-Type-Options"], "nosniff")

    def test_same_barangay_admin_and_field_official_can_stream_proof(self):
        for staff_user in [self.admin, self.field_official]:
            self.client.force_authenticate(user=staff_user)
            resp = self.client.get(f"/api/v1/document-requests/{self.document.id}/payment-proof/")
            self.assertEqual(
                resp.status_code,
                status.HTTP_200_OK,
                f"Failed for role {staff_user.role}",
            )
            self.assertEqual(resp["Cache-Control"], "private, no-store, max-age=0")

    def test_unauthorized_users_receive_404(self):
        unauthorized_users = [
            self.other_resident,
            self.foreign_admin,
            self.foreign_field_official,
            self.unassigned_official,
            self.barangay_operator,
        ]
        for user in unauthorized_users:
            self.client.force_authenticate(user=user)
            resp = self.client.get(f"/api/v1/document-requests/{self.document.id}/payment-proof/")
            self.assertEqual(
                resp.status_code,
                status.HTTP_404_NOT_FOUND,
                f"User {user.username} ({user.role}) should receive 404",
            )
            alias_resp = self.client.get(f"/api/v1/documents/{self.document.id}/payment-proof/")
            self.assertEqual(
                alias_resp.status_code,
                status.HTTP_404_NOT_FOUND,
                f"User {user.username} ({user.role}) should receive 404 on alias",
            )

    def test_unassigned_staff_cannot_read_or_validate_walkin_from_another_barangay(self):
        walkin = DocumentRequest.objects.create(
            user=None,
            barangay=self.other_barangay,
            is_walkin=True,
            walkin_name="Walk-in Resident",
            document_type="Barangay Clearance",
            status=DocumentRequest.Status.READY_FOR_PICKUP,
            fee_amount=50,
            or_number="",
        )
        unassigned_admin = User.objects.create_user(
            username="unassigned_admin",
            password="SecurePassword123!",
            email="unassigned_admin@test.ph",
            role=User.Role.ADMIN,
            barangay=None,
        )

        for staff_user in (self.unassigned_official, unassigned_admin):
            self.client.force_authenticate(user=staff_user)
            detail_url = reverse("document-request-detail", args=[walkin.pk])
            validate_url = reverse("document-request-validate", args=[walkin.pk])
            self.assertEqual(self.client.get(detail_url).status_code, status.HTTP_404_NOT_FOUND)
            self.assertEqual(
                self.client.patch(validate_url, {"or_number": "CROSS-TENANT-OR"}, format="json").status_code,
                status.HTTP_404_NOT_FOUND,
            )

        walkin.refresh_from_db()
        self.assertEqual(walkin.or_number, "")

    def test_document_barangay_controls_staff_scope_with_legacy_null_fallback(self):
        self.document.barangay = self.other_barangay
        self.document.save(update_fields=["barangay"])
        detail_url = reverse("document-request-detail", args=[self.document.pk])
        validate_url = reverse("document-request-validate", args=[self.document.pk])

        for staff_user in (self.admin, self.field_official):
            self.client.force_authenticate(user=staff_user)
            self.assertEqual(self.client.get(detail_url).status_code, status.HTTP_404_NOT_FOUND)
            self.assertEqual(
                self.client.patch(validate_url, {"or_number": "WRONG-TENANT"}, format="json").status_code,
                status.HTTP_404_NOT_FOUND,
            )
        for staff_user in (self.foreign_admin, self.foreign_field_official):
            self.client.force_authenticate(user=staff_user)
            self.assertEqual(self.client.get(detail_url).status_code, status.HTTP_200_OK)

        self.document.barangay = None
        self.document.save(update_fields=["barangay"])
        for staff_user in (self.admin, self.field_official):
            self.client.force_authenticate(user=staff_user)
            self.assertEqual(self.client.get(detail_url).status_code, status.HTTP_200_OK)
        for staff_user in (self.foreign_admin, self.foreign_field_official):
            self.client.force_authenticate(user=staff_user)
            self.assertEqual(self.client.get(detail_url).status_code, status.HTTP_404_NOT_FOUND)

        self.document.is_walkin = True
        self.document.save(update_fields=["is_walkin"])
        self.client.force_authenticate(user=self.admin)
        self.assertEqual(self.client.get(detail_url).status_code, status.HTTP_404_NOT_FOUND)

    def test_missing_proof_returns_404_to_owner_and_staff(self):
        doc_without_proof = DocumentRequest.objects.create(
            user=self.resident,
            barangay=self.barangay,
            document_type="Barangay Clearance",
            status=DocumentRequest.Status.READY_FOR_PICKUP,
            fee_amount=50.00,
        )
        self.client.force_authenticate(user=self.resident)
        res1 = self.client.get(f"/api/v1/document-requests/{doc_without_proof.id}/payment-proof/")
        self.assertEqual(res1.status_code, status.HTTP_404_NOT_FOUND)

        self.client.force_authenticate(user=self.admin)
        res2 = self.client.get(f"/api/v1/document-requests/{doc_without_proof.id}/payment-proof/")
        self.assertEqual(res2.status_code, status.HTTP_404_NOT_FOUND)

    def test_transaction_safe_deletion_cleanup(self):
        storage = self.document.payment_proof_image.storage
        file_name = self.document.payment_proof_image.name
        self.assertTrue(storage.exists(file_name))

        # Test rollback preserves file
        try:
            with transaction.atomic():
                doc_to_delete = DocumentRequest.objects.get(pk=self.document.pk)
                doc_to_delete.delete()
                raise RuntimeError("Simulated transaction rollback")
        except RuntimeError:
            pass

        # File must still exist after rollback
        self.assertTrue(
            storage.exists(file_name),
            "Storage file should not be deleted on rolled-back transaction",
        )

        # Committed delete cleans up file
        with self.captureOnCommitCallbacks(execute=True):
            doc_to_delete = DocumentRequest.objects.get(pk=self.document.pk)
            doc_to_delete.delete()

        self.assertFalse(
            storage.exists(file_name),
            "Storage file must be deleted after committed document deletion",
        )


class PaymentSubmissionAndReviewWorkflowTests(APITestCase):
    def setUp(self):
        self.barangay = Barangay.objects.create(name="Barangay Submission Central")
        self.other_barangay = Barangay.objects.create(name="Barangay Foreign Sub")

        self.resident = User.objects.create_user(
            username="submitter_resident",
            password="SecurePassword123!",
            email="submitter@test.ph",
            role=User.Role.RESIDENT,
            barangay=self.barangay,
        )
        Resident.objects.create(
            user=self.resident,
            full_name="Submitter Resident",
            birth_date="1995-05-05",
            is_verified=True,
        )

        self.admin = User.objects.create_user(
            username="sub_admin",
            password="SecurePassword123!",
            email="sub_admin@test.ph",
            role=User.Role.ADMIN,
            barangay=self.barangay,
        )
        self.field_official = User.objects.create_user(
            username="sub_field",
            password="SecurePassword123!",
            email="sub_field@test.ph",
            role=User.Role.FIELD_OFFICIAL,
            barangay=self.barangay,
        )
        self.foreign_field_official = User.objects.create_user(
            username="foreign_sub_field",
            password="SecurePassword123!",
            email="foreign_field@test.ph",
            role=User.Role.FIELD_OFFICIAL,
            barangay=self.other_barangay,
        )

        self.recipient = PaymentRecipient.objects.create(
            barangay=self.barangay,
            provider=PaymentRecipient.Provider.GCASH,
            display_name="GCash - Barangay Hall",
            recipient_name="Official Treasurer",
            recipient_identifier="09181234567",
            instructions="Send exact amount with request ID.",
        )

    def _sample_image(self, format="PNG", size=(50, 50), color="green", name="proof.png"):
        buf = BytesIO()
        Image.new("RGB", size, color=color).save(buf, format=format)
        return SimpleUploadedFile(
            name,
            buf.getvalue(),
            content_type=f"image/{format.lower()}",
        )

    def _make_ready_request(self, **kwargs):
        values = {
            "user": self.resident,
            "barangay": self.barangay,
            "document_type": "Barangay Clearance",
            "purpose": "Employment",
            "status": DocumentRequest.Status.READY_FOR_PICKUP,
            "fee_amount": 75.00,
            "fee_assessment_status": DocumentRequest.FeeAssessmentStatus.ASSESSED,
            "payment_status": DocumentRequest.PaymentStatus.UNPAID,
        }
        values.update(kwargs)
        return DocumentRequest.objects.create(**values)

    def choose_payment_method(self, document, *, recipient=None):
        payload = (
            {"payment_recipient_id": recipient.pk}
            if recipient
            else {"payment_method": DocumentRequest.PaymentMethod.CASH}
        )
        return self.client.post(
            reverse("document-request-payment-choice", args=[document.pk]),
            payload,
            format="json",
        )

    def test_positive_multipart_submission_saves_details_and_snapshots(self):
        document = self._make_ready_request()
        self.client.force_login(self.resident)
        choice_response = self.choose_payment_method(document, recipient=self.recipient)
        self.assertEqual(choice_response.status_code, status.HTTP_200_OK, choice_response.data)
        transacted_at = timezone.now() - datetime.timedelta(minutes=2)

        response = self.client.post(
            reverse("document-request-payment-reference", args=[document.pk]),
            {
                "payment_recipient_id": self.recipient.id,
                "payment_reference": "GCASH-SUCCESS-101",
                "payment_transacted_at": transacted_at.isoformat(),
                "payment_proof_image": self._sample_image(),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        document.refresh_from_db()
        self.assertEqual(document.payment_method, DocumentRequest.PaymentMethod.GCASH)
        self.assertEqual(document.payment_reference, "GCASH-SUCCESS-101")
        self.assertEqual(
            document.payment_status,
            DocumentRequest.PaymentStatus.PENDING_VERIFICATION,
        )
        self.assertEqual(document.payment_recipient, self.recipient)
        self.assertEqual(
            document.payment_recipient_name_snapshot,
            self.recipient.recipient_name,
        )
        self.assertEqual(
            document.payment_recipient_identifier_snapshot,
            self.recipient.recipient_identifier,
        )
        self.assertEqual(
            document.payment_instructions_snapshot,
            self.recipient.instructions,
        )
        self.assertTrue(bool(document.payment_proof_image))
        self.assertEqual(
            response.data["payment_proof_url"],
            f"/api/v1/document-requests/{document.pk}/payment-proof/",
        )

    def test_upload_extension_and_streamed_mime_follow_verified_image_format(self):
        document = self._make_ready_request()
        self.client.force_login(self.resident)
        choice_response = self.choose_payment_method(document, recipient=self.recipient)
        self.assertEqual(choice_response.status_code, status.HTTP_200_OK, choice_response.data)

        response = self.client.post(
            reverse("document-request-payment-reference", args=[document.pk]),
            {
                "payment_recipient_id": self.recipient.id,
                "payment_reference": "GCASH-MIME-101",
                "payment_transacted_at": timezone.now().isoformat(),
                "payment_proof_image": self._sample_image(name="receipt.jpg"),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        document.refresh_from_db()
        self.assertTrue(document.payment_proof_image.name.endswith(".png"))

        proof_response = self.client.get(
            f"/api/v1/document-requests/{document.pk}/payment-proof/"
        )
        self.assertEqual(proof_response.status_code, status.HTTP_200_OK)
        self.assertEqual(proof_response["Content-Type"], "image/png")
        self.assertEqual(proof_response["X-Content-Type-Options"], "nosniff")

    def test_validation_errors_for_missing_fields(self):
        document = self._make_ready_request()
        self.client.force_login(self.resident)

        # Missing payment_proof_image
        res1 = self.client.post(
            reverse("document-request-payment-reference", args=[document.pk]),
            {
                "payment_recipient_id": self.recipient.id,
                "payment_reference": "GCASH-123",
                "payment_transacted_at": timezone.now().isoformat(),
            },
            format="multipart",
        )
        self.assertEqual(res1.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("payment_proof_image", res1.data)

        # Missing payment_reference
        res2 = self.client.post(
            reverse("document-request-payment-reference", args=[document.pk]),
            {
                "payment_recipient_id": self.recipient.id,
                "payment_transacted_at": timezone.now().isoformat(),
                "payment_proof_image": self._sample_image(),
            },
            format="multipart",
        )
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("payment_reference", res2.data)

        # Missing payment_transacted_at
        res3 = self.client.post(
            reverse("document-request-payment-reference", args=[document.pk]),
            {
                "payment_recipient_id": self.recipient.id,
                "payment_reference": "GCASH-123",
                "payment_proof_image": self._sample_image(),
            },
            format="multipart",
        )
        self.assertEqual(res3.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("payment_transacted_at", res3.data)

    def test_future_timestamp_beyond_five_minutes_rejected(self):
        document = self._make_ready_request()
        self.client.force_login(self.resident)
        future_time = timezone.now() + datetime.timedelta(minutes=10)

        response = self.client.post(
            reverse("document-request-payment-reference", args=[document.pk]),
            {
                "payment_recipient_id": self.recipient.id,
                "payment_reference": "GCASH-123",
                "payment_transacted_at": future_time.isoformat(),
                "payment_proof_image": self._sample_image(),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("payment_transacted_at", response.data)

    def test_invalid_or_corrupt_image_rejected(self):
        document = self._make_ready_request()
        self.client.force_login(self.resident)

        # Plain text disguised as PNG
        fake_file = SimpleUploadedFile(
            "not_an_image.png",
            b"This is just plain text content, not an image.",
            content_type="image/png",
        )
        response = self.client.post(
            reverse("document-request-payment-reference", args=[document.pk]),
            {
                "payment_recipient_id": self.recipient.id,
                "payment_reference": "GCASH-123",
                "payment_transacted_at": timezone.now().isoformat(),
                "payment_proof_image": fake_file,
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("payment_proof_image", response.data)

        # GIF format (not supported)
        gif_buf = BytesIO()
        Image.new("RGB", (20, 20)).save(gif_buf, format="GIF")
        gif_file = SimpleUploadedFile(
            "test.gif", gif_buf.getvalue(), content_type="image/gif"
        )
        res_gif = self.client.post(
            reverse("document-request-payment-reference", args=[document.pk]),
            {
                "payment_recipient_id": self.recipient.id,
                "payment_reference": "GCASH-123",
                "payment_transacted_at": timezone.now().isoformat(),
                "payment_proof_image": gif_file,
            },
            format="multipart",
        )
        self.assertEqual(res_gif.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("payment_proof_image", res_gif.data)

    def test_oversized_image_rejected(self):
        document = self._make_ready_request()
        self.client.force_login(self.resident)

        # File > 5MB
        oversized = SimpleUploadedFile(
            "big.png",
            b"0" * (5 * 1024 * 1024 + 1024),
            content_type="image/png",
        )
        response = self.client.post(
            reverse("document-request-payment-reference", args=[document.pk]),
            {
                "payment_recipient_id": self.recipient.id,
                "payment_reference": "GCASH-123",
                "payment_transacted_at": timezone.now().isoformat(),
                "payment_proof_image": oversized,
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("payment_proof_image", response.data)

    def test_readiness_barrier_blocks_submission_in_processing_or_pending(self):
        self.client.force_login(self.resident)
        for st in [DocumentRequest.Status.PENDING, DocumentRequest.Status.PROCESSING]:
            doc = self._make_ready_request(status=st)
            resp = self.client.post(
                reverse("document-request-payment-reference", args=[doc.pk]),
                {
                    "payment_recipient_id": self.recipient.id,
                    "payment_reference": "GCASH-123",
                    "payment_transacted_at": timezone.now().isoformat(),
                    "payment_proof_image": self._sample_image(),
                },
                format="multipart",
            )
            self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_submission_blocked_when_pending_or_verified(self):
        self.client.force_login(self.resident)
        for ps in [
            DocumentRequest.PaymentStatus.PENDING_VERIFICATION,
            DocumentRequest.PaymentStatus.VERIFIED,
        ]:
            doc = self._make_ready_request(payment_status=ps)
            resp = self.client.post(
                reverse("document-request-payment-reference", args=[doc.pk]),
                {
                    "payment_recipient_id": self.recipient.id,
                    "payment_reference": "GCASH-123",
                    "payment_transacted_at": timezone.now().isoformat(),
                    "payment_proof_image": self._sample_image(),
                },
                format="multipart",
            )
            self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_resubmission_replaces_proof_and_cleans_up_old_file_on_commit(self):
        document = self._make_ready_request(
            payment_status=DocumentRequest.PaymentStatus.REJECTED,
            payment_method=DocumentRequest.PaymentMethod.GCASH,
            payment_recipient=self.recipient,
            payment_proof_image=self._sample_image(name="old_proof.png"),
        )
        old_file_name = document.payment_proof_image.name
        storage = document.payment_proof_image.storage
        self.assertTrue(storage.exists(old_file_name))

        self.client.force_login(self.resident)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("document-request-payment-reference", args=[document.pk]),
                {
                    "payment_recipient_id": self.recipient.id,
                    "payment_reference": "GCASH-RETRY-456",
                    "payment_transacted_at": timezone.now().isoformat(),
                    "payment_proof_image": self._sample_image(color="yellow", name="new_proof.png"),
                },
                format="multipart",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        document.refresh_from_db()
        self.assertFalse(
            storage.exists(old_file_name),
            "Old proof file must be deleted on commit when superseded",
        )
        self.assertTrue(
            storage.exists(document.payment_proof_image.name),
            "New proof file must exist in storage",
        )

    def test_database_save_failure_cleans_new_proof_and_preserves_existing_proof(self):
        document = self._make_ready_request(
            payment_status=DocumentRequest.PaymentStatus.REJECTED,
            payment_method=DocumentRequest.PaymentMethod.GCASH,
            payment_recipient=self.recipient,
            payment_proof_image=self._sample_image(name="old_receipt.png"),
        )
        old_name = document.payment_proof_image.name
        storage = document.payment_proof_image.storage
        self.assertTrue(storage.exists(old_name))
        self.client.force_login(self.resident)

        with patch.object(
            DocumentRequest,
            "save",
            side_effect=DatabaseError("simulated document save failure"),
        ):
            with self.assertRaises(DatabaseError):
                self.client.post(
                    reverse("document-request-payment-reference", args=[document.pk]),
                    {
                        "payment_recipient_id": self.recipient.id,
                        "payment_reference": "GCASH-DB-FAIL-102",
                        "payment_transacted_at": timezone.now().isoformat(),
                        "payment_proof_image": self._sample_image(
                            name="new_receipt.png"
                        ),
                    },
                    format="multipart",
                )

        document.refresh_from_db()
        self.assertEqual(document.payment_proof_image.name, old_name)
        self.assertTrue(storage.exists(old_name))
        self.assertFalse(storage.exists("payment_proofs/new_receipt.png"))

    def test_resident_can_switch_rejected_payment_to_cash_and_cleans_up_proof(self):
        document = self._make_ready_request(
            payment_proof_image=self._sample_image(name="cash_cleared.png"),
            payment_method=DocumentRequest.PaymentMethod.GCASH,
            payment_recipient=self.recipient,
            payment_status=DocumentRequest.PaymentStatus.REJECTED,
        )
        file_name = document.payment_proof_image.name
        storage = document.payment_proof_image.storage
        self.assertTrue(storage.exists(file_name))

        self.client.force_login(self.resident)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("document-request-payment-choice", args=[document.pk]),
                {"payment_method": DocumentRequest.PaymentMethod.CASH},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        document.refresh_from_db()
        self.assertEqual(document.payment_method, DocumentRequest.PaymentMethod.CASH)
        self.assertIsNone(document.payment_recipient)
        self.assertFalse(bool(document.payment_proof_image))
        self.assertIsNone(document.payment_transacted_at)
        self.assertFalse(storage.exists(file_name))

    def test_converting_to_fee_exempt_cleans_up_proof_on_commit(self):
        document = self._make_ready_request(
            payment_proof_image=self._sample_image(name="exempt_cleared.png"),
            payment_status=DocumentRequest.PaymentStatus.PENDING_VERIFICATION,
        )
        file_name = document.payment_proof_image.name
        storage = document.payment_proof_image.storage
        self.assertTrue(storage.exists(file_name))

        self.client.force_login(self.admin)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.patch(
                reverse("document-request-validate", args=[document.pk]),
                {
                    "fee_amount": 0,
                    "fee_waiver_reason": "Resident qualified for fee waiver",
                },
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        document.refresh_from_db()
        self.assertFalse(bool(document.payment_proof_image))
        self.assertEqual(
            document.payment_status, DocumentRequest.PaymentStatus.NOT_REQUIRED
        )
        self.assertFalse(storage.exists(file_name))

    def test_field_official_can_verify_payment_and_record_or_number(self):
        document = self._make_ready_request(
            payment_method=DocumentRequest.PaymentMethod.GCASH,
            payment_reference="GCASH-VERIFY-1",
            payment_status=DocumentRequest.PaymentStatus.PENDING_VERIFICATION,
        )
        self.client.force_login(self.field_official)

        response = self.client.patch(
            reverse("document-request-payment-review", args=[document.pk]),
            {
                "status": DocumentRequest.PaymentStatus.VERIFIED,
                "or_number": "OR-2026-0099",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        document.refresh_from_db()
        self.assertEqual(document.payment_status, DocumentRequest.PaymentStatus.VERIFIED)
        self.assertEqual(document.or_number, "OR-2026-0099")
        self.assertEqual(document.status, DocumentRequest.Status.READY_FOR_PICKUP)
        self.assertTrue(
            AuditLog.objects.filter(
                action_by=self.field_official,
                action_type=AuditLog.ActionType.DOCUMENT_ACTION,
                description__icontains=f"#{document.pk}",
            ).exists()
        )

    def test_field_official_rejection_requires_reason(self):
        document = self._make_ready_request(
            payment_method=DocumentRequest.PaymentMethod.GCASH,
            payment_reference="GCASH-REJECT-1",
            payment_status=DocumentRequest.PaymentStatus.PENDING_VERIFICATION,
        )
        self.client.force_login(self.field_official)

        # Rejected without note -> 400
        res1 = self.client.patch(
            reverse("document-request-payment-review", args=[document.pk]),
            {"status": DocumentRequest.PaymentStatus.REJECTED},
            format="json",
        )
        self.assertEqual(res1.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("note", res1.data)

        # Rejected with note -> 200
        res2 = self.client.patch(
            reverse("document-request-payment-review", args=[document.pk]),
            {
                "status": DocumentRequest.PaymentStatus.REJECTED,
                "note": "Reference number not found in barangay GCash statement.",
            },
            format="json",
        )
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        document.refresh_from_db()
        self.assertEqual(document.payment_status, DocumentRequest.PaymentStatus.REJECTED)
        self.assertEqual(
            document.payment_review_note,
            "Reference number not found in barangay GCash statement.",
        )

    def test_cross_barangay_field_official_cannot_review_payment(self):
        document = self._make_ready_request(
            payment_method=DocumentRequest.PaymentMethod.GCASH,
            payment_reference="GCASH-CROSS-1",
            payment_status=DocumentRequest.PaymentStatus.PENDING_VERIFICATION,
        )
        self.client.force_login(self.foreign_field_official)

        response = self.client.patch(
            reverse("document-request-payment-review", args=[document.pk]),
            {"status": DocumentRequest.PaymentStatus.VERIFIED},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_or_persistence_decoupled_from_release_in_validate(self):
        document = self._make_ready_request()
        self.client.force_login(self.admin)

        response = self.client.patch(
            reverse("document-request-validate", args=[document.pk]),
            {"or_number": "OR-EARLY-SAVE-123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        document.refresh_from_db()
        self.assertEqual(document.or_number, "OR-EARLY-SAVE-123")
        self.assertEqual(document.status, DocumentRequest.Status.READY_FOR_PICKUP)

    @patch("gridy_services.views.documents.send_notification_to_user_task.delay")
    def test_saving_only_or_number_does_not_send_duplicate_status_notification(
        self, send_notification
    ):
        document = self._make_ready_request()
        self.client.force_login(self.admin)

        response = self.client.patch(
            reverse("document-request-validate", args=[document.pk]),
            {"or_number": "OR-ONLY-SAVE-1"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        send_notification.assert_not_called()

    def test_admin_can_save_or_number_without_resubmitting_workflow_fields(self):
        document = self._make_ready_request()
        self.client.force_login(self.admin)

        response = self.client.patch(
            reverse("document-request-or-number", args=[document.pk]),
            {"or_number": "OR-2026-0099"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        document.refresh_from_db()
        self.assertEqual(document.or_number, "OR-2026-0099")
        self.assertEqual(document.status, DocumentRequest.Status.READY_FOR_PICKUP)
        self.assertEqual(response.data["or_number"], "OR-2026-0099")

    def test_resident_cannot_save_an_official_receipt_number(self):
        document = self._make_ready_request()
        self.client.force_login(self.resident)

        response = self.client.patch(
            reverse("document-request-or-number", args=[document.pk]),
            {"or_number": "OR-2026-0099"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        document.refresh_from_db()
        self.assertFalse(document.or_number)

    def test_field_official_can_find_document_by_exact_or_or_tracking_id(self):
        document = self._make_ready_request(or_number="OR-2026-0099")
        self.client.force_login(self.field_official)

        receipt_response = self.client.get(
            reverse("document-request-verify"),
            {"identifier": "OR-2026-0099"},
        )
        tracking_response = self.client.get(
            reverse("document-request-verify"),
            {
                "identifier": (
                    f"ID: #BC-{document.created_at.year}-"
                    f"{document.pk:04d}"
                )
            },
        )

        self.assertEqual(receipt_response.status_code, status.HTTP_200_OK)
        self.assertEqual(receipt_response.data["id"], document.pk)
        self.assertEqual(receipt_response.data["or_number"], "OR-2026-0099")
        self.assertEqual(tracking_response.status_code, status.HTTP_200_OK)
        self.assertEqual(tracking_response.data["id"], document.pk)

    def test_field_official_receipt_lookup_is_limited_to_their_barangay(self):
        foreign_document = DocumentRequest.objects.create(
            barangay=self.other_barangay,
            is_walkin=True,
            walkin_name="Foreign Resident",
            document_type="Barangay Clearance",
            status=DocumentRequest.Status.READY_FOR_PICKUP,
            or_number="OR-FOREIGN-2026-1",
        )
        self.client.force_login(self.field_official)

        response = self.client.get(
            reverse("document-request-verify"),
            {"identifier": foreign_document.or_number},
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_receipt_digits_are_not_misread_as_a_tracking_id(self):
        self.client.force_login(self.field_official)

        response = self.client.get(
            reverse("document-request-verify"),
            {"identifier": "OR-2026-0099"},
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_model_and_serializer_require_receipt_for_paid_release(self):
        document = self._make_ready_request(
            fee_amount=75,
            status=DocumentRequest.Status.RELEASED,
            or_number=" ",
        )

        with self.assertRaises(ValidationError) as model_error:
            document.full_clean()
        self.assertIn("or_number", model_error.exception.message_dict)

        serializer = DocumentRequestReviewSerializer(
            document,
            data={"status": DocumentRequest.Status.RELEASED},
            partial=True,
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("or_number", serializer.errors)

        exempt = self._make_ready_request(
            document_type="Certificate of Indigency",
            fee_amount=0,
            status=DocumentRequest.Status.READY_FOR_PICKUP,
            or_number="",
        )
        exempt_serializer = DocumentRequestReviewSerializer(
            exempt,
            data={"status": DocumentRequest.Status.RELEASED},
            partial=True,
        )
        self.assertTrue(exempt_serializer.is_valid(), exempt_serializer.errors)

    def test_release_gate_enforces_or_number_on_paid_document(self):
        self.client.force_login(self.admin)

        # 1. Paid document without O.R. cannot be released
        paid_unverified = self._make_ready_request(
            payment_method=DocumentRequest.PaymentMethod.CASH,
            or_number="",
        )
        res1 = self.client.patch(
            reverse("document-request-validate", args=[paid_unverified.pk]),
            {"status": DocumentRequest.Status.RELEASED},
            format="json",
        )
        self.assertEqual(res1.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("or_number", res1.data)

        # 2. Paid document with O.R. can be released
        res2 = self.client.patch(
            reverse("document-request-validate", args=[paid_unverified.pk]),
            {
                "status": DocumentRequest.Status.RELEASED,
                "or_number": "OR-FINAL-999",
                "payment_method": DocumentRequest.PaymentMethod.CASH,
            },
            format="json",
        )
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        paid_unverified.refresh_from_db()
        self.assertEqual(paid_unverified.status, DocumentRequest.Status.RELEASED)
        self.assertEqual(paid_unverified.or_number, "OR-FINAL-999")

        # 3. Fee-exempt document (fee = 0) can be released without O.R.
        exempt_doc = self._make_ready_request(
            document_type="Certificate of Indigency",
            fee_amount=0,
            payment_status=DocumentRequest.PaymentStatus.NOT_REQUIRED,
            or_number="",
        )
        res3 = self.client.patch(
            reverse("document-request-validate", args=[exempt_doc.pk]),
            {"status": DocumentRequest.Status.RELEASED},
            format="json",
        )
        self.assertEqual(res3.status_code, status.HTTP_200_OK)
        exempt_doc.refresh_from_db()
        self.assertEqual(exempt_doc.status, DocumentRequest.Status.RELEASED)
