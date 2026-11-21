from unittest.mock import AsyncMock, MagicMock, patch

from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APITransactionTestCase

from config.asgi import application
from gridy_auth.models import Barangay, User
from gridy_services.models import QueueTicket
from gridy_services.websocket_events import (
    async_broadcast_queue_update,
    broadcast_queue_update,
)


class PublicQueueStatusAPITests(APITestCase):
    def setUp(self):
        self.barangay_a = Barangay.objects.create(
            name="Public Queue Barangay A",
            primary_color="#123456",
        )
        self.barangay_b = Barangay.objects.create(
            name="Public Queue Barangay B",
            primary_color="#654321",
        )

        QueueTicket.objects.create(
            barangay=self.barangay_a,
            ticket_number="A-101",
            service_type="DOCUMENT",
            status=QueueTicket.Status.SERVING,
        )
        QueueTicket.objects.create(
            barangay=self.barangay_a,
            ticket_number="A-102",
            service_type="DOCUMENT",
            status=QueueTicket.Status.WAITING,
        )
        QueueTicket.objects.create(
            barangay=self.barangay_b,
            ticket_number="B-201",
            service_type="DOCUMENT",
            status=QueueTicket.Status.SERVING,
        )
        QueueTicket.objects.create(
            barangay=self.barangay_b,
            ticket_number="B-202",
            service_type="DOCUMENT",
            status=QueueTicket.Status.WAITING,
        )

    def test_anonymous_status_is_scoped_to_requested_barangay(self):
        url = reverse(
            "public-queue-status",
            kwargs={"barangay_id": self.barangay_a.pk},
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {
                "barangay_name": "Public Queue Barangay A",
                "primary_color": "#123456",
                "current_ticket": "A-101",
                "total_waiting": 1,
            },
        )

    def test_unknown_barangay_returns_not_found(self):
        url = reverse(
            "public-queue-status",
            kwargs={"barangay_id": 999999},
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_existing_live_status_endpoint_still_requires_authentication(self):
        response = self.client.get(reverse("ticket-live-status"))

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_live_status_for_user_without_barangay_returns_empty_summary_and_ignores_null_tickets(self):
        # Create legacy tickets with null barangay
        QueueTicket.objects.create(
            ticket_number="NULL-001",
            status=QueueTicket.Status.SERVING,
            barangay=None,
        )
        QueueTicket.objects.create(
            ticket_number="NULL-002",
            status=QueueTicket.Status.WAITING,
            barangay=None,
        )
        unassigned_user = User.objects.create_user(
            username="unassigned_queue_user",
            password="SecurePassword123!",
            email="unassigned_queue@example.com",
            role=User.Role.RESIDENT,
            barangay=None,
            is_active=True,
        )
        self.client.force_login(unassigned_user)
        response = self.client.get(reverse("ticket-live-status"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {
                "current_ticket": None,
                "total_waiting": 0,
                "avg_wait_mins": 0,
            },
        )

    def test_live_status_isolates_assigned_barangay_and_ignores_other_barangays(self):
        barangay_a = Barangay.objects.create(name="Barangay Alpha")
        barangay_b = Barangay.objects.create(name="Barangay Beta")

        QueueTicket.objects.create(
            ticket_number="A-001",
            status=QueueTicket.Status.SERVING,
            barangay=barangay_a,
        )
        QueueTicket.objects.create(
            ticket_number="A-002",
            status=QueueTicket.Status.WAITING,
            barangay=barangay_a,
        )
        QueueTicket.objects.create(
            ticket_number="A-003",
            status=QueueTicket.Status.WAITING,
            barangay=barangay_a,
        )

        QueueTicket.objects.create(
            ticket_number="B-001",
            status=QueueTicket.Status.SERVING,
            barangay=barangay_b,
        )
        QueueTicket.objects.create(
            ticket_number="B-002",
            status=QueueTicket.Status.WAITING,
            barangay=barangay_b,
        )

        user_a = User.objects.create_user(
            username="user_alpha",
            password="SecurePassword123!",
            email="user_alpha@example.com",
            role=User.Role.RESIDENT,
            barangay=barangay_a,
            is_active=True,
        )
        self.client.force_login(user_a)
        response = self.client.get(reverse("ticket-live-status"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["current_ticket"], "A-001")
        self.assertEqual(response.data["total_waiting"], 2)
        self.assertEqual(response.data["avg_wait_mins"], 4)


class QueueWebSocketIsolationSecurityTests(APITransactionTestCase):
    def setUp(self):
        self.barangay_a = Barangay.objects.create(name="WS Security Barangay A")
        self.barangay_b = Barangay.objects.create(name="WS Security Barangay B")

    def test_broadcast_dispatches_only_to_barangay_group_never_global_room(self):
        fake_layer = MagicMock()
        fake_layer.group_send = AsyncMock()

        with patch(
            "gridy_services.websocket_events.get_channel_layer",
            return_value=fake_layer,
        ):
            broadcast_queue_update(
                barangay_id=self.barangay_a.id,
                ticket="A-101",
                action="call_next",
            )
            async_to_sync(async_broadcast_queue_update)(
                barangay_id=self.barangay_a.id,
                ticket="A-102",
                action="create",
            )

        sent_groups = [call.args[0] for call in fake_layer.group_send.await_args_list]
        self.assertEqual(
            sent_groups,
            [f"queue_{self.barangay_a.id}", f"queue_{self.barangay_a.id}"],
        )
        self.assertNotIn("queue_updates", sent_groups)

        fake_layer.group_send.reset_mock()
        with patch(
            "gridy_services.websocket_events.get_channel_layer",
            return_value=fake_layer,
        ):
            broadcast_queue_update(barangay_id=None, ticket="NONE-1", action="create")
            async_to_sync(async_broadcast_queue_update)(
                barangay_id=None,
                ticket="NONE-2",
                action="create",
            )
        fake_layer.group_send.assert_not_called()

    def test_websocket_routes_reject_unscoped_or_unknown_and_isolate_tenants(self):
        headers = [(b"origin", b"http://localhost")]

        async def _exercise():
            unscoped = WebsocketCommunicator(application, "/ws/queue/", headers=headers)
            with self.assertRaises(ValueError):
                await unscoped.connect()

            unknown = WebsocketCommunicator(
                application,
                "/ws/queue/999999/",
                headers=headers,
            )
            connected_unknown, close_code = await unknown.connect()
            self.assertFalse(connected_unknown)
            self.assertEqual(close_code, 4004)

            client_a = WebsocketCommunicator(
                application,
                f"/ws/queue/{self.barangay_a.id}/",
                headers=headers,
            )
            client_b = WebsocketCommunicator(
                application,
                f"/ws/queue/{self.barangay_b.id}/",
                headers=headers,
            )
            connected_a, _ = await client_a.connect()
            connected_b, _ = await client_b.connect()
            self.assertTrue(connected_a)
            self.assertTrue(connected_b)

            await async_broadcast_queue_update(
                barangay_id=self.barangay_a.id,
                ticket="SEC-001",
                action="call_next",
            )
            msg_a = await client_a.receive_json_from(timeout=2)
            self.assertEqual(msg_a["ticket"], "SEC-001")
            self.assertTrue(await client_b.receive_nothing(timeout=0.2))

            await client_a.disconnect()
            await client_b.disconnect()

        async_to_sync(_exercise)()
