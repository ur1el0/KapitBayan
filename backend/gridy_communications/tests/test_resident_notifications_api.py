from django.urls import reverse
from rest_framework import status

from gridy_auth.models import User
from gridy_communications.models import ResidentNotification
from gridy_services.tests.base import ServiceAPIBaseTestCase


class ResidentNotificationAPITests(ServiceAPIBaseTestCase):
    def setUp(self):
        super().setUp()
        self.notification = ResidentNotification.objects.create(
            user=self.resident,
            notification_type=ResidentNotification.Type.QUEUE,
            title="Queue ticket T-014 is still being served",
            message="Please proceed to the service counter.",
            data={"type": "queue", "ticket_id": "14"},
        )

    def test_resident_can_list_only_their_own_notifications(self):
        other_resident = User.objects.create_user(
            username="other_resident_notifications",
            password="SecurePassword123!",
            email="other-notifications@example.com",
            role=User.Role.RESIDENT,
        )
        ResidentNotification.objects.create(
            user=other_resident,
            title="Private queue alert",
            message="Private message",
        )

        self.client.force_authenticate(user=self.resident)
        response = self.client.get(reverse("resident-notification-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if isinstance(response.data, dict) else response.data
        self.assertEqual([item["id"] for item in results], [self.notification.pk])
        self.assertEqual(results[0]["data"]["ticket_id"], "14")

    def test_other_authenticated_user_cannot_read_notification(self):
        other_resident = User.objects.create_user(
            username="another_resident_notifications",
            password="SecurePassword123!",
            email="another-notifications@example.com",
            role=User.Role.RESIDENT,
        )
        self.client.force_authenticate(user=other_resident)

        response = self.client.get(reverse("resident-notification-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if isinstance(response.data, dict) else response.data
        self.assertEqual(results, [])

    def test_residents_can_mark_their_own_notification_read_but_cannot_edit_content(self):
        self.client.force_authenticate(user=self.resident)

        create_response = self.client.post(
            reverse("resident-notification-list"),
            {"title": "Forged alert", "message": "Forged content"},
            format="json",
        )
        update_response = self.client.patch(
            reverse("resident-notification-detail", args=[self.notification.pk]),
            {"is_read": True, "message": "Changed content"},
            format="json",
        )

        self.assertEqual(create_response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.notification.refresh_from_db()
        self.assertTrue(self.notification.is_read)
        self.assertEqual(self.notification.message, "Please proceed to the service counter.")

    def test_resident_cannot_mark_another_users_notification_read(self):
        other_resident = User.objects.create_user(
            username="private_notification_owner",
            password="SecurePassword123!",
            email="private-notification-owner@example.com",
            role=User.Role.RESIDENT,
        )
        private_notification = ResidentNotification.objects.create(
            user=other_resident,
            title="Private alert",
            message="Do not expose this alert.",
        )
        self.client.force_authenticate(user=self.resident)

        response = self.client.patch(
            reverse("resident-notification-detail", args=[private_notification.pk]),
            {"is_read": True},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        private_notification.refresh_from_db()
        self.assertFalse(private_notification.is_read)
