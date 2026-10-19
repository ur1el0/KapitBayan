import secrets
import os
from datetime import timedelta
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib import admin
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase
from django.test.utils import override_settings
from rest_framework.test import APIClient
from rest_framework import status

from gridy_auth.admin import BarangayApplicationAdmin
from gridy_auth.models import Barangay, BarangayApplication, PrivateMediaCleanup, User
from gridy_auth.tokens import barangay_application_email_token_generator
from django.utils import timezone


VALID_PDF = b"%PDF-1.4\nKapitBayan authority proof fixture\n"


class BarangayOnboardingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.media_directory = TemporaryDirectory()
        self.addCleanup(self.media_directory.cleanup)
        self.media_override = override_settings(MEDIA_ROOT=self.media_directory.name)
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)
        self.barangay = Barangay.objects.create(
            name="Barangay Isabang",
            municipality="Tayabas City",
            province="Quezon",
        )

    def test_public_directory_remains_available_for_resident_registration(self):
        response = self.client.get("/api/v1/auth/public/barangays/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["id"], self.barangay.pk)

    def test_public_application_creates_only_a_pending_inactive_applicant_account(self):
        password = f"{secrets.token_urlsafe(24)}Aa1!"
        creation = self.client.post(
            "/api/v1/auth/public/barangay-applications/",
            {
                "name": "Barangay New",
                "municipality": "Tayabas City",
                "province": "Quezon",
                "applicant_name": "Applicant Example",
                "applicant_position": "Official",
                "applicant_email": "applicant@example.test",
                "applicant_phone": "09123456789",
                "proof_of_authority": SimpleUploadedFile(
                    "spoofed-name.png", VALID_PDF, content_type="image/png"
                ),
                "password": password,
                "password_confirm": password,
                "applicant_authorized": True,
                "contact_consent": True,
            },
            format="multipart",
        )

        self.assertEqual(creation.status_code, 201)
        application = BarangayApplication.objects.get(pk=creation.data["id"])
        applicant = application.applicant_user
        self.assertEqual(application.status, BarangayApplication.Status.PENDING)
        self.assertEqual(application.admin_username, "")
        self.assertTrue(application.proof_of_authority.name.startswith("barangay_onboarding/"))
        self.assertTrue(application.proof_of_authority.name.endswith(".pdf"))
        self.assertIsNone(application.email_verified_at)
        self.assertIsNotNone(application.email_verification_sent_at)
        self.assertEqual(applicant.role, User.Role.ADMIN)
        self.assertFalse(applicant.is_active)
        self.assertIsNone(applicant.barangay_id)
        self.assertNotEqual(applicant.password, password)
        self.assertTrue(applicant.check_password(password))
        self.assertEqual(Barangay.objects.count(), 1)

        login = self.client.post(
            "/api/v1/auth/login/",
            {"username": "applicant@example.test", "password": password},
            format="json",
        )
        self.assertEqual(login.status_code, 401)

    def test_invalid_signature_and_oversized_proof_are_rejected(self):
        password = f"{secrets.token_urlsafe(24)}Aa1!"
        payload = {
            "name": "Barangay Invalid Proof",
            "municipality": "Tayabas City",
            "province": "Quezon",
            "applicant_name": "Applicant Example",
            "applicant_position": "Official",
            "applicant_email": "invalid-proof@example.test",
            "applicant_phone": "09123456789",
            "proof_of_authority": SimpleUploadedFile("proof.pdf", b"not really pdf"),
            "password": password,
            "password_confirm": password,
            "applicant_authorized": True,
            "contact_consent": True,
        }

        invalid_signature = self.client.post(
            "/api/v1/auth/public/barangay-applications/", payload, format="multipart"
        )
        self.assertEqual(invalid_signature.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(BarangayApplication.objects.count(), 0)

        payload["proof_of_authority"] = SimpleUploadedFile(
            "proof.pdf", b"%PDF-1.4\n" + b"x" * (5 * 1024 * 1024)
        )
        oversized = self.client.post(
            "/api/v1/auth/public/barangay-applications/", payload, format="multipart"
        )
        self.assertEqual(oversized.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(BarangayApplication.objects.count(), 0)

    def test_submission_email_link_keeps_token_in_fragment(self):
        password = f"{secrets.token_urlsafe(24)}Aa1!"
        payload = {
            "name": "Barangay Email Link",
            "municipality": "Tayabas City",
            "province": "Quezon",
            "applicant_name": "Applicant Example",
            "applicant_position": "Barangay Official",
            "applicant_email": "email-link@example.test",
            "applicant_phone": "09123456789",
            "proof_of_authority": SimpleUploadedFile("proof.pdf", VALID_PDF),
            "password": password,
            "password_confirm": password,
            "applicant_authorized": True,
            "contact_consent": True,
        }
        with patch("gridy_auth.views.onboarding.send_barangay_application_verification_email.delay") as send_email:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(
                    "/api/v1/auth/public/barangay-applications/", payload, format="multipart"
                )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        link = send_email.call_args.args[3]
        self.assertIn("/verify-barangay-email?application=", link)
        self.assertIn("#token=", link)
        self.assertNotIn("token=", link.split("#", 1)[0])

    def create_application(self, email="applicant@example.test", name="Barangay New"):
        password = f"{secrets.token_urlsafe(24)}Aa1!"
        response = self.client.post(
            "/api/v1/auth/public/barangay-applications/",
            {
                "name": name,
                "municipality": "Tayabas City",
                "province": "Quezon",
                "applicant_name": "Applicant Example",
                "applicant_position": "Barangay Official",
                "applicant_email": email,
                "applicant_phone": "09123456789",
                "proof_of_authority": SimpleUploadedFile("proof.pdf", VALID_PDF),
                "password": password,
                "password_confirm": password,
                "applicant_authorized": True,
                "contact_consent": True,
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return BarangayApplication.objects.get(pk=response.data["id"])

    def test_verification_is_explicit_single_use_and_does_not_auto_activate_account(self):
        application = self.create_application()
        token = barangay_application_email_token_generator.make_token(application.applicant_user)
        verify_url = f"/api/v1/auth/public/barangay-applications/{application.pk}/verify-email/"

        get_response = self.client.get(verify_url, {"token": token})
        self.assertEqual(get_response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertIsNone(BarangayApplication.objects.get(pk=application.pk).email_verified_at)

        verified = self.client.post(verify_url, {"token": token}, format="json")
        self.assertEqual(verified.status_code, status.HTTP_200_OK)
        application.refresh_from_db()
        self.assertIsNotNone(application.email_verified_at)
        self.assertFalse(application.applicant_user.is_active)

        replay = self.client.post(verify_url, {"token": token}, format="json")
        self.assertEqual(replay.status_code, status.HTTP_400_BAD_REQUEST)

    def test_expired_verification_token_is_rejected(self):
        application = self.create_application(email="expired-link@example.test")
        token = barangay_application_email_token_generator.make_token(application.applicant_user)
        with override_settings(PASSWORD_RESET_TIMEOUT=-1):
            response = self.client.post(
                f"/api/v1/auth/public/barangay-applications/{application.pk}/verify-email/",
                {"token": token},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        application.refresh_from_db()
        self.assertIsNone(application.email_verified_at)

    def test_resend_is_generic_throttled_and_invalidates_previous_link(self):
        application = self.create_application()
        old_token = barangay_application_email_token_generator.make_token(application.applicant_user)
        application.email_verification_sent_at -= timedelta(minutes=11)
        application.save(update_fields=["email_verification_sent_at"])
        url = "/api/v1/auth/public/barangay-applications/resend-verification/"

        with patch("gridy_auth.views.onboarding.send_barangay_application_verification_email.delay") as send_email:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(
                    url,
                    {"application_id": application.pk, "applicant_email": application.applicant_email},
                    format="json",
                )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        send_email.assert_called_once()
        application.refresh_from_db()
        self.assertFalse(
            barangay_application_email_token_generator.check_token(application.applicant_user, old_token)
        )

        with patch("gridy_auth.views.onboarding.send_barangay_application_verification_email.delay") as send_email:
            with self.captureOnCommitCallbacks(execute=True):
                cooling_down = self.client.post(
                    url,
                    {"application_id": application.pk, "applicant_email": application.applicant_email},
                    format="json",
                )
        self.assertEqual(cooling_down.status_code, status.HTTP_202_ACCEPTED)
        send_email.assert_not_called()

        missing = self.client.post(
            url,
            {"application_id": 999999, "applicant_email": "missing@example.test"},
            format="json",
        )
        self.assertEqual(missing.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(missing.data, response.data)

    def test_reviewer_only_can_download_private_pending_proof(self):
        application = self.create_application()
        proof_path = application.proof_of_authority.path
        proof_url = f"/api/v1/auth/platform/barangay-applications/{application.pk}/proof/"
        public_media_response = self.client.get(f"/media/{application.proof_of_authority.name}")
        self.assertEqual(public_media_response.status_code, status.HTTP_404_NOT_FOUND)

        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get(proof_url).status_code, status.HTTP_401_UNAUTHORIZED)

        barangay_admin = User.objects.create_user(
            username="local_admin", password="test-password", role=User.Role.ADMIN,
            barangay=self.barangay,
        )
        self.client.force_authenticate(user=barangay_admin)
        self.assertEqual(self.client.get(proof_url).status_code, status.HTTP_403_FORBIDDEN)

        reviewer = User.objects.create_user(
            username="dilg_reviewer", password="test-password", role=User.Role.DILG_ADMIN,
            is_active=True,
        )
        self.client.force_authenticate(user=reviewer)
        response = self.client.get(proof_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertEqual(response["Cache-Control"], "private, no-store, max-age=0")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertEqual(b"".join(response.streaming_content), VALID_PDF)
        self.assertTrue(os.path.exists(proof_path))

    def test_approval_requires_verified_email_and_reviewed_proof_then_cleans_proof(self):
        application = self.create_application()
        reviewer = User.objects.create_user(
            username="dilg_reviewer", password="test-password", role=User.Role.DILG_ADMIN,
            is_active=True,
        )
        self.client.force_authenticate(user=reviewer)
        approve_url = f"/api/v1/auth/platform/barangay-applications/{application.pk}/approve/"

        unverified = self.client.post(
            approve_url, {"contact_verified": True, "proof_reviewed": True}, format="json"
        )
        self.assertEqual(unverified.status_code, status.HTTP_409_CONFLICT)
        self.assertFalse(application.applicant_user.is_active)

        application.email_verified_at = timezone.now()
        application.save(update_fields=["email_verified_at"])
        not_reviewed = self.client.post(
            approve_url, {"contact_verified": True, "proof_reviewed": False}, format="json"
        )
        self.assertEqual(not_reviewed.status_code, status.HTTP_400_BAD_REQUEST)

        file_path = application.proof_of_authority.path
        with self.captureOnCommitCallbacks(execute=True):
            approved = self.client.post(
                approve_url, {"contact_verified": True, "proof_reviewed": True}, format="json"
            )
        self.assertEqual(approved.status_code, status.HTTP_200_OK, approved.data)
        application.refresh_from_db()
        self.assertEqual(application.status, BarangayApplication.Status.APPROVED)
        self.assertTrue(application.proof_reviewed)
        self.assertFalse(application.proof_of_authority.name)
        self.assertTrue(application.applicant_user.is_active)
        self.assertFalse(os.path.exists(file_path))
        self.assertEqual(PrivateMediaCleanup.objects.count(), 0)

        self.assertEqual(self.client.get(
            f"/api/v1/auth/platform/barangay-applications/{application.pk}/proof/"
        ).status_code, status.HTTP_404_NOT_FOUND)

    def test_rejection_keeps_review_history_and_cleans_private_proof(self):
        application = self.create_application(email="reject@example.test")
        file_path = application.proof_of_authority.path
        reviewer = User.objects.create_user(
            username="dilg_reviewer", password="test-password", role=User.Role.DILG_ADMIN,
            is_active=True,
        )
        self.client.force_authenticate(user=reviewer)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                f"/api/v1/auth/platform/barangay-applications/{application.pk}/reject/",
                {"reason": "Authority document could not be verified."},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        application.refresh_from_db()
        self.assertEqual(application.status, BarangayApplication.Status.REJECTED)
        self.assertEqual(application.review_note, "Authority document could not be verified.")
        self.assertIsNotNone(application.reviewed_by_id)
        self.assertIsNone(application.applicant_user_id)
        self.assertFalse(application.proof_of_authority.name)
        self.assertFalse(os.path.exists(file_path))
        self.assertEqual(PrivateMediaCleanup.objects.count(), 0)

    def test_legacy_application_rows_are_preserved_and_read_only_to_superusers(self):
        application = BarangayApplication.objects.create(
            name=self.barangay.name,
            municipality=self.barangay.municipality,
            province=self.barangay.province,
            applicant_name="Historical Applicant",
            applicant_position="Barangay Official",
            applicant_email="historical@example.test",
            applicant_phone="09123456789",
            status=BarangayApplication.Status.PENDING,
        )
        ordinary_admin = User.objects.create_user(
            username="barangay_admin",
            password="test-password",
            role=User.Role.ADMIN,
            barangay=self.barangay,
            is_staff=True,
        )
        superuser = User.objects.create_superuser(
            username="platform_operator",
            email="operator@example.test",
            password="test-password",
        )
        model_admin = BarangayApplicationAdmin(BarangayApplication, admin.site)
        request_factory = RequestFactory()

        local_request = request_factory.get("/admin/gridy_auth/barangayapplication/")
        local_request.user = ordinary_admin
        operator_request = request_factory.get("/admin/gridy_auth/barangayapplication/")
        operator_request.user = superuser

        self.assertFalse(model_admin.has_view_permission(local_request))
        self.assertTrue(model_admin.has_view_permission(operator_request))
        self.assertFalse(model_admin.has_add_permission(operator_request))
        self.assertFalse(model_admin.has_change_permission(operator_request, application))
        self.assertFalse(model_admin.has_delete_permission(operator_request, application))

        application.refresh_from_db()
        self.assertEqual(application.status, BarangayApplication.Status.PENDING)
        self.assertIsNone(application.reviewed_by_id)
        self.assertEqual(BarangayApplication.objects.count(), 1)
