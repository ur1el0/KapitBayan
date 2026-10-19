import secrets

from django.contrib import admin
from django.test import RequestFactory, TestCase
from rest_framework.test import APIClient

from gridy_auth.admin import BarangayApplicationAdmin
from gridy_auth.models import Barangay, BarangayApplication, User


class BarangayOnboardingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
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
                "password": password,
                "password_confirm": password,
                "applicant_authorized": True,
                "contact_consent": True,
            },
            format="json",
        )

        self.assertEqual(creation.status_code, 201)
        application = BarangayApplication.objects.get(pk=creation.data["id"])
        applicant = application.applicant_user
        self.assertEqual(application.status, BarangayApplication.Status.PENDING)
        self.assertEqual(application.admin_username, "")
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
