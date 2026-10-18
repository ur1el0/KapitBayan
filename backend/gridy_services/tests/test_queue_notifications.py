from unittest.mock import patch

from django.urls import reverse
from rest_framework import status

from gridy_auth.models import Barangay, User
from gridy_communications.models import FCMDevice
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
        send_notification.assert_called_once()
        self.assertEqual(send_notification.call_args.kwargs["user_id"], self.resident.pk)
        self.assertEqual(send_notification.call_args.kwargs["data"]["type"], "queue")

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

    def test_page_requires_a_resident_notification_channel(self):
        self.resident.push_alerts = False
        self.resident.email_alerts = False
        self.resident.save(update_fields=["push_alerts", "email_alerts"])

        response = self.client.post(
            reverse("ticket-notify-resident", args=[self.ticket.pk]),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
