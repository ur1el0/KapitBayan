from datetime import timedelta
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from gridy_auth.models import Barangay, User
from gridy_communications.models import ActivitySchedule, Announcement, EmergencyHotline


class UnassignedCommunicationsAPITests(APITestCase):
    def setUp(self):
        self.barangay = Barangay.objects.create(name="Barangay Guadalupe")
        self.assigned_admin = User.objects.create_user(
            username="assigned_admin",
            password="SecurePassword123!",
            email="assigned_admin@example.com",
            role=User.Role.ADMIN,
            barangay=self.barangay,
            is_active=True,
        )
        self.assigned_resident = User.objects.create_user(
            username="assigned_resident",
            password="SecurePassword123!",
            email="assigned_resident@example.com",
            role=User.Role.RESIDENT,
            barangay=self.barangay,
            is_active=True,
        )
        self.unassigned_admin = User.objects.create_user(
            username="unassigned_admin",
            password="SecurePassword123!",
            email="unassigned_admin@example.com",
            role=User.Role.ADMIN,
            barangay=None,
            is_active=True,
        )
        self.unassigned_resident = User.objects.create_user(
            username="unassigned_resident",
            password="SecurePassword123!",
            email="unassigned_resident@example.com",
            role=User.Role.RESIDENT,
            barangay=None,
            is_active=True,
        )
        self.legacy_platform_user = User.objects.create_user(
            username="legacy_platform_comm",
            password="SecurePassword123!",
            email="legacy_platform_comm@example.com",
            role="BARANGAY_OPERATOR",
            barangay=None,
            is_active=True,
        )
        # Fixture created by an assigned official
        self.assigned_announcement = Announcement.objects.create(
            title="Assigned Announcement",
            content="Content for Barangay Guadalupe",
            created_by=self.assigned_admin,
        )
        self.assigned_activity = ActivitySchedule.objects.create(
            title="Assigned Activity",
            description="Activity for Barangay Guadalupe",
            event_datetime=timezone.now() + timedelta(days=3),
            location="Barangay Court",
            created_by=self.assigned_admin,
        )
        self.assigned_hotline = EmergencyHotline.objects.create(
            name="Guadalupe Desk",
            number="123-4567",
            category=EmergencyHotline.Category.BARANGAY,
            created_by=self.assigned_admin,
        )
        # Fixture created directly with null-owner tenant (unassigned creator)
        self.null_announcement = Announcement.objects.create(
            title="Null Tenant Announcement",
            content="Orphaned content without a barangay",
            created_by=self.unassigned_admin,
        )
        self.null_activity = ActivitySchedule.objects.create(
            title="Null Tenant Activity",
            description="Orphaned activity without a barangay",
            event_datetime=timezone.now() + timedelta(days=4),
            location="Unassigned Court",
            created_by=self.unassigned_admin,
        )
        self.null_hotline = EmergencyHotline.objects.create(
            name="Null Desk",
            number="000-0000",
            category=EmergencyHotline.Category.OTHER,
            created_by=self.unassigned_admin,
        )

    def test_unassigned_non_operator_users_receive_empty_communications_querysets(self):
        for unassigned_user in [self.unassigned_admin, self.unassigned_resident]:
            self.client.force_login(unassigned_user)

            for endpoint in ["announcement-list", "activity-list", "hotline-list"]:
                res = self.client.get(reverse(endpoint))
                self.assertEqual(res.status_code, status.HTTP_200_OK)
                results = res.data.get("results", res.data) if isinstance(res.data, dict) else res.data
                self.assertEqual(
                    len(results),
                    0,
                    f"Unassigned user {unassigned_user.username} received rows from {endpoint}",
                )

    def test_unassigned_admin_cannot_create_communications_records(self):
        self.client.force_login(self.unassigned_admin)

        # 1. Announcement create rejection
        ann_res = self.client.post(
            reverse("announcement-list"),
            {"title": "Blocked Announcement", "content": "Should fail"},
            format="json",
        )
        self.assertEqual(ann_res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Announcement.objects.filter(title="Blocked Announcement").exists())

        # 2. Activity schedule create rejection
        act_res = self.client.post(
            reverse("activity-list"),
            {
                "title": "Blocked Activity",
                "description": "Should fail",
                "event_datetime": (timezone.now() + timedelta(days=1)).isoformat(),
                "location": "Nowhere",
            },
            format="json",
        )
        self.assertEqual(act_res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(ActivitySchedule.objects.filter(title="Blocked Activity").exists())

        # 3. Emergency hotline create rejection
        hot_res = self.client.post(
            reverse("hotline-list"),
            {"name": "Blocked Hotline", "number": "999-9999", "category": "OTHER"},
            format="json",
        )
        self.assertEqual(hot_res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(EmergencyHotline.objects.filter(name="Blocked Hotline").exists())

    def test_legacy_platform_role_cannot_read_cross_barangay_communications(self):
        self.client.force_authenticate(user=self.legacy_platform_user)

        for endpoint in ["announcement-list", "activity-list", "hotline-list"]:
            response = self.client.get(reverse(endpoint))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            results = response.data.get("results", response.data) if isinstance(response.data, dict) else response.data
            self.assertEqual(results, [])

    def test_assigned_users_isolate_communications_to_own_barangay(self):
        other_barangay = Barangay.objects.create(name="Barangay Pinagkaisahan")
        other_admin = User.objects.create_user(
            username="other_admin",
            password="SecurePassword123!",
            email="other_admin@example.com",
            role=User.Role.ADMIN,
            barangay=other_barangay,
            is_active=True,
        )
        Announcement.objects.create(
            title="Other Barangay Announcement",
            content="Content for Pinagkaisahan",
            created_by=other_admin,
        )

        self.client.force_login(self.assigned_resident)
        res = self.client.get(reverse("announcement-list"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        results = res.data.get("results", res.data) if isinstance(res.data, dict) else res.data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], self.assigned_announcement.pk)
