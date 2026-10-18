from unittest.mock import patch

from django.test import TestCase
from firebase_admin import messaging

from gridy_auth.models import Barangay, User
from gridy_communications.models import FCMDevice
from gridy_communications.services import (
    send_email_notification_to_user,
    send_notification_to_user,
)
from gridy_communications.tasks import send_announcement_notification_task


class NotificationPreferenceDeliveryTests(TestCase):
    def setUp(self):
        self.barangay = Barangay.objects.create(name="Notification Test Barangay")
        self.user = User.objects.create_user(
            username="notify_resident",
            password="SecurePassword123!",
            email="resident@example.com",
            role=User.Role.RESIDENT,
            barangay=self.barangay,
            email_alerts=False,
            push_alerts=True,
        )
        self.device = FCMDevice.objects.create(
            user=self.user,
            token="notification-device-token",
        )

    @patch("gridy_communications.services.send_fcm_notification", return_value="message-id")
    def test_push_delivery_requires_opt_in_and_registered_device(self, send_fcm):
        responses = send_notification_to_user(self.user, "Queue update", "Please proceed.")

        self.assertEqual(responses, ["message-id"])
        send_fcm.assert_called_once_with(
            self.device,
            "Queue update",
            "Please proceed.",
            None,
        )

        self.user.push_alerts = False
        self.user.save(update_fields=["push_alerts"])
        send_fcm.reset_mock()

        self.assertEqual(
            send_notification_to_user(self.user, "Queue update", "Please proceed."),
            [],
        )
        send_fcm.assert_not_called()

    @patch("gridy_communications.services.messaging.send")
    def test_unregistered_device_is_removed_and_other_devices_are_still_sent(self, send):
        other_device = FCMDevice.objects.create(
            user=self.user,
            token="second-notification-device-token",
        )

        def send_to_device(message):
            if message.token == self.device.token:
                raise messaging.UnregisteredError("Token is no longer registered")
            return "other-device-message-id"

        send.side_effect = send_to_device

        responses = send_notification_to_user(self.user, "Queue update", "Please proceed.")

        self.assertEqual(responses, ["other-device-message-id"])
        self.assertFalse(FCMDevice.objects.filter(pk=self.device.pk).exists())
        self.assertTrue(FCMDevice.objects.filter(pk=other_device.pk).exists())
        self.assertEqual(send.call_count, 2)

    @patch("firebase_admin.get_app")
    @patch("gridy_communications.services.messaging.send")
    def test_sender_mismatch_logs_server_project_without_removing_device(
        self,
        send,
        get_firebase_app,
    ):
        get_firebase_app.return_value.project_id = "device-streaming-aca41bd3"
        send.side_effect = messaging.SenderIdMismatchError("Wrong sender")

        with self.assertLogs("gridy_communications.services", level="ERROR") as logs:
            responses = send_notification_to_user(
                self.user,
                "Queue update",
                "Please proceed.",
            )

        self.assertEqual(responses, [])
        self.assertTrue(FCMDevice.objects.filter(pk=self.device.pk).exists())
        self.assertTrue(
            any("server_project=device-streaming-aca41bd3" in line for line in logs.output)
        )

    @patch("gridy_communications.services.send_mail", return_value=1)
    def test_email_delivery_requires_opt_in_and_address(self, send_mail):
        self.user.email_alerts = True
        self.user.save(update_fields=["email_alerts"])

        self.assertTrue(
            send_email_notification_to_user(self.user, "Queue update", "Please proceed.")
        )
        send_mail.assert_called_once()
        self.assertEqual(send_mail.call_args.args[3], [self.user.email])

        self.user.email_alerts = False
        self.user.save(update_fields=["email_alerts"])
        send_mail.reset_mock()

        self.assertFalse(
            send_email_notification_to_user(self.user, "Queue update", "Please proceed.")
        )
        send_mail.assert_not_called()

    @patch("gridy_communications.tasks.send_notification_to_user")
    def test_announcement_fanout_targets_only_opted_in_residents_in_barangay(
        self,
        send_notification,
    ):
        other_barangay = Barangay.objects.create(name="Different Notification Barangay")
        other_resident = User.objects.create_user(
            username="other_notify_resident",
            password="SecurePassword123!",
            role=User.Role.RESIDENT,
            barangay=other_barangay,
            push_alerts=True,
        )
        User.objects.create_user(
            username="opted_out_resident",
            password="SecurePassword123!",
            role=User.Role.RESIDENT,
            barangay=self.barangay,
            push_alerts=False,
        )

        send_announcement_notification_task.__wrapped__(
            self.barangay.pk,
            42,
            "Office hours update",
        )

        send_notification.assert_called_once()
        self.assertEqual(send_notification.call_args.args[0].pk, self.user.pk)
        self.assertNotEqual(send_notification.call_args.args[0].pk, other_resident.pk)
        self.assertEqual(
            send_notification.call_args.kwargs["data"],
            {"type": "announcement", "announcement_id": "42"},
        )
