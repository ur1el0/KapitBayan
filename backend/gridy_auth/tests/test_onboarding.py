from unittest.mock import patch

from django.urls import reverse
from rest_framework import status

from gridy_auth.models import Barangay, BarangayApplication, User
from .base import IsolatedAuthAPITestCase


class BarangayOnboardingAPITests(IsolatedAuthAPITestCase):
    def setUp(self):
        self.barangay = Barangay.objects.create(
            name="Barangay Ibabang Dupay",
            municipality="Lucena City",
            province="Quezon",
        )
        self.dilg_admin = User.objects.create_user(
            username="dilg_onboarding_admin",
            email="dilg-onboarding@example.com",
            password="SecurePassword123!",
            role=User.Role.DILG_ADMIN,
            is_staff=True,
        )

    def test_public_official_account_request_is_reviewed_before_account_creation(self):
        payload = {
            "application_type": "OFFICIAL",
            "barangay_id": self.barangay.pk,
            "applicant_name": "Juan Dela Cruz",
            "applicant_position": "Barangay Secretary",
            "applicant_email": "juan.official@example.com",
            "applicant_phone": "09171234567",
        }
        response = self.client.post(reverse("barangay-application-list"), payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        application = BarangayApplication.objects.get(pk=response.data["id"])
        self.assertEqual(application.application_type, BarangayApplication.ApplicationType.OFFICIAL)
        self.assertEqual(application.existing_barangay, self.barangay)
        self.assertFalse(User.objects.filter(email=payload["applicant_email"]).exists())

    @patch("gridy_auth.views.onboarding.send_barangay_approval_email.delay")
    def test_dilg_approval_provisions_official_in_existing_barangay(self, send_email):
        payload = {
            "application_type": "OFFICIAL",
            "barangay_id": self.barangay.pk,
            "applicant_name": "Juan Dela Cruz",
            "applicant_position": "Barangay Secretary",
            "applicant_email": "juan.official@example.com",
            "applicant_phone": "09171234567",
        }
        created = self.client.post(reverse("barangay-application-list"), payload, format="json")
        self.client.force_authenticate(self.dilg_admin)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("barangay-application-review", args=[created.data["id"]]),
                {"status": BarangayApplication.Status.APPROVED},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Barangay.objects.count(), 1)
        official = User.objects.get(email=payload["applicant_email"])
        self.assertEqual(official.role, User.Role.ADMIN)
        self.assertEqual(official.barangay, self.barangay)
        self.assertFalse(official.has_usable_password())
        send_email.assert_called_once()

    def test_public_onboarding_application_is_rejected(self):
        # Direct attempt to submit a barangay onboarding application is rejected
        onboarding_payload = {
            "application_type": "BARANGAY",
            "name": "Barangay New Locality",
            "municipality": "Lucena City",
            "province": "Quezon",
            "applicant_name": "Maria Santos",
            "applicant_position": "Barangay Captain",
            "applicant_email": "maria.captain@example.com",
            "applicant_phone": "09170000000",
        }
        response = self.client.post(
            reverse("barangay-application-list"), onboarding_payload, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(BarangayApplication.objects.filter(name="Barangay New Locality").exists())
        self.assertFalse(Barangay.objects.filter(name="Barangay New Locality").exists())

    def test_submission_without_existing_barangay_is_rejected(self):
        payload = {
            "application_type": "OFFICIAL",
            "applicant_name": "Maria Santos",
            "applicant_position": "Barangay Secretary",
            "applicant_email": "maria.santos@example.com",
            "applicant_phone": "09171234567",
        }
        response = self.client.post(reverse("barangay-application-list"), payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("barangay_id", response.data)

    def test_historical_onboarding_application_cannot_be_reviewed_or_create_barangay(self):
        # Even if a historical BARANGAY application exists in DB, it cannot be approved or create a tenant
        historical_app = BarangayApplication.objects.create(
            application_type=BarangayApplication.ApplicationType.BARANGAY,
            name="Barangay Historical",
            municipality="Lucena City",
            province="Quezon",
            applicant_name="Old Applicant",
            applicant_position="Applicant",
            applicant_email="old.applicant@example.com",
            applicant_phone="09170000001",
            status=BarangayApplication.Status.PENDING,
        )
        self.client.force_authenticate(self.dilg_admin)

        response = self.client.post(
            reverse("barangay-application-review", args=[historical_app.pk]),
            {"status": BarangayApplication.Status.APPROVED},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(Barangay.objects.filter(name="Barangay Historical").exists())
        self.assertFalse(User.objects.filter(email="old.applicant@example.com").exists())

    def test_dilg_application_list_excludes_onboarding_applications(self):
        BarangayApplication.objects.create(
            application_type=BarangayApplication.ApplicationType.BARANGAY,
            name="Barangay Historical",
            municipality="Lucena City",
            province="Quezon",
            applicant_name="Old Applicant",
            applicant_position="Applicant",
            applicant_email="old.applicant@example.com",
            applicant_phone="09170000001",
            status=BarangayApplication.Status.PENDING,
        )
        official_app = BarangayApplication.objects.create(
            application_type=BarangayApplication.ApplicationType.OFFICIAL,
            existing_barangay=self.barangay,
            name=self.barangay.name,
            municipality=self.barangay.municipality,
            province=self.barangay.province,
            applicant_name="Official Applicant",
            applicant_position="Barangay Secretary",
            applicant_email="official.applicant@example.com",
            applicant_phone="09170000002",
            status=BarangayApplication.Status.PENDING,
        )

        self.client.force_authenticate(self.dilg_admin)
        response = self.client.get(reverse("barangay-application-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data if isinstance(response.data, list) else response.data.get("results", [])
        ids = [item["id"] for item in results]
        self.assertIn(official_app.pk, ids)
        self.assertEqual(len(results), 1)

    def test_only_dilg_admin_can_review_applications(self):
        application = BarangayApplication.objects.create(
            application_type=BarangayApplication.ApplicationType.OFFICIAL,
            existing_barangay=self.barangay,
            name=self.barangay.name,
            municipality=self.barangay.municipality,
            province=self.barangay.province,
            applicant_name="Juan Dela Cruz",
            applicant_position="Barangay Secretary",
            applicant_email="juan.official@example.com",
            applicant_phone="09171234567",
        )
        self.client.force_authenticate(
            User.objects.create_user(
                username="unrelated_resident",
                password="SecurePassword123!",
                role=User.Role.RESIDENT,
            )
        )

        response = self.client.post(
            reverse("barangay-application-review", args=[application.pk]),
            {"status": BarangayApplication.Status.APPROVED},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(application.status, BarangayApplication.Status.PENDING)

    def test_dilg_review_of_unknown_application_returns_not_found(self):
        self.client.force_authenticate(self.dilg_admin)

        response = self.client.post(
            reverse("barangay-application-review", args=[999999]),
            {"status": BarangayApplication.Status.APPROVED},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_application_rejection_requires_reason(self):
        application = BarangayApplication.objects.create(
            application_type=BarangayApplication.ApplicationType.OFFICIAL,
            existing_barangay=self.barangay,
            name=self.barangay.name,
            municipality=self.barangay.municipality,
            province=self.barangay.province,
            applicant_name="Juan Dela Cruz",
            applicant_position="Barangay Secretary",
            applicant_email="juan.official@example.com",
            applicant_phone="09171234567",
        )
        self.client.force_authenticate(self.dilg_admin)
        review_url = reverse(
            "barangay-application-review", args=[application.pk]
        )

        missing_reason = self.client.post(
            review_url,
            {"status": BarangayApplication.Status.REJECTED},
            format="json",
        )
        rejected = self.client.post(
            review_url,
            {
                "status": BarangayApplication.Status.REJECTED,
                "review_note": "Could not independently verify the applicant.",
            },
            format="json",
        )

        self.assertEqual(missing_reason.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(rejected.status_code, status.HTTP_200_OK)
        self.assertEqual(rejected.data["status"], BarangayApplication.Status.REJECTED)
        self.assertFalse(User.objects.filter(email=application.applicant_email).exists())

    def test_public_barangay_directory_contains_locality_but_no_private_application_data(self):
        BarangayApplication.objects.create(
            application_type=BarangayApplication.ApplicationType.OFFICIAL,
            existing_barangay=self.barangay,
            name=self.barangay.name,
            municipality=self.barangay.municipality,
            province=self.barangay.province,
            applicant_name="Juan Dela Cruz",
            applicant_position="Barangay Secretary",
            applicant_email="juan.official@example.com",
            applicant_phone="09171234567",
        )

        response = self.client.get(reverse("public-barangay-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["id"], self.barangay.id)
        self.assertEqual(response.data[0]["municipality"], "Lucena City")
        self.assertNotIn("applicant_email", response.data[0])
        self.assertEqual(len(response.data), 1)
