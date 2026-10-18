
from unittest.mock import patch

from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from gridy_auth.models import Barangay, User
from gridy_audit.models import AuditLog
from .models import IssueReport

# Create your tests here.

class IssueReportAPITests(APITestCase):
    def setUp(self):
        # Create a test resident user
        self.user = User.objects.create_user(
            username="test_resident",
            password="SecurePassword123!",
            email="resident@example.com",
            role=User.Role.RESIDENT
        )
        self.client.force_login(self.user)
        self.url = reverse('issue-report-list')

    def test_report_creation_default_urgency(self):
        # Create a report without providing the urgency key
        payload = {
            "title": "Flooded street",
            "description": "Purok 1 is flooded",
            "location": "Purok 1"
        }
        response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(IssueReport.objects.get(title="Flooded street").urgency, IssueReport.Urgency.MINOR)    

    def test_report_creation_ignores_client_urgency(self):
        # Create a report with EMERGENCY urgency
        payload = {
            "title": "Fallen power line",
            "description": "Live wire exposed",
            "location": "Purok 3",
            "urgency": "EMERGENCY"
        }
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(IssueReport.objects.get(title="Fallen power line").urgency, IssueReport.Urgency.MINOR)

    def test_report_creation_invalid_urgency(self):
        # Try to post with an invalid urgency choice
        payload = {
            "title": "test",
            "description": "test",
            "location": "test",
            "urgency": "CRITICAL" # invalid choice
        }
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_official_cannot_create_issue_report(self):
        # Officials triage and resolve reports; only citizens submit resident community issues
        official = User.objects.create_user(
            username="captain_test",
            password="SecurePassword123!",
            email="captain@example.com",
            role=User.Role.ADMIN
        )
        self.client.force_login(official)
        payload = {
            "title": "Broken pipe",
            "description": "Leaking water",
            "location": "Purok 4"
        }
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_field_official_can_update_urgency_and_audit_change(self):
        barangay = Barangay.objects.create(name="Triage Test Barangay")
        resident = User.objects.create_user(
            username="triage_reporter",
            password=None,
            role=User.Role.RESIDENT,
            barangay=barangay,
        )
        official = User.objects.create_user(
            username="triage_field_official",
            password=None,
            role=User.Role.FIELD_OFFICIAL,
            barangay=barangay,
        )
        report = IssueReport.objects.create(
            reporter=resident,
            title="Exposed electrical wire",
            description="A live wire is hanging near homes.",
            location="Purok 3",
            urgency=IssueReport.Urgency.MINOR,
        )

        self.client.force_login(official)
        response = self.client.patch(
            reverse('issue-report-detail', args=[report.id]),
            {"urgency": IssueReport.Urgency.EMERGENCY},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        report.refresh_from_db()
        self.assertEqual(report.urgency, IssueReport.Urgency.EMERGENCY)
        audit_log = AuditLog.objects.get(
            action_type=AuditLog.ActionType.REPORT_ACTION,
            action_by=official,
            description__icontains="urgency",
        )
        self.assertIn(IssueReport.Urgency.MINOR, audit_log.description)
        self.assertIn(IssueReport.Urgency.EMERGENCY, audit_log.description)

    @patch('gridy_reports.signals.send_notification_to_user_task.delay')
    def test_status_change_schedules_one_notification_after_commit(self, notify):
        barangay = Barangay.objects.create(name="Report Update Barangay")
        resident = User.objects.create_user(
            username="report_update_resident",
            password=None,
            role=User.Role.RESIDENT,
            barangay=barangay,
        )
        official = User.objects.create_user(
            username="report_update_official",
            password=None,
            role=User.Role.ADMIN,
            barangay=barangay,
        )
        report = IssueReport.objects.create(
            reporter=resident,
            title="Blocked sidewalk",
            description="Construction materials block the sidewalk.",
            location="Purok 2",
        )
        self.client.force_login(official)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.patch(
                reverse('issue-report-detail', args=[report.id]),
                {"status": IssueReport.Status.IN_PROGRESS},
                format='json',
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notify.assert_called_once_with(
            user_id=resident.id,
            title="Issue Report Update",
            body="Your issue report 'Blocked sidewalk' has been marked as In Progress.",
            data={"type": "issue", "report_id": str(report.id)},
        )

    def test_resident_cannot_update_report_urgency(self):
        report = IssueReport.objects.create(
            reporter=self.user,
            title="Street accident",
            description="A collision was reported.",
            location="Purok 2",
        )

        response = self.client.patch(
            reverse('issue-report-detail', args=[report.id]),
            {"urgency": IssueReport.Urgency.EMERGENCY},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        report.refresh_from_db()
        self.assertEqual(report.urgency, IssueReport.Urgency.MINOR)

    def test_field_official_cannot_update_another_barangays_report(self):
        reporter_barangay = Barangay.objects.create(name="Report Owner Barangay")
        official_barangay = Barangay.objects.create(name="Official Assigned Barangay")
        reporter = User.objects.create_user(
            username="other_barangay_reporter",
            password=None,
            role=User.Role.RESIDENT,
            barangay=reporter_barangay,
        )
        official = User.objects.create_user(
            username="other_barangay_field_official",
            password=None,
            role=User.Role.FIELD_OFFICIAL,
            barangay=official_barangay,
        )
        report = IssueReport.objects.create(
            reporter=reporter,
            title="Neighborhood hazard",
            description="A hazard was reported in another barangay.",
            location="Purok 5",
        )

        self.client.force_login(official)
        response = self.client.patch(
            reverse('issue-report-detail', args=[report.id]),
            {"urgency": IssueReport.Urgency.EMERGENCY},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        report.refresh_from_db()
        self.assertEqual(report.urgency, IssueReport.Urgency.MINOR)

    def test_official_can_delete_issue_report_with_audit_log(self):
        official = User.objects.create_user(
            username="captain_delete_test",
            password="SecurePassword123!",
            email="captain_del@example.com",
            role=User.Role.ADMIN
        )
        report = IssueReport.objects.create(
            reporter=self.user,
            title="Spam Report",
            description="Fake text",
            location="Purok 1"
        )
        self.client.force_login(official)
        detail_url = reverse('issue-report-detail', args=[report.id])
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(IssueReport.objects.filter(id=report.id).exists())
        self.assertTrue(
            AuditLog.objects.filter(
                action_type=AuditLog.ActionType.REPORT_ACTION,
                action_by=official
            ).exists()
        )

    def test_resident_cannot_delete_issue_report(self):
        report = IssueReport.objects.create(
            reporter=self.user,
            title="Pothole",
            description="Big pothole",
            location="Purok 2"
        )
        detail_url = reverse('issue-report-detail', args=[report.id])
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(IssueReport.objects.filter(id=report.id).exists())
