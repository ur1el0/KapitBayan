
from unittest.mock import patch

from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from gridy_auth.models import Barangay, Resident, User
from gridy_audit.models import AuditLog
from .models import IssueReport

# Create your tests here.

class IssueReportAPITests(APITestCase):
    def setUp(self):
        self.barangay = Barangay.objects.create(name="Report Fixture Barangay")
        # Create a verified resident user
        self.user = User.objects.create_user(
            username="test_resident",
            password="SecurePassword123!",
            email="resident@example.com",
            role=User.Role.RESIDENT,
            barangay=self.barangay,
        )
        self.resident_profile = Resident.objects.create(
            user=self.user,
            full_name="Test Resident",
            birth_date="1995-05-15",
            is_verified=True,
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

    def test_report_creation_respects_client_urgency(self):
        # Create a report with EMERGENCY urgency
        payload = {
            "title": "Fallen power line",
            "description": "Live wire exposed",
            "location": "Purok 3",
            "urgency": "EMERGENCY"
        }
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(IssueReport.objects.get(title="Fallen power line").urgency, IssueReport.Urgency.EMERGENCY)

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
        barangay = Barangay.objects.create(name="Report Delete Test Barangay")
        self.user.barangay = barangay
        self.user.save(update_fields=["barangay"])
        official = User.objects.create_user(
            username="captain_delete_test",
            password="SecurePassword123!",
            email="captain_del@example.com",
            role=User.Role.ADMIN,
            barangay=barangay,
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

    def test_resident_reports_paginate_first_5_recent_and_support_filters(self):
        from datetime import timedelta
        from django.utils import timezone

        base_time = timezone.now() - timedelta(hours=10)
        reports = []
        for idx in range(7):
            r = IssueReport.objects.create(
                reporter=self.user,
                title=f"Report #{idx + 1}",
                description=f"Details for report {idx + 1}",
                location=f"Purok {idx + 1}",
                category=(
                    IssueReport.Category.INFRASTRUCTURE
                    if idx % 2 == 0
                    else IssueReport.Category.ENVIRONMENT
                ),
                status=(
                    IssueReport.Status.RESOLVED
                    if idx >= 5
                    else IssueReport.Status.PENDING
                ),
            )
            IssueReport.objects.filter(pk=r.pk).update(created_at=base_time + timedelta(minutes=idx * 10))
            reports.append(r)

        page1 = self.client.get(self.url, {"page": 1, "page_size": 5})
        self.assertEqual(page1.status_code, status.HTTP_200_OK)
        self.assertEqual(page1.data["count"], 7)
        self.assertIsNotNone(page1.data["next"])
        self.assertEqual(
            [item["title"] for item in page1.data["results"]],
            ["Report #7", "Report #6", "Report #5", "Report #4", "Report #3"],
        )

        page2 = self.client.get(self.url, {"page": 2, "page_size": 5})
        self.assertEqual(page2.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item["title"] for item in page2.data["results"]],
            ["Report #2", "Report #1"],
        )

        filtered = self.client.get(
            self.url,
            {
                "status": IssueReport.Status.RESOLVED,
                "category": IssueReport.Category.INFRASTRUCTURE,
                "page_size": 5,
            },
        )
        self.assertEqual(filtered.status_code, status.HTTP_200_OK)
        self.assertEqual(filtered.data["count"], 1)
        self.assertEqual(filtered.data["results"][0]["title"], "Report #7")

        searched = self.client.get(self.url, {"search": "Report #2", "page_size": 5})
        self.assertEqual(searched.status_code, status.HTTP_200_OK)
        self.assertEqual(searched.data["count"], 1)
        self.assertEqual(searched.data["results"][0]["title"], "Report #2")

    def test_field_official_cannot_delete_issue_report(self):
        field_official = User.objects.create_user(
            username="tanod_cannot_delete_report",
            password="SecurePassword123!",
            role=User.Role.FIELD_OFFICIAL,
            barangay=self.barangay,
        )
        report = IssueReport.objects.create(
            reporter=self.user,
            barangay=self.barangay,
            title="Active Emergency",
            description="Downed line",
            location="Purok 1",
            urgency=IssueReport.Urgency.EMERGENCY,
        )
        self.client.force_login(field_official)
        response = self.client.delete(reverse("issue-report-detail", args=[report.id]))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(IssueReport.objects.filter(pk=report.pk).exists())

    def test_unverified_or_unassigned_resident_cannot_submit_issue_report(self):
        unassigned_user = User.objects.create_user(
            username="unassigned_report_resident",
            password="SecurePassword123!",
            role=User.Role.RESIDENT,
            barangay=None,
        )
        Resident.objects.create(
            user=unassigned_user,
            full_name="Unassigned Resident",
            birth_date="1998-01-01",
            is_verified=True,
        )
        self.client.force_login(unassigned_user)
        unassigned_resp = self.client.post(
            self.url,
            {"title": "Leak", "description": "Pipe leak", "location": "Purok 1"},
            format="json",
        )
        self.assertEqual(unassigned_resp.status_code, status.HTTP_403_FORBIDDEN)

        unverified_user = User.objects.create_user(
            username="unverified_report_resident",
            password="SecurePassword123!",
            role=User.Role.RESIDENT,
            barangay=self.barangay,
        )
        Resident.objects.create(
            user=unverified_user,
            full_name="Unverified Resident",
            birth_date="1999-01-01",
            is_verified=False,
        )
        self.client.force_login(unverified_user)
        unverified_resp = self.client.post(
            self.url,
            {"title": "Leak", "description": "Pipe leak", "location": "Purok 1"},
            format="json",
        )
        self.assertEqual(unverified_resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(IssueReport.objects.filter(reporter=unverified_user).exists())
