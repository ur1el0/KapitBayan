from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from django.db import close_old_connections, connections
from django.test import TransactionTestCase, skipUnlessDBFeature
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate
from gridy_auth.models import Barangay, User
from gridy_services.models import QueueTicket
from gridy_services.views.queue import QueueTicketViewSet


class QueueConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.barangay = Barangay.objects.create(
            name="Queue Concurrency Test Barangay"
        )
        self.official = User.objects.create_user(
            username="queue_concurrency_official",
            password="SecurePassword123!",
            email="queue-concurrency@example.com",
            role=User.Role.ADMIN,
            barangay=self.barangay,
        )

    @skipUnlessDBFeature("has_select_for_update")
    def test_concurrent_ticket_creation_assigns_distinct_numbers(self):
        barrier = Barrier(2)
        barangay_id = self.barangay.pk

        def create_ticket(_):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                ticket = QueueTicket.objects.create(
                    barangay_id=barangay_id,
                    service_type="DOCUMENT",
                )
                return ticket.ticket_number
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            ticket_numbers = list(executor.map(create_ticket, range(2)))

        self.assertCountEqual(ticket_numbers, ["T001", "T002"])

    @skipUnlessDBFeature("has_select_for_update")
    def test_concurrent_advances_serve_different_waiting_tickets(self):
        first_ticket = QueueTicket.objects.create(
            barangay=self.barangay,
            ticket_number="T001",
            service_type="DOCUMENT",
            status=QueueTicket.Status.WAITING,
        )
        second_ticket = QueueTicket.objects.create(
            barangay=self.barangay,
            ticket_number="T002",
            service_type="DOCUMENT",
            status=QueueTicket.Status.WAITING,
        )

        barrier = Barrier(2)
        official_id = self.official.pk
        view = QueueTicketViewSet.as_view({"post": "next_ticket"})

        def advance_queue(_):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                official = User.objects.get(pk=official_id)
                request = APIRequestFactory().post("/api/v1/tickets/next/")
                force_authenticate(request, user=official)
                response = view(request)
                return response.status_code, response.data.get("current_ticket")
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(advance_queue, range(2)))

        self.assertEqual(
            [response_status for response_status, _ in results],
            [status.HTTP_200_OK, status.HTTP_200_OK],
        )
        self.assertCountEqual(
            [ticket_number for _, ticket_number in results],
            ["T001", "T002"],
        )

        first_ticket.refresh_from_db()
        second_ticket.refresh_from_db()
        self.assertEqual(first_ticket.status, QueueTicket.Status.COMPLETED)
        self.assertEqual(second_ticket.status, QueueTicket.Status.SERVING)

    def test_next_ticket_serves_two_priority_tickets_before_regular(self):
        tickets = [
            QueueTicket.objects.create(
                barangay=self.barangay,
                ticket_number=f"R{number:03d}",
                service_type="DOCUMENT",
                is_priority=False,
                status=QueueTicket.Status.WAITING,
            )
            for number in range(1, 3)
        ]
        tickets.extend(
            QueueTicket.objects.create(
                barangay=self.barangay,
                ticket_number=f"P{number:03d}",
                service_type="DOCUMENT",
                is_priority=True,
                priority_status=QueueTicket.Priority.PRIORITY,
                status=QueueTicket.Status.WAITING,
            )
            for number in range(1, 5)
        )
        view = QueueTicketViewSet.as_view({"post": "next_ticket"})

        def advance_queue():
            request = APIRequestFactory().post("/api/v1/tickets/next/")
            force_authenticate(request, user=self.official)
            return view(request)

        served = [advance_queue().data["current_ticket"] for _ in range(6)]

        self.assertEqual(
            served,
            ["P001", "P002", "R001", "P003", "P004", "R002"],
        )

    def test_next_ticket_uses_priority_when_regular_lane_is_empty(self):
        QueueTicket.objects.create(
            barangay=self.barangay,
            ticket_number="P001",
            service_type="DOCUMENT",
            is_priority=True,
            priority_status=QueueTicket.Priority.PRIORITY,
            status=QueueTicket.Status.WAITING,
        )
        request = APIRequestFactory().post("/api/v1/tickets/next/")
        force_authenticate(request, user=self.official)

        response = QueueTicketViewSet.as_view({"post": "next_ticket"})(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["current_ticket"], "P001")

    def test_next_ticket_resets_priority_count_at_manila_day_boundary(self):
        from datetime import datetime
        from zoneinfo import ZoneInfo

        manila = ZoneInfo("Asia/Manila")
        previous_day_call = datetime(2026, 10, 8, 23, 59, tzinfo=manila)
        next_day_call = datetime(2026, 10, 9, 0, 1, tzinfo=manila)
        previous_day_ticket = QueueTicket.objects.create(
            barangay=self.barangay,
            ticket_number="R000",
            service_type="DOCUMENT",
            is_priority=False,
            status=QueueTicket.Status.COMPLETED,
            called_at=previous_day_call,
        )
        QueueTicket.objects.filter(pk=previous_day_ticket.pk).update(
            created_at=previous_day_call
        )
        regular_ticket = QueueTicket.objects.create(
            barangay=self.barangay,
            ticket_number="R001",
            service_type="DOCUMENT",
            is_priority=False,
            status=QueueTicket.Status.WAITING,
        )
        QueueTicket.objects.filter(pk=regular_ticket.pk).update(
            created_at=next_day_call
        )
        priority_ticket = QueueTicket.objects.create(
            barangay=self.barangay,
            ticket_number="P001",
            service_type="DOCUMENT",
            is_priority=True,
            priority_status=QueueTicket.Priority.PRIORITY,
            status=QueueTicket.Status.WAITING,
        )
        QueueTicket.objects.filter(pk=priority_ticket.pk).update(
            created_at=next_day_call
        )
        request = APIRequestFactory().post("/api/v1/tickets/next/")
        force_authenticate(request, user=self.official)

        with patch(
            "gridy_services.views.queue.timezone.now",
            return_value=next_day_call,
        ):
            response = QueueTicketViewSet.as_view(
                {"post": "next_ticket"}
            )(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["current_ticket"], "P001")
