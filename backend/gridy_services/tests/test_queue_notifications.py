from unittest.mock import patch

from django.urls import reverse
from rest_framework import status

from gridy_auth.models import Barangay, User
from gridy_communications.models import FCMDevice, ResidentNotification
from gridy_services.models import QueueTicket
from .base import ServiceAPIBaseTestCase


class QueueResidentNotificationAPITests(ServiceAPIBaseTestCase):
    def setUp(self):
        super().setUp()
        self.barangay = Barangay.objects.create(name="Queue Paging Barangay")
        self.official = User.objects.create_user(
            username="paging_admin",
            password="SecurePassword123!",
            email="paging-admin@example.com",
            role=User.Role.ADMIN,
            barangay=self.barangay,
        )
        self.resident.barangay = self.barangay
        self.resident.push_alerts = True
        self.resident.email_alerts = False
        self.resident.save(update_fields=["barangay", "push_alerts", "email_alerts"])
        FCMDevice.objects.create(user=self.resident, token="resident-device-token")
        self.ticket = QueueTicket.objects.create(
            barangay=self.barangay,
            user=self.resident,
            ticket_number="P-001",
            service_type="DOCUMENT",
            status=QueueTicket.Status.SERVING,
        )
        self.client.force_authenticate(user=self.official)

    @patch("gridy_services.views.queue.send_notification_to_user_task.delay")
    def test_barangay_official_can_page_current_resident(self, send_notification):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("ticket-notify-resident", args=[self.ticket.pk]),
                {},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data["ticket_number"], self.ticket.ticket_number)
        self.assertEqual(response.data["notification_id"], ResidentNotification.objects.get().pk)
        send_notification.assert_called_once()
        self.assertEqual(send_notification.call_args.kwargs["user_id"], self.resident.pk)
        self.assertEqual(send_notification.call_args.kwargs["data"]["type"], "queue")
        notification = ResidentNotification.objects.get(user=self.resident)
        self.assertEqual(notification.notification_type, ResidentNotification.Type.QUEUE)
        self.assertIn(self.ticket.ticket_number, notification.title)
        self.assertIn("service counter", notification.message)
        self.assertEqual(notification.data["ticket_id"], str(self.ticket.pk))

    def test_official_cannot_page_ticket_in_another_barangay(self):
        other_barangay = Barangay.objects.create(name="Other Queue Barangay")
        other_ticket = QueueTicket.objects.create(
            barangay=other_barangay,
            user=self.resident,
            ticket_number="P-002",
            service_type="DOCUMENT",
            status=QueueTicket.Status.SERVING,
        )

        response = self.client.post(
            reverse("ticket-notify-resident", args=[other_ticket.pk]),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_only_a_serving_ticket_can_be_paged(self):
        self.ticket.status = QueueTicket.Status.WAITING
        self.ticket.save(update_fields=["status"])

        response = self.client.post(
            reverse("ticket-notify-resident", args=[self.ticket.pk]),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(ResidentNotification.objects.exists())

    @patch("gridy_services.views.queue.send_notification_to_user_task.delay")
    def test_page_is_saved_in_app_even_without_external_notification_channels(self, send_notification):
        self.resident.push_alerts = False
        self.resident.email_alerts = False
        self.resident.save(update_fields=["push_alerts", "email_alerts"])

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("ticket-notify-resident", args=[self.ticket.pk]),
                {},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertTrue(ResidentNotification.objects.filter(user=self.resident).exists())
        send_notification.assert_called_once()

    def test_page_rejects_tickets_linked_to_nonresident_accounts(self):
        field_official = User.objects.create_user(
            username="paging_field_official",
            password="SecurePassword123!",
            role=User.Role.FIELD_OFFICIAL,
            barangay=self.barangay,
        )
        self.ticket.user = field_official
        self.ticket.save(update_fields=["user"])

        response = self.client.post(
            reverse("ticket-notify-resident", args=[self.ticket.pk]),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertFalse(ResidentNotification.objects.exists())
