from rest_framework import status

from gridy_auth.models import Barangay
from gridy_reports.models import IssueReport
from gridy_services.models import DocumentRequest, QueueTicket
from .base import ServiceAPIBaseTestCase


class DashboardSummaryAPITests(ServiceAPIBaseTestCase):
    def test_empty_dashboard_uses_real_zero_counts_instead_of_sample_values(self):
        empty_barangay = Barangay.objects.create(name="Empty Analytics Test Barangay")
        self.official.barangay = empty_barangay
        self.official.save(update_fields=["barangay"])
        self.client.force_login(self.official)

        response = self.client.get("/api/v1/dashboard/summary/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_residents"], 0)
        self.assertEqual(response.data["demographics"]["purok_distribution"], {})
        self.assertEqual(
            response.data["demographics"]["age_demographics"],
            {"youth": 0, "young_adult": 0, "adult": 0, "senior": 0},
        )
        self.assertEqual(
            response.data["issue_reports"]["category_breakdown"],
            {
                "peace_and_order": 0,
                "public_health": 0,
                "infrastructure": 0,
                "environment": 0,
                "other": 0,
            },
        )

    def test_dashboard_summary_required_auth(self):
        url = "/api/v1/dashboard/summary/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_dashboard_summary_blocked_for_residents(self):
        self.client.force_login(self.resident)
        url = "/api/v1/dashboard/summary/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_dashboard_summary_success_for_official(self):
        barangay = Barangay.objects.create(name="Dashboard Assigned Barangay")
        self.official.barangay = barangay
        self.official.save(update_fields=["barangay"])
        self.resident.barangay = barangay
        self.resident.save(update_fields=["barangay"])
        self.client.force_login(self.official)

        # Create some mock data to verify aggregation counters
        DocumentRequest.objects.create(
            user=self.resident,
            barangay=barangay,
            document_type="Indigency Certificate",
            status="PENDING"
        )
        IssueReport.objects.create(
            reporter=self.resident,
            barangay=barangay,
            title="Broken Light",
            description="Dark alley",
            location="Purok 2",
            urgency="HAZARD"
        )
        QueueTicket.objects.create(
            barangay=barangay,
            status="SERVING",
            ticket_number="T001",
            service_type="DOCUMENT"
        )

        url = "/api/v1/dashboard/summary/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify JSON structure contains expected keys and data values
        self.assertIn("document_requests", response.data)
        self.assertIn("issue_reports", response.data)
        self.assertIn("queue_activity", response.data)

        # Verify values
        self.assertEqual(response.data["document_requests"]["pending"], 1)
        self.assertEqual(response.data["issue_reports"]["urgency_breakdown"]["hazard"], 1)
        self.assertEqual(response.data["queue_activity"]["serving_now"], "T001")

    def test_dashboard_summary_rejects_unassigned_official(self):
        self.client.force_login(self.official)
        response = self.client.get("/api/v1/dashboard/summary/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_dashboard_summary_isolates_transferred_resident_records_and_includes_walkin_issues(self):
        from gridy_auth.models import User

        barangay_a = Barangay.objects.create(name="Transfer Source Barangay")
        barangay_b = Barangay.objects.create(name="Transfer Destination Barangay")
        admin_b = User.objects.create_user(
            username="admin_b_dashboard",
            email="admin-b@example.com",
            password="SecurePassword123!",
            role=User.Role.ADMIN,
            barangay=barangay_b,
        )

        # Resident already transferred from Barangay A to Barangay B.
        self.resident.barangay = barangay_b
        self.resident.save(update_fields=["barangay"])

        DocumentRequest.objects.create(
            user=self.resident,
            barangay=barangay_a,
            document_type="Barangay Clearance",
            status=DocumentRequest.Status.RELEASED,
            fee_amount="999.00",
        )
        IssueReport.objects.create(
            reporter=self.resident,
            barangay=barangay_a,
            title="Old Barangay A Leak",
            description="Reported before transfer",
            location="Purok 1",
            urgency=IssueReport.Urgency.MINOR,
        )

        DocumentRequest.objects.create(
            user=self.resident,
            barangay=barangay_b,
            document_type="Barangay Clearance",
            status=DocumentRequest.Status.RELEASED,
            fee_amount="50.00",
        )
        IssueReport.objects.create(
            reporter=None,
            barangay=barangay_b,
            walkin_name="Kiosk Reporter",
            title="Streetlight Outage",
            description="Logged at Barangay B kiosk",
            location="Purok 3",
            status=IssueReport.Status.PENDING,
            urgency=IssueReport.Urgency.HAZARD,
        )

        self.client.force_login(admin_b)
        response = self.client.get("/api/v1/dashboard/summary/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["document_requests"]["released"], 1)
        self.assertEqual(response.data["document_requests"]["total_revenue"], 50.0)
        self.assertEqual(response.data["issue_reports"]["total"], 1)
        self.assertEqual(response.data["issue_reports"]["urgency_breakdown"]["hazard"], 1)
