from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from gridy_auth.models import User, Barangay, Resident
from gridy_services.models import DocumentRequest
from gridy_audit.models import AuditLog


class FeeAssessmentWorkflowAndRBACTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.barangay = Barangay.objects.create(name="Barangay Assessment City")
        self.other_barangay = Barangay.objects.create(name="Foreign Assessment City")

        self.resident = User.objects.create_user(
            username="assessment_resident",
            email="resident@assessment.test",
            role=User.Role.RESIDENT,
            barangay=self.barangay,
        )
        Resident.objects.create(
            user=self.resident,
            full_name="Assessment Resident",
            birth_date="1995-05-15",
            is_verified=True,
        )
        self.other_resident = User.objects.create_user(
            username="other_resident",
            email="other@assessment.test",
            role=User.Role.RESIDENT,
            barangay=self.barangay,
        )
        Resident.objects.create(
            user=self.other_resident,
            full_name="Other Resident",
            birth_date="1992-02-12",
            is_verified=True,
        )
        self.admin = User.objects.create_user(
            username="barangay_admin",
            email="admin@assessment.test",
            role=User.Role.ADMIN,
            barangay=self.barangay,
        )
        self.field_official = User.objects.create_user(
            username="field_official",
            email="official@assessment.test",
            role=User.Role.FIELD_OFFICIAL,
            barangay=self.barangay,
        )
        self.foreign_admin = User.objects.create_user(
            username="foreign_admin",
            email="foreign@assessment.test",
            role=User.Role.ADMIN,
            barangay=self.other_barangay,
        )
        self.unassigned_official = User.objects.create_user(
            username="unassigned_official",
            email="unassigned@assessment.test",
            role=User.Role.FIELD_OFFICIAL,
            barangay=None,
        )

    def test_ordinary_request_creation_defaults_to_awaiting_assessment(self):
        self.client.force_login(self.resident)
        response = self.client.post(
            reverse("document-request-list"),
            {
                "document_type": "Barangay Clearance",
                "purpose": "Employment",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        doc = DocumentRequest.objects.get(pk=response.data["id"])
        self.assertEqual(
            doc.fee_assessment_status,
            DocumentRequest.FeeAssessmentStatus.AWAITING_ASSESSMENT,
        )
        self.assertEqual(doc.fee_amount, Decimal("0.00"))
        self.assertEqual(doc.payment_status, DocumentRequest.PaymentStatus.NOT_REQUIRED)
        self.assertIsNone(doc.fee_assessed_by)
        self.assertIsNone(doc.fee_assessed_at)
        self.assertEqual(doc.fee_waiver_reason, "")

    def test_statutory_exempt_creation_defaults_to_statutory_exempt(self):
        self.client.force_login(self.resident)
        response = self.client.post(
            reverse("document-request-list"),
            {
                "document_type": "Certificate of Indigency",
                "purpose": "Scholarship",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        doc = DocumentRequest.objects.get(pk=response.data["id"])
        self.assertEqual(
            doc.fee_assessment_status,
            DocumentRequest.FeeAssessmentStatus.STATUTORY_EXEMPT,
        )
        self.assertEqual(doc.fee_amount, Decimal("0.00"))
        self.assertEqual(doc.payment_status, DocumentRequest.PaymentStatus.NOT_REQUIRED)
        self.assertIsNone(doc.fee_assessed_by)
        self.assertIsNotNone(doc.fee_assessed_at)

    def test_staff_cannot_mark_ready_for_pickup_while_awaiting_assessment(self):
        doc = DocumentRequest.objects.create(
            user=self.resident,
            barangay=self.barangay,
            document_type="Barangay Clearance",
            purpose="Employment",
            status=DocumentRequest.Status.PROCESSING,
            fee_amount=Decimal("0.00"),
            fee_assessment_status=DocumentRequest.FeeAssessmentStatus.AWAITING_ASSESSMENT,
        )
        self.client.force_login(self.admin)
        response = self.client.patch(
            reverse("document-request-validate", args=[doc.pk]),
            {"status": DocumentRequest.Status.READY_FOR_PICKUP},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("fee_assessment_status", response.data)
        doc.refresh_from_db()
        self.assertEqual(doc.status, DocumentRequest.Status.PROCESSING)

    def test_field_official_cannot_assess_positive_fee(self):
        doc = DocumentRequest.objects.create(
            user=self.resident,
            barangay=self.barangay,
            document_type="Barangay Clearance",
            purpose="Employment",
            status=DocumentRequest.Status.PROCESSING,
            fee_amount=Decimal("0.00"),
            fee_assessment_status=DocumentRequest.FeeAssessmentStatus.AWAITING_ASSESSMENT,
        )
        initial_audit_count = AuditLog.objects.count()
        self.client.force_login(self.field_official)
        response = self.client.patch(
            reverse("document-request-validate", args=[doc.pk]),
            {
                "fee_amount": 65.00,
                "status": DocumentRequest.Status.READY_FOR_PICKUP,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("Only a Barangay Admin", response.data["detail"])
        doc.refresh_from_db()
        self.assertEqual(
            doc.fee_assessment_status,
            DocumentRequest.FeeAssessmentStatus.AWAITING_ASSESSMENT,
        )
        self.assertEqual(doc.fee_amount, Decimal("0.00"))
        self.assertIsNone(doc.fee_assessed_by)
        self.assertIsNone(doc.fee_assessed_at)
        self.assertEqual(doc.fee_waiver_reason, "")
        self.assertEqual(doc.payment_status, DocumentRequest.PaymentStatus.NOT_REQUIRED)
        self.assertEqual(doc.status, DocumentRequest.Status.PROCESSING)
        self.assertEqual(AuditLog.objects.count(), initial_audit_count)

    def test_staff_waiving_fee_requires_justification(self):
        doc = DocumentRequest.objects.create(
            user=self.resident,
            barangay=self.barangay,
            document_type="Barangay Clearance",
            purpose="Employment",
            status=DocumentRequest.Status.PROCESSING,
            fee_amount=Decimal("0.00"),
            fee_assessment_status=DocumentRequest.FeeAssessmentStatus.AWAITING_ASSESSMENT,
        )
        self.client.force_login(self.admin)

        # Attempt to waive with 0 fee but empty reason
        res_empty = self.client.patch(
            reverse("document-request-validate", args=[doc.pk]),
            {
                "fee_amount": 0,
                "fee_waiver_reason": "   ",
                "status": DocumentRequest.Status.READY_FOR_PICKUP,
            },
            format="json",
        )
        self.assertEqual(res_empty.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("fee_waiver_reason", res_empty.data)

        # Attempt with valid justification
        res_valid = self.client.patch(
            reverse("document-request-validate", args=[doc.pk]),
            {
                "fee_amount": 0,
                "fee_waiver_reason": "Resident presented approved financial assistance referral.",
                "status": DocumentRequest.Status.READY_FOR_PICKUP,
            },
            format="json",
        )
        self.assertEqual(res_valid.status_code, status.HTTP_200_OK)
        doc.refresh_from_db()
        self.assertEqual(
            doc.fee_assessment_status, DocumentRequest.FeeAssessmentStatus.WAIVED
        )
        self.assertEqual(doc.fee_amount, Decimal("0.00"))
        self.assertEqual(doc.fee_assessed_by, self.admin)
        self.assertEqual(
            doc.fee_waiver_reason,
            "Resident presented approved financial assistance referral.",
        )
        self.assertEqual(doc.payment_status, DocumentRequest.PaymentStatus.NOT_REQUIRED)
        self.assertEqual(doc.status, DocumentRequest.Status.READY_FOR_PICKUP)

        # Confirm AuditLog
        log_entry = AuditLog.objects.filter(
            action_type=AuditLog.ActionType.DOCUMENT_ACTION,
            action_by=self.admin,
        ).first()
        self.assertIsNotNone(log_entry)
        self.assertIn("Approved zero-fee waiver", log_entry.description)
        self.assertIn("financial assistance referral", log_entry.description)

    def test_status_only_waiver_cannot_bypass_reason_provenance_or_readiness_gate(self):
        doc = DocumentRequest.objects.create(
            user=self.resident,
            barangay=self.barangay,
            document_type="Barangay Clearance",
            purpose="Employment",
            status=DocumentRequest.Status.PROCESSING,
            fee_amount=Decimal("0.00"),
            fee_assessment_status=DocumentRequest.FeeAssessmentStatus.AWAITING_ASSESSMENT,
        )
        self.client.force_login(self.admin)
        initial_audit_count = AuditLog.objects.count()

        response = self.client.patch(
            reverse("document-request-validate", args=[doc.pk]),
            {
                "fee_assessment_status": DocumentRequest.FeeAssessmentStatus.WAIVED,
                "status": DocumentRequest.Status.READY_FOR_PICKUP,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("fee_assessment_status", response.data)
        doc.refresh_from_db()
        self.assertEqual(doc.status, DocumentRequest.Status.PROCESSING)
        self.assertEqual(
            doc.fee_assessment_status,
            DocumentRequest.FeeAssessmentStatus.AWAITING_ASSESSMENT,
        )
        self.assertIsNone(doc.fee_assessed_by)
        self.assertIsNone(doc.fee_assessed_at)
        self.assertEqual(doc.fee_waiver_reason, "")
        self.assertEqual(AuditLog.objects.count(), initial_audit_count)

    def test_statutory_exempt_request_cannot_have_fee_added(self):
        doc = DocumentRequest.objects.create(
            user=self.resident,
            barangay=self.barangay,
            document_type="First Time Job Seeker Certificate",
            purpose="Job Application",
            status=DocumentRequest.Status.PROCESSING,
            fee_amount=Decimal("0.00"),
            fee_assessment_status=DocumentRequest.FeeAssessmentStatus.STATUTORY_EXEMPT,
        )
        self.client.force_login(self.admin)
        response = self.client.patch(
            reverse("document-request-validate", args=[doc.pk]),
            {"fee_amount": 50.00},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        doc.refresh_from_db()
        self.assertEqual(doc.fee_amount, Decimal("0.00"))
        self.assertEqual(
            doc.fee_assessment_status,
            DocumentRequest.FeeAssessmentStatus.STATUTORY_EXEMPT,
        )

    def test_cross_barangay_and_unassigned_staff_cannot_validate(self):
        doc = DocumentRequest.objects.create(
            user=self.resident,
            barangay=self.barangay,
            document_type="Barangay Clearance",
            purpose="Employment",
            status=DocumentRequest.Status.PROCESSING,
            fee_amount=Decimal("0.00"),
            fee_assessment_status=DocumentRequest.FeeAssessmentStatus.AWAITING_ASSESSMENT,
        )
        # Foreign Admin
        self.client.force_login(self.foreign_admin)
        res_foreign = self.client.patch(
            reverse("document-request-validate", args=[doc.pk]),
            {"fee_amount": 50.00},
            format="json",
        )
        self.assertEqual(res_foreign.status_code, status.HTTP_404_NOT_FOUND)

        # Unassigned Official
        self.client.force_login(self.unassigned_official)
        res_unassigned = self.client.patch(
            reverse("document-request-validate", args=[doc.pk]),
            {"fee_amount": 50.00},
            format="json",
        )
        self.assertEqual(res_unassigned.status_code, status.HTTP_404_NOT_FOUND)

    def test_resident_cannot_mutate_fee_assessment_fields(self):
        doc = DocumentRequest.objects.create(
            user=self.resident,
            barangay=self.barangay,
            document_type="Barangay Clearance",
            purpose="Employment",
            status=DocumentRequest.Status.PENDING,
            fee_amount=Decimal("0.00"),
            fee_assessment_status=DocumentRequest.FeeAssessmentStatus.AWAITING_ASSESSMENT,
        )
        self.client.force_login(self.resident)
        response = self.client.patch(
            reverse("document-request-detail", args=[doc.pk]),
            {
                "fee_assessment_status": "WAIVED",
                "fee_waiver_reason": "I waived it myself",
                "fee_amount": 0.00,
            },
            format="json",
        )
        # Residents cannot update fields or mutate assessment
        doc.refresh_from_db()
        self.assertEqual(
            doc.fee_assessment_status,
            DocumentRequest.FeeAssessmentStatus.AWAITING_ASSESSMENT,
        )
        self.assertEqual(doc.fee_waiver_reason, "")

    def test_release_gate_allows_waived_document_without_or_number(self):
        doc = DocumentRequest.objects.create(
            user=self.resident,
            barangay=self.barangay,
            document_type="Barangay Clearance",
            purpose="Employment",
            status=DocumentRequest.Status.READY_FOR_PICKUP,
            fee_amount=Decimal("0.00"),
            fee_assessment_status=DocumentRequest.FeeAssessmentStatus.WAIVED,
            fee_assessed_by=self.admin,
            fee_assessed_at=timezone.now(),
            fee_waiver_reason="Emergency shelter assistance exemption",
            payment_status=DocumentRequest.PaymentStatus.NOT_REQUIRED,
        )
        self.client.force_login(self.admin)
        response = self.client.patch(
            reverse("document-request-validate", args=[doc.pk]),
            {"status": DocumentRequest.Status.RELEASED},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        doc.refresh_from_db()
        self.assertEqual(doc.status, DocumentRequest.Status.RELEASED)

    def test_serializer_exposes_fee_assessment_provenance(self):
        doc = DocumentRequest.objects.create(
            user=self.resident,
            barangay=self.barangay,
            document_type="Barangay Clearance",
            purpose="Employment",
            status=DocumentRequest.Status.READY_FOR_PICKUP,
            fee_amount=Decimal("50.00"),
            fee_assessment_status=DocumentRequest.FeeAssessmentStatus.ASSESSED,
            fee_assessed_by=self.field_official,
            fee_assessed_at=timezone.now(),
            payment_status=DocumentRequest.PaymentStatus.UNPAID,
        )
        self.client.force_login(self.resident)
        response = self.client.get(reverse("document-request-detail", args=[doc.pk]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["fee_assessment_status"], "ASSESSED")
        self.assertEqual(
            response.data["fee_assessed_by_name"], self.field_official.get_full_name() or self.field_official.username
        )
        self.assertIsNotNone(response.data["fee_assessed_at"])
        self.assertEqual(response.data["fee_waiver_reason"], "")


class StatutoryExemptionPolicyAndRegressionTests(TestCase):
    """Regression tests for RA 11261 exemption policy and model-level write guard."""

    def setUp(self):
        self.client = APIClient()
        self.barangay = Barangay.objects.create(name="Policy Test Barangay")
        self.resident = User.objects.create_user(
            username="policy_resident",
            email="policy@test.test",
            role=User.Role.RESIDENT,
            barangay=self.barangay,
        )
        Resident.objects.create(
            user=self.resident,
            full_name="Policy Resident",
            birth_date="1995-06-10",
            is_verified=True,
        )
        self.admin = User.objects.create_user(
            username="policy_admin",
            email="policyadmin@test.test",
            role=User.Role.ADMIN,
            barangay=self.barangay,
        )

    def test_document_name_alone_does_not_grant_statutory_exemption_on_creation(self):
        """Codex REV-01: Do not grant a statutory exemption solely because a request has
        a matching document name. Requests for 'First Time Job Seeker Certificate' start
        as AWAITING_ASSESSMENT until eligibility is explicitly verified."""
        self.client.force_login(self.resident)
        response = self.client.post(
            reverse("document-request-list"),
            {
                "document_type": "First Time Job Seeker Certificate",
                "purpose": "Employment",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        doc = DocumentRequest.objects.get(pk=response.data["id"])
        self.assertEqual(
            doc.fee_assessment_status,
            DocumentRequest.FeeAssessmentStatus.AWAITING_ASSESSMENT,
        )
        self.assertIsNone(doc.fee_assessed_by)
        self.assertIsNone(doc.fee_assessed_at)

    def test_ra11261_fee_free_barangay_clearance_granted_with_staff_provenance(self):
        """RA 11261: Barangay Clearance fee can be exempted under RA 11261 when staff
        explicitly assesses and verifies first-time-jobseeker eligibility."""
        self.client.force_login(self.resident)
        create_resp = self.client.post(
            reverse("document-request-list"),
            {
                "document_type": "Barangay Clearance",
                "purpose": "First Time Jobseeker under RA 11261",
            },
            format="json",
        )
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        doc_id = create_resp.data["id"]

        self.client.force_login(self.admin)
        validate_url = reverse("document-request-validate", kwargs={"pk": doc_id})
        response = self.client.patch(
            validate_url,
            {
                "fee_assessment_status": DocumentRequest.FeeAssessmentStatus.STATUTORY_EXEMPT,
                "fee_waiver_reason": "RA 11261 First-Time Jobseeker certification verified on file.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        doc = DocumentRequest.objects.get(pk=doc_id)
        self.assertEqual(
            doc.fee_assessment_status,
            DocumentRequest.FeeAssessmentStatus.STATUTORY_EXEMPT,
        )
        self.assertEqual(doc.fee_amount, Decimal("0.00"))
        self.assertEqual(doc.fee_assessed_by, self.admin)
        self.assertIsNotNone(doc.fee_assessed_at)
        self.assertEqual(
            doc.fee_waiver_reason,
            "RA 11261 First-Time Jobseeker certification verified on file.",
        )
        self.assertEqual(doc.payment_status, DocumentRequest.PaymentStatus.NOT_REQUIRED)

    def test_ra11261_requires_explicit_staff_justification(self):
        doc = DocumentRequest.objects.create(
            user=self.resident,
            barangay=self.barangay,
            document_type="Barangay Clearance",
            purpose="First Time Jobseeker under RA 11261",
            status=DocumentRequest.Status.PROCESSING,
            fee_amount=Decimal("0.00"),
            fee_assessment_status=DocumentRequest.FeeAssessmentStatus.AWAITING_ASSESSMENT,
        )
        self.client.force_login(self.admin)
        initial_audit_count = AuditLog.objects.count()

        response = self.client.patch(
            reverse("document-request-validate", args=[doc.pk]),
            {"fee_assessment_status": DocumentRequest.FeeAssessmentStatus.STATUTORY_EXEMPT},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("fee_waiver_reason", response.data)
        doc.refresh_from_db()
        self.assertEqual(
            doc.fee_assessment_status,
            DocumentRequest.FeeAssessmentStatus.AWAITING_ASSESSMENT,
        )
        self.assertEqual(doc.fee_waiver_reason, "")
        self.assertEqual(AuditLog.objects.count(), initial_audit_count)

    def test_ra11261_rejects_non_clearance_document_type(self):
        doc = DocumentRequest.objects.create(
            user=self.resident,
            barangay=self.barangay,
            document_type="Police Clearance",
            purpose="First Time Jobseeker under RA 11261",
            status=DocumentRequest.Status.PROCESSING,
            fee_amount=Decimal("0.00"),
            fee_assessment_status=DocumentRequest.FeeAssessmentStatus.AWAITING_ASSESSMENT,
        )
        self.client.force_login(self.admin)

        response = self.client.patch(
            reverse("document-request-validate", args=[doc.pk]),
            {
                "fee_assessment_status": DocumentRequest.FeeAssessmentStatus.STATUTORY_EXEMPT,
                "fee_waiver_reason": "RA 11261 eligibility verified on file.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Barangay Clearance", str(response.data))
        doc.refresh_from_db()
        self.assertEqual(
            doc.fee_assessment_status,
            DocumentRequest.FeeAssessmentStatus.AWAITING_ASSESSMENT,
        )

    def test_ra11261_rejects_walk_in_without_linked_resident(self):
        doc = DocumentRequest.objects.create(
            user=None,
            barangay=self.barangay,
            is_walkin=True,
            walkin_name="Walk-in Applicant",
            document_type="Barangay Clearance",
            purpose="First Time Jobseeker under RA 11261",
            status=DocumentRequest.Status.PROCESSING,
            fee_amount=Decimal("0.00"),
            fee_assessment_status=DocumentRequest.FeeAssessmentStatus.AWAITING_ASSESSMENT,
        )
        self.client.force_login(self.admin)

        response = self.client.patch(
            reverse("document-request-validate", args=[doc.pk]),
            {
                "fee_assessment_status": DocumentRequest.FeeAssessmentStatus.STATUTORY_EXEMPT,
                "fee_waiver_reason": "RA 11261 eligibility verified on file.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("linked resident", str(response.data).lower())
        doc.refresh_from_db()
        self.assertEqual(
            doc.fee_assessment_status,
            DocumentRequest.FeeAssessmentStatus.AWAITING_ASSESSMENT,
        )

    def test_other_statutory_document_does_not_consume_ra11261_one_time_benefit(self):
        DocumentRequest.objects.create(
            user=self.resident,
            barangay=self.barangay,
            document_type="Certificate of Indigency",
            purpose="Scholarship",
            fee_amount=Decimal("0.00"),
            fee_assessment_status=DocumentRequest.FeeAssessmentStatus.STATUTORY_EXEMPT,
            status=DocumentRequest.Status.RELEASED,
        )
        clearance = DocumentRequest.objects.create(
            user=self.resident,
            barangay=self.barangay,
            document_type="Barangay Clearance",
            purpose="First Time Jobseeker under RA 11261",
            fee_amount=Decimal("0.00"),
            fee_assessment_status=DocumentRequest.FeeAssessmentStatus.AWAITING_ASSESSMENT,
            status=DocumentRequest.Status.PROCESSING,
        )
        self.client.force_login(self.admin)

        response = self.client.patch(
            reverse("document-request-validate", args=[clearance.pk]),
            {
                "fee_assessment_status": DocumentRequest.FeeAssessmentStatus.STATUTORY_EXEMPT,
                "fee_waiver_reason": "RA 11261 first-time jobseeker certification verified.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        clearance.refresh_from_db()
        self.assertEqual(
            clearance.fee_assessment_status,
            DocumentRequest.FeeAssessmentStatus.STATUTORY_EXEMPT,
        )

    def test_one_time_benefit_restriction_blocks_second_ra11261_statutory_exemption(self):
        """RA 11261 Sec. 5: The benefit is strictly one-time. A resident who has already
        received an RA 11261 statutory fee exemption cannot receive another."""
        # First clearance granted statutory exemption
        DocumentRequest.objects.create(
            user=self.resident,
            barangay=self.barangay,
            # Historical free-text labels can contain inconsistent whitespace.
            document_type="  Barangay   Clearance  ",
            purpose="First Time Jobseeker - First Job",
            fee_amount=Decimal("0.00"),
            fee_assessment_status=DocumentRequest.FeeAssessmentStatus.STATUTORY_EXEMPT,
            fee_assessed_by=self.admin,
            fee_assessed_at=timezone.now(),
            fee_waiver_reason="RA 11261 verified",
            status=DocumentRequest.Status.RELEASED,
        )

        # Second clearance requested by same resident
        second_doc = DocumentRequest.objects.create(
            user=self.resident,
            barangay=self.barangay,
            document_type="Barangay Clearance",
            purpose="Second Employment Application",
            fee_amount=Decimal("0.00"),
            fee_assessment_status=DocumentRequest.FeeAssessmentStatus.AWAITING_ASSESSMENT,
            status=DocumentRequest.Status.PROCESSING,
        )

        self.client.force_login(self.admin)
        validate_url = reverse("document-request-validate", kwargs={"pk": second_doc.pk})
        response = self.client.patch(
            validate_url,
            {
                "fee_assessment_status": DocumentRequest.FeeAssessmentStatus.STATUTORY_EXEMPT,
                "fee_waiver_reason": "Second claim attempt under RA 11261",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("fee_assessment_status", response.data)
        self.assertIn("already availed", str(response.data["fee_assessment_status"]))

        # But the second clearance CAN be assessed a normal fee
        assessed_resp = self.client.patch(
            validate_url,
            {"fee_amount": "50.00"},
            format="json",
        )
        self.assertEqual(assessed_resp.status_code, status.HTTP_200_OK)
        second_doc.refresh_from_db()
        self.assertEqual(second_doc.fee_assessment_status, DocumentRequest.FeeAssessmentStatus.ASSESSED)
        self.assertEqual(second_doc.fee_amount, Decimal("50.00"))

    def test_rejected_statutory_exempt_request_does_not_consume_one_time_benefit(self):
        """If a previous statutory exempt request was REJECTED, the resident has not
        effectively availed of the benefit, so a subsequent request may still receive it."""
        DocumentRequest.objects.create(
            user=self.resident,
            barangay=self.barangay,
            document_type="Barangay Clearance",
            purpose="Failed application",
            fee_amount=Decimal("0.00"),
            fee_assessment_status=DocumentRequest.FeeAssessmentStatus.STATUTORY_EXEMPT,
            status=DocumentRequest.Status.REJECTED,
        )

        new_doc = DocumentRequest.objects.create(
            user=self.resident,
            barangay=self.barangay,
            document_type="Barangay Clearance",
            purpose="Valid First Time Jobseeker",
            fee_amount=Decimal("0.00"),
            fee_assessment_status=DocumentRequest.FeeAssessmentStatus.AWAITING_ASSESSMENT,
            status=DocumentRequest.Status.PROCESSING,
        )

        self.client.force_login(self.admin)
        validate_url = reverse("document-request-validate", kwargs={"pk": new_doc.pk})
        response = self.client.patch(
            validate_url,
            {
                "fee_assessment_status": DocumentRequest.FeeAssessmentStatus.STATUTORY_EXEMPT,
                "fee_waiver_reason": "Valid first jobseeker certification.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        new_doc.refresh_from_db()
        self.assertEqual(new_doc.fee_assessment_status, DocumentRequest.FeeAssessmentStatus.STATUTORY_EXEMPT)

    def test_barangay_clearance_does_not_receive_statutory_exempt(self):
        """Barangay Clearance is an ordinary document; it must start as AWAITING_ASSESSMENT."""
        self.client.force_login(self.resident)
        response = self.client.post(
            reverse("document-request-list"),
            {
                "document_type": "Barangay Clearance",
                "purpose": "Employment",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        doc = DocumentRequest.objects.get(pk=response.data["id"])
        self.assertNotEqual(
            doc.fee_assessment_status,
            DocumentRequest.FeeAssessmentStatus.STATUTORY_EXEMPT,
        )
        self.assertEqual(
            doc.fee_assessment_status,
            DocumentRequest.FeeAssessmentStatus.AWAITING_ASSESSMENT,
        )

    def test_model_level_write_with_positive_fee_does_not_auto_promote_to_assessed(self):
        """Regression: Bypassing the view and setting fee_amount > 0 must not auto-promote
        fee_assessment_status to ASSESSED. All state transitions require staff provenance."""
        doc = DocumentRequest.objects.create(
            document_type="Barangay Clearance",
            purpose="Employment",
            user=self.resident,
            barangay=self.barangay,
            fee_amount=Decimal("0.00"),
            fee_assessment_status=DocumentRequest.FeeAssessmentStatus.AWAITING_ASSESSMENT,
        )
        # Directly mutate fee_amount as if a rogue model-level write occurred
        doc.fee_amount = Decimal("50.00")
        doc.save(update_fields=["fee_amount"])
        doc.refresh_from_db()
        # The status must NOT have been silently promoted
        self.assertEqual(
            doc.fee_assessment_status,
            DocumentRequest.FeeAssessmentStatus.AWAITING_ASSESSMENT,
        )
        self.assertIsNone(doc.fee_assessed_by)
        self.assertIsNone(doc.fee_assessed_at)

    def test_invariant_no_ready_for_pickup_record_with_awaiting_assessment_after_creation(self):
        """Documents created via the API must never be at READY_FOR_PICKUP with
        AWAITING_ASSESSMENT — the assessment gate in the validate action prevents it.
        This test documents the pre/post invariant that migration 0016 enforced."""
        self.client.force_login(self.resident)
        response = self.client.post(
            reverse("document-request-list"),
            {
                "document_type": "Barangay Clearance",
                "purpose": "Employment invariant test",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        doc = DocumentRequest.objects.get(pk=response.data["id"])
        # Attempt to set the document to READY_FOR_PICKUP via the staff validate action
        # while fee is still AWAITING_ASSESSMENT — must be rejected.
        self.client.force_login(self.admin)
        validate_url = reverse("document-request-validate", kwargs={"pk": doc.pk})
        response = self.client.patch(
            validate_url,
            {"status": "READY_FOR_PICKUP"},
            format="json",
        )
        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN])
        doc.refresh_from_db()
        # Must NOT be at READY_FOR_PICKUP with AWAITING_ASSESSMENT simultaneously
        if doc.status == DocumentRequest.Status.READY_FOR_PICKUP:
            self.assertNotEqual(
                doc.fee_assessment_status,
                DocumentRequest.FeeAssessmentStatus.AWAITING_ASSESSMENT,
            )
