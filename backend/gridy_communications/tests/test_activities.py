from datetime import timedelta
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from gridy_auth.models import Barangay, User
from gridy_communications.models import ActivitySchedule


class ActivityScheduleAPITests(APITestCase):
    def setUp(self):
        self.barangay = Barangay.objects.create(name="Activity Test Barangay")
        self.admin = User.objects._create_user(
            username="admin_official",
            password="SecurePassword123!",
            email="admin_official@example.com",
            role=User.Role.ADMIN,
            barangay=self.barangay,
            is_active=True
        )
        self.resident = User.objects._create_user(
            username="resident_juan",
            password="SecurePassword123!",
            email="resident_juan@example.com",
            role=User.Role.RESIDENT,
            barangay=self.barangay,
            is_active=True
        )
        self.list_url = reverse('activity-list')

    def test_resident_can_view_activities_but_cannot_create(self):
        # 1. Admin creates an activity
        ActivitySchedule.objects.create(
            title="Clean-Up Drive",
            description="Community cleanup along Main Street.",
            event_datetime=timezone.now() + timedelta(days=2),
            location="Main Street Covered Court",
            created_by=self.admin
        )

        # 2. Resident logs in and lists activities -> 200 OK
        self.client.force_login(self.resident)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        results = data.get('results', data) if isinstance(data, dict) else data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], "Clean-Up Drive")

        # 3. Resident attempts to schedule an activity -> 403 Forbidden
        payload = {
            "title": "Unauthorized Party",
            "description": "Resident trying to create official event.",
            "event_datetime": (timezone.now() + timedelta(days=1)).isoformat(),
            "location": "Plaza"
        }
        post_response = self.client.post(self.list_url, payload, format='json')
        self.assertEqual(post_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_official_can_create_and_delete_activity(self):
        self.client.force_login(self.admin)
        payload = {
            "title": "Barangay Assembly",
            "description": "Quarterly financial report and discussion.",
            "event_datetime": (timezone.now() + timedelta(days=5)).isoformat(),
            "location": "Barangay Hall"
        }
        create_res = self.client.post(self.list_url, payload, format='json')
        self.assertEqual(create_res.status_code, status.HTTP_201_CREATED)
        activity_id = create_res.json()['id']

        # Official deletes activity -> 204 No Content
        detail_url = reverse('activity-detail', kwargs={'pk': activity_id})
        delete_res = self.client.delete(detail_url)
        self.assertEqual(delete_res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ActivitySchedule.objects.filter(id=activity_id).exists())

    def test_official_cannot_schedule_past_date_or_past_same_day_time(self):
        self.client.force_login(self.admin)

        one_hour_ago = (timezone.now() - timedelta(hours=1)).isoformat()
        same_day_past = self.client.post(
            self.list_url,
            {
                "title": "Past Same Day Event",
                "description": "Attempted to schedule one hour in the past.",
                "event_datetime": one_hour_ago,
                "location": "Barangay Hall",
            },
            format="json",
        )
        self.assertEqual(same_day_past.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("event_datetime", same_day_past.data)

        two_days_ago = (timezone.now() - timedelta(days=2)).isoformat()
        past_day = self.client.post(
            self.list_url,
            {
                "title": "Past Day Event",
                "description": "Attempted to schedule on a previous day.",
                "event_datetime": two_days_ago,
                "location": "Covered Court",
            },
            format="json",
        )
        self.assertEqual(past_day.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("event_datetime", past_day.data)
        self.assertEqual(ActivitySchedule.objects.count(), 0)

        # Updating an existing past activity's title keeps working unless datetime is moved to another past time
        existing = ActivitySchedule.objects.create(
            title="Past Event Record",
            description="Already happened.",
            event_datetime=timezone.now() - timedelta(days=3),
            location="Plaza",
            created_by=self.admin,
        )
        detail_url = reverse("activity-detail", kwargs={"pk": existing.pk})
        patch_title = self.client.patch(detail_url, {"title": "Past Event Updated"}, format="json")
        self.assertEqual(patch_title.status_code, status.HTTP_200_OK)

        patch_past_dt = self.client.patch(detail_url, {"event_datetime": one_hour_ago}, format="json")
        self.assertEqual(patch_past_dt.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("event_datetime", patch_past_dt.data)
