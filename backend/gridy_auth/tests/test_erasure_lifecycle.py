from decimal import Decimal
from io import BytesIO
from unittest.mock import patch

from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from rest_framework import status

from gridy_audit.models import AuditLog
from gridy_auth.models import Barangay, PrivateMediaCleanup, RefreshSession, Resident, User
from gridy_auth.lifecycle import erase_user_account
from gridy_services.models import AidRequest, DocumentRequest
from .base import IsolatedAuthAPITestCase


def create_dummy_image(name="dummy-id.png"):
    image_data = BytesIO()
    Image.new("RGB", (10, 10), color="white").save(image_data, format="PNG")
    return SimpleUploadedFile(name, image_data.getvalue(), content_type="image/png")


class AccountErasureLifecycleTests(IsolatedAuthAPITestCase):
    def setUp(self):
        self.barangay = Barangay.objects.create(name="Barangay Test Central")
        self.other_barangay = Barangay.objects.create(name="Other Barangay")

        # Admin user
        self.admin = User.objects.create_user(
            username="admin_user",
            email="admin@barangay.gov.ph",
            password="AdminPassword123!",
            role=User.Role.ADMIN,
            barangay=self.barangay,
        )

        # Resident user with profile
        self.resident_user = User.objects.create_user(
            username="resident_maria",
            email="maria@example.com",
            password="ResidentPassword123!",
            role=User.Role.RESIDENT,
            barangay=self.barangay,
        )
        self.resident = Resident.objects.create(
            user=self.resident_user,
            full_name="Maria Clara De Los Santos",
            birth_date="1995-03-12",
            is_verified=True,
            philsys_id_photo=create_dummy_image("maria-philsys.png"),
            utility_billing_photo=create_dummy_image("maria-billing.png"),
        )

        # Active RefreshSession
        self.session = RefreshSession.objects.create(
            user=self.resident_user,
            refresh_token_jti="session-token-jti-123",
            expires_at=timezone.now() + timezone.timedelta(days=7),
            is_revoked=False,
        )

        # Associated Document Requests (COA Treasury history)
        self.doc_req1 = DocumentRequest.objects.create(
            user=self.resident_user,
            barangay=self.barangay,
            document_type="BARANGAY_CLEARANCE",
            status=DocumentRequest.Status.RELEASED,
            fee_amount=Decimal("150.00"),
            or_number="OR-2026-9999",
            purpose="Employment",
        )
        self.doc_req2 = DocumentRequest.objects.create(
            user=self.resident_user,
            barangay=self.barangay,
            document_type="CERTIFICATE_OF_INDIGENCY",
            status=DocumentRequest.Status.PENDING,
            fee_amount=Decimal("0.00"),
            purpose="Medical Aid",
        )

        # Associated Aid Request
        self.aid_req = AidRequest.objects.create(
            requester=self.resident_user,
            barangay=self.barangay,
            assistance_type="FOOD_ASSISTANCE",
            reason="Emergency Relief",
            status=AidRequest.Status.APPROVED,
        )

    def test_right_to_erasure_preserves_documents_aid_and_cleans_files(self):
        self.client.force_authenticate(user=self.resident_user)
        philsys_file_name = self.resident.philsys_id_photo.name
        billing_file_name = self.resident.utility_billing_photo.name

        self.assertTrue(default_storage.exists(philsys_file_name))
        self.assertTrue(default_storage.exists(billing_file_name))

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(reverse("auth_me"))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # User and profile are destroyed
        self.assertFalse(User.objects.filter(username="resident_maria").exists())
        self.assertFalse(Resident.objects.filter(id=self.resident.id).exists())

        # Storage files are cleaned
        self.assertFalse(default_storage.exists(philsys_file_name))
        self.assertFalse(default_storage.exists(billing_file_name))

        # Document requests are preserved with O.R. and fee history intact
        self.doc_req1.refresh_from_db()
        self.assertIsNone(self.doc_req1.user)
        self.assertEqual(self.doc_req1.walkin_name, "Maria Clara De Los Santos")
        self.assertEqual(self.doc_req1.or_number, "OR-2026-9999")
        self.assertEqual(self.doc_req1.fee_amount, Decimal("150.00"))
        self.assertEqual(self.doc_req1.status, DocumentRequest.Status.RELEASED)

        self.doc_req2.refresh_from_db()
        self.assertIsNone(self.doc_req2.user)
        self.assertEqual(self.doc_req2.walkin_name, "Maria Clara De Los Santos")

        # Aid request is preserved
        self.aid_req.refresh_from_db()
        self.assertIsNone(self.aid_req.requester)
        self.assertEqual(self.aid_req.assistance_type, "FOOD_ASSISTANCE")
        self.assertEqual(self.aid_req.status, AidRequest.Status.APPROVED)

        # Audit log records the erasure
        self.assertTrue(
            AuditLog.objects.filter(
                description__icontains="Right to Erasure"
            ).exists()
        )

    def test_official_resident_deletion_preserves_records_and_cleans_files(self):
        self.client.force_authenticate(user=self.admin)
        philsys_file_name = self.resident.philsys_id_photo.name
        self.assertTrue(default_storage.exists(philsys_file_name))

        url = reverse("resident-detail", kwargs={"pk": self.resident.id})
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertFalse(User.objects.filter(username="resident_maria").exists())
        self.assertFalse(Resident.objects.filter(id=self.resident.id).exists())
        self.assertFalse(default_storage.exists(philsys_file_name))

        self.doc_req1.refresh_from_db()
        self.assertIsNone(self.doc_req1.user)
        self.assertEqual(self.doc_req1.or_number, "OR-2026-9999")
        self.assertEqual(self.doc_req1.walkin_name, "Maria Clara De Los Santos")

    def test_official_rejection_of_pending_resident_cleans_files_and_logs(self):
        self.client.force_authenticate(user=self.admin)
        pending_user = User.objects.create_user(
            username="pending_pedro",
            email="pedro@example.com",
            password="PedroPass123!",
            role=User.Role.RESIDENT,
            barangay=self.barangay,
        )
        pending_resident = Resident.objects.create(
            user=pending_user,
            full_name="Pedro Penduko",
            birth_date="2000-01-01",
            is_verified=False,
            philsys_id_photo=create_dummy_image("pedro-id.png"),
        )
        pedro_file = pending_resident.philsys_id_photo.name
        self.assertTrue(default_storage.exists(pedro_file))

        url = reverse("reject_resident", kwargs={"pk": pending_resident.id})
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(url, {"rejection_reason": "Blurry ID photo"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertFalse(User.objects.filter(username="pending_pedro").exists())
        self.assertFalse(Resident.objects.filter(id=pending_resident.id).exists())
        self.assertFalse(default_storage.exists(pedro_file))

        self.assertTrue(
            AuditLog.objects.filter(
                description__icontains="Rejected pending resident account for Pedro Penduko"
            ).exists()
        )

    def test_identity_files_are_deleted_only_after_commit(self):
        self.client.force_authenticate(user=self.resident_user)
        philsys_file_name = self.resident.philsys_id_photo.name
        billing_file_name = self.resident.utility_billing_photo.name

        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            response = self.client.delete(reverse("auth_me"))
            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            self.assertTrue(default_storage.exists(philsys_file_name))
            self.assertTrue(default_storage.exists(billing_file_name))

        self.assertEqual(len(callbacks), 2)
        for callback in callbacks:
            callback()

        self.assertFalse(default_storage.exists(philsys_file_name))
        self.assertFalse(default_storage.exists(billing_file_name))

    def test_profile_picture_cleanup_failure_keeps_retry_without_failing_erasure(self):
        self.resident_user.profile_picture = create_dummy_image("maria-profile.png")
        self.resident_user.save(update_fields=["profile_picture"])
        account_id = self.resident_user.pk
        self.client.force_authenticate(user=self.resident_user)

        with patch.object(default_storage, "exists", side_effect=OSError("storage unavailable")):
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.delete(reverse("auth_me"))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(User.objects.filter(pk=account_id).exists())
        self.assertTrue(PrivateMediaCleanup.objects.filter(
            storage_model="gridy_auth.User",
            field_name="profile_picture",
            attempt_count=1,
        ).exists())

    def test_database_rollback_preserves_identity_files_and_account(self):
        resident_user_id = self.resident_user.pk
        resident_id = self.resident.pk
        philsys_file_name = self.resident.philsys_id_photo.name
        billing_file_name = self.resident.utility_billing_photo.name

        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            with self.assertRaisesRegex(RuntimeError, "force erasure rollback"):
                with transaction.atomic():
                    erase_user_account(
                        self.resident_user,
                        "Test account erasure rollback.",
                        actor=self.resident_user,
                    )
                    raise RuntimeError("force erasure rollback")

        self.assertEqual(callbacks, [])
        self.assertTrue(User.objects.filter(pk=resident_user_id).exists())
        self.assertTrue(Resident.objects.filter(pk=resident_id).exists())
        self.assertTrue(default_storage.exists(philsys_file_name))
        self.assertTrue(default_storage.exists(billing_file_name))
