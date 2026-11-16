from datetime import date, timedelta
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from gridy_audit.models import AuditLog
from gridy_auth.models import Barangay, Resident, User
from gridy_communications.models import AdminNotification, ResidentNotification
from gridy_services.models import EquipmentBorrowRequest


class EquipmentBorrowRequestAPITests(APITestCase):
    def setUp(self):
        self.barangay = Barangay.objects.create(name="Equipment Borrowing Barangay")
        self.other_barangay = Barangay.objects.create(
            name="Other Equipment Borrowing Barangay"
        )
        self.resident = User.objects.create_user(
            username="borrow_resident",
            password="SecurePassword123!",
            role=User.Role.RESIDENT,
            barangay=self.barangay,
        )
        Resident.objects.create(
            user=self.resident,
            full_name="Borrow Resident",
            birth_date="1994-04-14",
            is_verified=True,
        )
        self.unverified_resident = User.objects.create_user(
            username="unverified_borrow_resident",
            password="SecurePassword123!",
            role=User.Role.RESIDENT,
            barangay=self.barangay,
        )
        Resident.objects.create(
            user=self.unverified_resident,
            full_name="Unverified Resident",
            birth_date="1995-05-15",
            is_verified=False,
        )
        self.unassigned_resident = User.objects.create_user(
            username="unassigned_borrow_resident",
            password="SecurePassword123!",
            role=User.Role.RESIDENT,
            barangay=None,
        )
        Resident.objects.create(
            user=self.unassigned_resident,
            full_name="Unassigned Resident",
            birth_date="1996-06-16",
            is_verified=True,
        )
        self.official = User.objects.create_user(
            username="borrow_official",
            password="SecurePassword123!",
            role=User.Role.ADMIN,
            barangay=self.barangay,
        )
        self.other_official = User.objects.create_user(
            username="other_borrow_official",
            password="SecurePassword123!",
            role=User.Role.ADMIN,
            barangay=self.other_barangay,
        )
        self.url = reverse("equipment-request-list")
        self.today = date.today()

    def test_resident_can_submit_borrowing_request_and_notifies_barangay_admins(self):
        self.client.force_login(self.resident)

        response = self.client.post(
            self.url,
            {
                "item_type": EquipmentBorrowRequest.ItemType.MONOBLOCK_CHAIRS,
                "quantity": 25,
                "borrow_date": str(self.today + timedelta(days=2)),
                "return_date": str(self.today + timedelta(days=3)),
                "time_slot": "08:00 AM - 05:00 PM",
                "purpose": "Neighborhood anniversary gathering.",
                "status": EquipmentBorrowRequest.Status.APPROVED,
                "admin_notes": "Forged approval",
                "barangay": self.other_barangay.pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        borrow_request = EquipmentBorrowRequest.objects.get(pk=response.data["id"])
        self.assertEqual(borrow_request.resident, self.resident)
        self.assertEqual(borrow_request.barangay, self.barangay)
        self.assertEqual(borrow_request.quantity, 25)
        self.assertEqual(borrow_request.status, EquipmentBorrowRequest.Status.PENDING)
        self.assertEqual(borrow_request.admin_notes, "")
        self.assertIsNone(borrow_request.reviewed_by)
        self.assertIsNone(borrow_request.reviewed_at)
        self.assertIsNone(borrow_request.returned_at)
        self.assertTrue(
            AdminNotification.objects.filter(
                user=self.official,
                title__icontains="equipment",
            ).exists()
        )
        self.assertFalse(
            AdminNotification.objects.filter(user=self.other_official).exists()
        )

    def test_return_date_before_borrow_date_is_rejected(self):
        self.client.force_login(self.resident)

        response = self.client.post(
            self.url,
            {
                "item_type": EquipmentBorrowRequest.ItemType.TENT_CANOPY,
                "quantity": 1,
                "borrow_date": str(self.today + timedelta(days=5)),
                "return_date": str(self.today + timedelta(days=3)),
                "purpose": "Community clean-up drive.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("return_date", response.data)
        self.assertEqual(EquipmentBorrowRequest.objects.count(), 0)

    def test_unverified_and_unassigned_residents_cannot_submit_requests(self):
        payload = {
            "item_type": EquipmentBorrowRequest.ItemType.TABLES,
            "quantity": 4,
            "borrow_date": str(self.today + timedelta(days=1)),
            "return_date": str(self.today + timedelta(days=1)),
            "purpose": "Community meeting.",
        }

        self.client.force_login(self.unverified_resident)
        unverified_resp = self.client.post(self.url, payload, format="json")
        self.assertEqual(unverified_resp.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_login(self.unassigned_resident)
        unassigned_resp = self.client.post(self.url, payload, format="json")
        self.assertEqual(unassigned_resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(EquipmentBorrowRequest.objects.count(), 0)

    def test_cross_barangay_tenant_isolation(self):
        borrow_request = EquipmentBorrowRequest.objects.create(
            resident=self.resident,
            barangay=self.barangay,
            item_type=EquipmentBorrowRequest.ItemType.SOUND_SYSTEM,
            quantity=1,
            borrow_date=self.today,
            return_date=self.today + timedelta(days=1),
            purpose="Purok assembly.",
        )

        self.client.force_login(self.other_official)
        list_resp = self.client.get(self.url)
        self.assertEqual(list_resp.status_code, status.HTTP_200_OK)
        results = list_resp.data.get("results", list_resp.data)
        self.assertEqual(len(results), 0)

        patch_resp = self.client.patch(
            reverse("equipment-request-detail", args=[borrow_request.pk]),
            {"status": EquipmentBorrowRequest.Status.APPROVED},
            format="json",
        )
        self.assertEqual(patch_resp.status_code, status.HTTP_404_NOT_FOUND)
        borrow_request.refresh_from_db()
        self.assertEqual(borrow_request.status, EquipmentBorrowRequest.Status.PENDING)

    def test_admin_can_approve_and_mark_returned_with_timestamps_audit_and_notifications(
        self,
    ):
        borrow_request = EquipmentBorrowRequest.objects.create(
            resident=self.resident,
            barangay=self.barangay,
            item_type=EquipmentBorrowRequest.ItemType.COVERED_COURT,
            quantity=1,
            borrow_date=self.today + timedelta(days=1),
            return_date=self.today + timedelta(days=1),
            time_slot="01:00 PM - 05:00 PM",
            purpose="Youth basketball practice.",
        )
        self.client.force_login(self.official)

        approve_resp = self.client.patch(
            reverse("equipment-request-detail", args=[borrow_request.pk]),
            {
                "status": EquipmentBorrowRequest.Status.APPROVED,
                "admin_notes": "Approved. Claim key at the barangay desk.",
            },
            format="json",
        )
        self.assertEqual(approve_resp.status_code, status.HTTP_200_OK)
        borrow_request.refresh_from_db()
        self.assertEqual(borrow_request.status, EquipmentBorrowRequest.Status.APPROVED)
        self.assertEqual(borrow_request.reviewed_by, self.official)
        self.assertIsNotNone(borrow_request.reviewed_at)
        self.assertIsNone(borrow_request.returned_at)
        self.assertTrue(
            ResidentNotification.objects.filter(
                user=self.resident,
                data__equipment_request_id=str(borrow_request.pk),
                data__status=EquipmentBorrowRequest.Status.APPROVED,
            ).exists()
        )

        return_resp = self.client.patch(
            reverse("equipment-request-detail", args=[borrow_request.pk]),
            {
                "status": EquipmentBorrowRequest.Status.RETURNED,
                "admin_notes": "Returned in good condition.",
            },
            format="json",
        )
        self.assertEqual(return_resp.status_code, status.HTTP_200_OK)
        borrow_request.refresh_from_db()
        self.assertEqual(borrow_request.status, EquipmentBorrowRequest.Status.RETURNED)
        self.assertIsNotNone(borrow_request.returned_at)
        self.assertTrue(
            ResidentNotification.objects.filter(
                user=self.resident,
                data__equipment_request_id=str(borrow_request.pk),
                data__status=EquipmentBorrowRequest.Status.RETURNED,
            ).exists()
        )
        self.assertTrue(
            AuditLog.objects.filter(
                action_by=self.official,
                action_type=AuditLog.ActionType.USER_ACTION,
                description__icontains=f"#{borrow_request.pk}",
            ).exists()
        )

    def test_declining_requires_admin_notes_and_locks_further_changes(self):
        borrow_request = EquipmentBorrowRequest.objects.create(
            resident=self.resident,
            barangay=self.barangay,
            item_type=EquipmentBorrowRequest.ItemType.TENT_CANOPY,
            quantity=2,
            borrow_date=self.today + timedelta(days=2),
            return_date=self.today + timedelta(days=3),
            purpose="Private event.",
        )
        self.client.force_login(self.official)

        missing_note_resp = self.client.patch(
            reverse("equipment-request-detail", args=[borrow_request.pk]),
            {"status": EquipmentBorrowRequest.Status.DECLINED},
            format="json",
        )
        self.assertEqual(missing_note_resp.status_code, status.HTTP_400_BAD_REQUEST)

        decline_resp = self.client.patch(
            reverse("equipment-request-detail", args=[borrow_request.pk]),
            {
                "status": EquipmentBorrowRequest.Status.DECLINED,
                "admin_notes": "All tents are reserved for the medical mission on that date.",
            },
            format="json",
        )
        self.assertEqual(decline_resp.status_code, status.HTTP_200_OK)
        borrow_request.refresh_from_db()
        self.assertEqual(borrow_request.status, EquipmentBorrowRequest.Status.DECLINED)
        self.assertIsNotNone(borrow_request.reviewed_at)

        reopen_resp = self.client.patch(
            reverse("equipment-request-detail", args=[borrow_request.pk]),
            {"status": EquipmentBorrowRequest.Status.APPROVED},
            format="json",
        )
        self.assertEqual(reopen_resp.status_code, status.HTTP_400_BAD_REQUEST)
