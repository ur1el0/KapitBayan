from datetime import date, datetime
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from gridy_auth.models import Barangay, Resident, ResidentTransferRequest, User
from gridy_communications.models import ActivitySchedule, Announcement
from gridy_reports.models import IssueReport
from gridy_services.models import (
    AidRequest,
    DocumentRequest,
    EquipmentBorrowRequest,
    MANILA_TIME_ZONE,
)


class AccomplishmentReportAPITests(APITestCase):
    def setUp(self):
        self.barangay = Barangay.objects.create(
            name="Ibabang Dupay",
            municipality="City of Lucena",
            province="Quezon",
            captain_name="Hon. Juan Dela Cruz",
        )
        self.other_barangay = Barangay.objects.create(
            name="Gulang-Gulang",
            municipality="City of Lucena",
            province="Quezon",
            captain_name="Hon. Pedro Penduko",
        )
        self.admin = User.objects.create_user(
            username="dupay_admin",
            password="SecurePassword123!",
            role=User.Role.ADMIN,
            barangay=self.barangay,
        )
        self.other_admin = User.objects.create_user(
            username="gulang_admin",
            password="SecurePassword123!",
            role=User.Role.ADMIN,
            barangay=self.other_barangay,
        )
        self.resident = User.objects.create_user(
            username="dupay_resident",
            password="SecurePassword123!",
            role=User.Role.RESIDENT,
            barangay=self.barangay,
        )
        Resident.objects.create(
            user=self.resident,
            full_name="Maria Santos",
            birth_date="1990-05-10",
            is_verified=True,
        )
        self.report_url = reverse("dashboard-accomplishment-report")
        self.export_url = reverse("dashboard-accomplishment-report-export")

        self.oct_dt = datetime(2026, 10, 15, 10, 0, tzinfo=MANILA_TIME_ZONE)
        self.sep_dt = datetime(2026, 9, 20, 10, 0, tzinfo=MANILA_TIME_ZONE)
        self.nov_dt = datetime(2026, 11, 5, 10, 0, tzinfo=MANILA_TIME_ZONE)

        User.objects.filter(pk=self.resident.pk).update(date_joined=self.oct_dt)

        prev_resident = User.objects.create_user(
            username="sep_resident",
            password="SecurePassword123!",
            role=User.Role.RESIDENT,
            barangay=self.barangay,
        )
        Resident.objects.create(
            user=prev_resident,
            full_name="September Resident",
            birth_date="1988-01-01",
            is_verified=True,
        )
        User.objects.filter(pk=prev_resident.pk).update(date_joined=self.sep_dt)

        other_resident = User.objects.create_user(
            username="other_brgy_resident",
            password="SecurePassword123!",
            role=User.Role.RESIDENT,
            barangay=self.other_barangay,
        )
        Resident.objects.create(
            user=other_resident,
            full_name="Other Barangay Resident",
            birth_date="1991-03-03",
            is_verified=True,
        )
        User.objects.filter(pk=other_resident.pk).update(date_joined=self.oct_dt)

        # RBI Transfer in October
        transfer = ResidentTransferRequest.objects.create(
            resident=self.resident,
            source_barangay=self.other_barangay,
            destination_barangay=self.barangay,
            reason="Moved household",
            status=ResidentTransferRequest.Status.APPROVED,
        )
        ResidentTransferRequest.objects.filter(pk=transfer.pk).update(
            created_at=self.oct_dt
        )

        # Document Requests in October vs September vs Other Barangay
        doc1 = DocumentRequest.objects.create(
            user=self.resident,
            barangay=self.barangay,
            document_type="Barangay Clearance",
            status=DocumentRequest.Status.RELEASED,
            fee_assessment_status=DocumentRequest.FeeAssessmentStatus.ASSESSED,
        )
        doc2 = DocumentRequest.objects.create(
            user=self.resident,
            barangay=self.barangay,
            document_type="Certificate of Indigency",
            status=DocumentRequest.Status.RELEASED,
            fee_assessment_status=DocumentRequest.FeeAssessmentStatus.STATUTORY_EXEMPT,
        )
        doc_sep = DocumentRequest.objects.create(
            user=self.resident,
            barangay=self.barangay,
            document_type="Barangay Clearance",
            status=DocumentRequest.Status.RELEASED,
        )
        doc_other = DocumentRequest.objects.create(
            user=other_resident,
            barangay=self.other_barangay,
            document_type="Business Permit",
            status=DocumentRequest.Status.RELEASED,
        )
        DocumentRequest.objects.filter(pk__in=[doc1.pk, doc2.pk, doc_other.pk]).update(
            created_at=self.oct_dt
        )
        DocumentRequest.objects.filter(pk=doc_sep.pk).update(created_at=self.sep_dt)

        # Issues, Aid & Equipment in October vs November
        issue_oct = IssueReport.objects.create(
            reporter=self.resident,
            title="Clogged drain",
            description="Drainage issue",
            location="Purok 1",
            status=IssueReport.Status.RESOLVED,
        )
        issue_nov = IssueReport.objects.create(
            reporter=self.resident,
            title="Broken lamp",
            description="Streetlight out",
            location="Purok 2",
            status=IssueReport.Status.RESOLVED,
        )
        IssueReport.objects.filter(pk=issue_oct.pk).update(created_at=self.oct_dt)
        IssueReport.objects.filter(pk=issue_nov.pk).update(created_at=self.nov_dt)

        aid_oct = AidRequest.objects.create(
            requester=self.resident,
            barangay=self.barangay,
            assistance_type="Medical assistance",
            reason="Clinic support",
            status=AidRequest.Status.APPROVED,
        )
        AidRequest.objects.filter(pk=aid_oct.pk).update(created_at=self.oct_dt)

        equip_oct = EquipmentBorrowRequest.objects.create(
            resident=self.resident,
            barangay=self.barangay,
            item_type=EquipmentBorrowRequest.ItemType.MONOBLOCK_CHAIRS,
            quantity=20,
            borrow_date=date(2026, 10, 16),
            return_date=date(2026, 10, 17),
            purpose="Assembly",
            status=EquipmentBorrowRequest.Status.RETURNED,
        )
        EquipmentBorrowRequest.objects.filter(pk=equip_oct.pk).update(
            created_at=self.oct_dt
        )

        # Announcements & Activities in October
        ann_oct = Announcement.objects.create(
            title="October Clean-up",
            content="Bring broomsticks",
            created_by=self.admin,
        )
        Announcement.objects.filter(pk=ann_oct.pk).update(created_at=self.oct_dt)

        ActivitySchedule.objects.create(
            title="Barangay Assembly",
            description="General assembly",
            event_datetime=self.oct_dt,
            location="Covered Court",
            created_by=self.admin,
        )

    def test_monthly_filtering_and_categorized_metrics_accuracy(self):
        self.client.force_login(self.admin)

        response = self.client.get(self.report_url, {"year": 2026, "month": 10})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data["barangay_name"], "Ibabang Dupay")
        self.assertEqual(data["period_label"], "October 2026")

        self.assertEqual(data["residents_rbi"]["new_registered_residents"], 1)
        self.assertEqual(data["residents_rbi"]["new_verified_residents"], 1)
        self.assertEqual(data["residents_rbi"]["approved_rbi_transfers"], 1)
        self.assertEqual(data["residents_rbi"]["total_active_verified_residents"], 2)

        self.assertEqual(data["certificates_issuance"]["total_issued"], 2)
        self.assertEqual(data["certificates_issuance"]["fee_waived_or_exempt_count"], 1)
        doc_types = {
            row["document_type"]: row["count"]
            for row in data["certificates_issuance"]["by_document_type"]
        }
        self.assertEqual(
            doc_types,
            {"Barangay Clearance": 1, "Certificate of Indigency": 1},
        )

        self.assertEqual(data["community_services"]["issues_submitted"], 1)
        self.assertEqual(data["community_services"]["issues_resolved"], 1)
        self.assertEqual(data["community_services"]["aid_requests_approved"], 1)
        self.assertEqual(data["community_services"]["equipment_requests_fulfilled"], 1)

        self.assertEqual(data["communications_activities"]["announcements_published"], 1)
        self.assertEqual(data["communications_activities"]["activities_conducted"], 1)

    def test_cross_tenant_barangay_isolation(self):
        self.client.force_login(self.other_admin)

        response = self.client.get(self.report_url, {"year": 2026, "month": 10})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data["barangay_name"], "Gulang-Gulang")
        self.assertEqual(data["certificates_issuance"]["total_issued"], 1)
        self.assertEqual(
            data["certificates_issuance"]["by_document_type"],
            [{"document_type": "Business Permit", "count": 1}],
        )
        self.assertEqual(data["community_services"]["issues_resolved"], 0)
        self.assertEqual(data["community_services"]["aid_requests_approved"], 0)
        self.assertEqual(data["community_services"]["equipment_requests_fulfilled"], 0)
        self.assertEqual(data["communications_activities"]["announcements_published"], 0)

    def test_resident_and_unauthenticated_users_are_rejected(self):
        unauth_resp = self.client.get(self.report_url)
        self.assertEqual(unauth_resp.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.force_login(self.resident)
        resident_resp = self.client.get(self.report_url)
        self.assertEqual(resident_resp.status_code, status.HTTP_403_FORBIDDEN)

        resident_export_resp = self.client.get(
            self.export_url,
            {"year": 2026, "month": 10, "export_format": "pdf"},
        )
        self.assertEqual(resident_export_resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_csv_and_pdf_exports_return_valid_non_empty_files(self):
        self.client.force_login(self.admin)

        csv_resp = self.client.get(
            self.export_url,
            {"year": 2026, "month": 10, "export_format": "csv"},
        )
        self.assertEqual(csv_resp.status_code, status.HTTP_200_OK)
        self.assertIn("text/csv", csv_resp["Content-Type"])
        self.assertIn(
            'filename="Accomplishment_Report_Ibabang_Dupay_2026_10.csv"',
            csv_resp["Content-Disposition"],
        )
        csv_text = csv_resp.content.decode("utf-8-sig")
        self.assertIn("MONTHLY BARANGAY ACCOMPLISHMENT REPORT", csv_text)
        self.assertIn("Ibabang Dupay", csv_text)
        self.assertIn("Certificate of Indigency", csv_text)

        pdf_resp = self.client.get(
            self.export_url,
            {"year": 2026, "month": 10, "export_format": "pdf"},
        )
        self.assertEqual(pdf_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(pdf_resp["Content-Type"], "application/pdf")
        self.assertIn(
            'filename="Accomplishment_Report_Ibabang_Dupay_2026_10.pdf"',
            pdf_resp["Content-Disposition"],
        )
        self.assertTrue(pdf_resp.content.startswith(b"%PDF"))
        self.assertGreater(len(pdf_resp.content), 500)

    def test_custom_date_range_and_metric_filtering_synchronize_ui_csv_and_pdf(self):
        self.client.force_login(self.admin)

        # Custom date range spanning October 2026, filtered only to documents_issued and new_registered_residents
        params = {
            "start_date": "2026-10-01",
            "end_date": "2026-10-31",
            "metrics": "new_registered_residents,documents_issued",
        }
        report_resp = self.client.get(self.report_url, params)
        self.assertEqual(report_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(report_resp.data["period_mode"], "range")
        self.assertEqual(
            report_resp.data["included_metrics"],
            ["new_registered_residents", "documents_issued"],
        )

        # CSV should only contain the selected categories and exclude Community Issues / Communications
        csv_resp = self.client.get(
            self.export_url,
            {**params, "export_format": "csv"},
        )
        self.assertEqual(csv_resp.status_code, status.HTTP_200_OK)
        self.assertIn(
            'filename="Accomplishment_Report_Ibabang_Dupay_2026-10-01_to_2026-10-31.csv"',
            csv_resp["Content-Disposition"],
        )
        csv_text = csv_resp.content.decode("utf-8-sig")
        self.assertIn("New Registered Residents", csv_text)
        self.assertIn("Total Certificates / Clearances Issued", csv_text)
        self.assertNotIn("Community Issues Submitted", csv_text)
        self.assertNotIn("Public Announcements Published", csv_text)

        # PDF should render cleanly with filtered filename & content
        pdf_resp = self.client.get(
            self.export_url,
            {**params, "export_format": "pdf"},
        )
        self.assertEqual(pdf_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(pdf_resp["Content-Type"], "application/pdf")
        self.assertIn(
            'filename="Accomplishment_Report_Ibabang_Dupay_2026-10-01_to_2026-10-31.pdf"',
            pdf_resp["Content-Disposition"],
        )
        self.assertTrue(pdf_resp.content.startswith(b"%PDF"))

        # Reject reversed custom range or unsupported metric keys
        bad_range = self.client.get(
            self.report_url,
            {"start_date": "2026-10-31", "end_date": "2026-10-01"},
        )
        self.assertEqual(bad_range.status_code, status.HTTP_400_BAD_REQUEST)

        bad_metric = self.client.get(
            self.report_url,
            {"year": 2026, "month": 10, "metrics": "unknown_metric"},
        )
        self.assertEqual(bad_metric.status_code, status.HTTP_400_BAD_REQUEST)
