from datetime import datetime, time, timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from gridy_audit.models import AuditLog
from gridy_audit.services import log_action
from gridy_auth.models import Barangay, User
from gridy_auth.permissions import IsBarangayOfficial, IsBarangayOfficialOrField
from gridy_communications.models import ResidentNotification
from gridy_communications.tasks import send_notification_to_user_task
from gridy_services.models import MANILA_TIME_ZONE, QueueTicket
from gridy_services.serializers import (
    QueueTicketPrioritySerializer,
    QueueTicketSerializer,
)
from .dashboard import DashboardSummaryView

__all__ = ["QueueTicketViewSet", "DashboardSummaryView"]

class QueueTicketViewSet(viewsets.ModelViewSet):
    serializer_class = QueueTicketSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'create', 'live_status', 'cancel_ticket']:
            return [permissions.IsAuthenticated()]
        if self.action == 'set_priority':
            return [IsBarangayOfficial()]
        return [IsBarangayOfficialOrField()]

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return QueueTicket.objects.none()

        if user.role in [User.Role.ADMIN, User.Role.FIELD_OFFICIAL]:
            return QueueTicket.objects.filter(barangay=user.barangay).order_by('-created_at')

        return QueueTicket.objects.filter(user=user).order_by('-created_at')

    def perform_create(self, serializer):
        user = self.request.user
        if not user or not user.is_authenticated:
            raise PermissionDenied("Authentication required to generate queue tickets.")

        if (
            user.role in (User.Role.ADMIN, User.Role.RESIDENT)
            and user.barangay_id is None
        ):
            raise PermissionDenied(
                "A barangay assignment is required to generate queue tickets."
            )

        priority_reason = serializer.validated_data.get('priority_reason')
        with transaction.atomic():
            if user.role == User.Role.ADMIN:
                ticket = serializer.save(user=None, barangay=user.barangay)
            elif user.role == User.Role.RESIDENT:
                ticket = serializer.save(
                    user=user,
                    barangay=user.barangay,
                    priority_status=QueueTicket.Priority.REGULAR,
                    is_priority=False,
                )
            else:
                raise PermissionDenied(
                    "Field officials cannot generate queue tickets."
                )

            if ticket.is_priority:
                log_action(
                    user=user,
                    action_type=AuditLog.ActionType.QUEUE_ACTION,
                    description=(
                        f"Official {user.username} issued priority queue ticket "
                        f"{ticket.ticket_number} (ID: {ticket.id}) in "
                        f"{ticket.barangay.name}. Reason: {priority_reason}"
                    ),
                    request=self.request,
                )

    def perform_update(self, serializer):
        serializer.save()

    @staticmethod
    def _has_notification_channel(user):
        has_email = bool(user.email_alerts and user.email)
        has_push = bool(user.push_alerts and user.fcm_devices.exists())
        return has_email or has_push

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[IsBarangayOfficialOrField],
        url_path='notify',
    )
    def notify_resident(self, request, pk=None):
        official = request.user
        if official.barangay_id is None:
            raise PermissionDenied(
                "A barangay assignment is required to page a resident."
            )

        ticket = self.get_object()
        if ticket.status != QueueTicket.Status.SERVING:
            return Response(
                {"detail": "Only the currently serving ticket can be paged."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if ticket.user_id is None or ticket.user.role != User.Role.RESIDENT:
            return Response(
                {"detail": "This ticket is not linked to a resident account."},
                status=status.HTTP_409_CONFLICT,
            )
        ticket_id = ticket.pk
        resident_id = ticket.user_id
        ticket_number = ticket.ticket_number
        message = (
            f"Your ticket {ticket_number} is still being served. "
            "Please proceed to the service counter."
        )
        notification = ResidentNotification.objects.create(
            user=ticket.user,
            notification_type=ResidentNotification.Type.QUEUE,
            title=f"Queue ticket {ticket_number} is still being served",
            message=message,
            data={
                "type": "queue",
                "ticket_id": str(ticket_id),
                "ticket_number": ticket_number,
            },
        )
        log_action(
            user=official,
            action_type=AuditLog.ActionType.QUEUE_ACTION,
            description=(
                f"Paged the resident linked to ticket {ticket_number} "
                f"(ID: {ticket_id})."
            ),
            request=request,
        )
        transaction.on_commit(
            lambda: send_notification_to_user_task.delay(
                user_id=resident_id,
                title="Queue Paging Alert",
                body=message,
                data={"type": "queue", "ticket_id": str(ticket_id)},
            )
        )
        return Response(
            {
                "detail": (
                    "Paging alert saved for the resident. Push and email delivery "
                    "are attempted when enabled in the resident's preferences."
                ),
                "ticket_number": ticket_number,
                "notification_id": notification.pk,
            },
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated], url_path='cancel')
    def cancel_ticket(self, request, pk=None):
        user = request.user

        if user.role not in (
            User.Role.RESIDENT,
            User.Role.ADMIN,
            User.Role.FIELD_OFFICIAL,
        ):
            raise PermissionDenied("You are not allowed to cancel queue tickets.")

        if user.barangay_id is None:
            raise PermissionDenied(
                "A barangay assignment is required to cancel queue tickets."
            )

        with transaction.atomic():
            Barangay.objects.select_for_update().get(pk=user.barangay_id)
            ticket = self.get_object()

            if user.role == User.Role.RESIDENT and ticket.user_id != user.id:
                raise PermissionDenied(
                    "You can only cancel your own queue tickets."
                )

            if ticket.status != QueueTicket.Status.WAITING:
                return Response(
                    {"detail": "Only tickets currently in queue can be cancelled."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            ticket.status = QueueTicket.Status.CANCELLED
            ticket.save()

            actor_desc = (
                f"Resident {user.username}"
                if user.role == User.Role.RESIDENT
                else f"Official {user.username}"
            )
            log_action(
                user=user,
                action_type=AuditLog.ActionType.QUEUE_ACTION,
                description=(
                    f"{actor_desc} cancelled queue ticket "
                    f"{ticket.ticket_number} (ID: {ticket.id})."
                ),
                request=request,
            )

        return Response(
            {
                "detail": "Queue ticket cancelled successfully.",
                "ticket_number": ticket.ticket_number,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=['get'], url_path='live-status')
    def live_status(self, request):
        user = request.user
        if not user or not user.is_authenticated or not user.barangay_id:
            return Response({
                "current_ticket": None,
                "total_waiting": 0,
                "avg_wait_mins": 0,
            }, status=status.HTTP_200_OK)

        serving_ticket = QueueTicket.objects.filter(
            barangay_id=user.barangay_id,
            status=QueueTicket.Status.SERVING,
        ).first()
        total_waiting = QueueTicket.objects.filter(
            barangay_id=user.barangay_id,
            status=QueueTicket.Status.WAITING,
        ).count()

        return Response({
            "current_ticket": serving_ticket.ticket_number if serving_ticket else None,
            "total_waiting": total_waiting,
            "avg_wait_mins": total_waiting * 2,
        }, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[IsBarangayOfficialOrField],
        url_path='complete',
    )
    def complete_ticket(self, request, pk=None):
        user = request.user

        if user.barangay_id is None:
            raise PermissionDenied(
                "A barangay assignment is required to complete queue tickets."
            )

        with transaction.atomic():
            Barangay.objects.select_for_update().get(pk=user.barangay_id)
            ticket = self.get_object()

            if ticket.status != QueueTicket.Status.SERVING:
                return Response(
                    {"detail": "Only the serving ticket can be completed."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            ticket.status = QueueTicket.Status.COMPLETED
            ticket.save(update_fields=["status", "updated_at"])

            log_action(
                user=user,
                action_type=AuditLog.ActionType.QUEUE_ACTION,
                description=(
                    f"Official {user.username} completed queue ticket "
                    f"{ticket.ticket_number} (ID: {ticket.id})."
                ),
                request=request,
            )

        return Response(
            {
                "detail": "Queue ticket completed successfully.",
                "ticket_number": ticket.ticket_number,
                "status": ticket.status,
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(request=QueueTicketPrioritySerializer)
    @action(
        detail=True,
        methods=['post'],
        permission_classes=[IsBarangayOfficial],
        url_path='priority',
    )
    def set_priority(self, request, pk=None):
        user = request.user
        if user.barangay_id is None:
            raise PermissionDenied(
                "A barangay assignment is required to change queue priority."
            )

        serializer = QueueTicketPrioritySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_priority_status = serializer.validated_data['priority_status']
        reason = serializer.validated_data['reason']

        with transaction.atomic():
            Barangay.objects.select_for_update().get(pk=user.barangay_id)
            ticket = self.get_object()

            if ticket.status != QueueTicket.Status.WAITING:
                return Response(
                    {"detail": "Priority can only be changed for waiting tickets."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            previous_priority_status = ticket.priority_status
            if previous_priority_status == new_priority_status:
                return Response(
                    {
                        "detail": "Ticket already has the requested priority status.",
                        "priority_status": ticket.priority_status,
                        "is_priority": ticket.is_priority,
                    },
                    status=status.HTTP_200_OK,
                )

            ticket.priority_status = new_priority_status
            ticket.is_priority = (
                new_priority_status == QueueTicket.Priority.PRIORITY
            )
            ticket.save(
                update_fields=["priority_status", "is_priority", "updated_at"]
            )

            log_action(
                user=user,
                action_type=AuditLog.ActionType.QUEUE_ACTION,
                description=(
                    f"Official {user.username} changed queue ticket "
                    f"{ticket.ticket_number} (ID: {ticket.id}) in "
                    f"{ticket.barangay.name} priority from "
                    f"{previous_priority_status} to {new_priority_status}. "
                    f"Reason: {reason}"
                ),
                request=request,
            )

        return Response(
            {
                "detail": "Queue ticket priority updated successfully.",
                "ticket_number": ticket.ticket_number,
                "priority_status": ticket.priority_status,
                "is_priority": ticket.is_priority,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=['post'], permission_classes=[IsBarangayOfficialOrField], url_path='next')
    def next_ticket(self, request):
        user = request.user

        if user.barangay_id is None:
            raise PermissionDenied(
                "A barangay assignment is required to advance the queue."
            )

        with transaction.atomic():
            Barangay.objects.select_for_update().get(pk=user.barangay_id)
            now = timezone.now()
            local_today = timezone.localtime(now, MANILA_TIME_ZONE).date()
            day_start = datetime.combine(
                local_today,
                time.min,
                tzinfo=MANILA_TIME_ZONE,
            )
            next_day_start = day_start + timedelta(days=1)

            QueueTicket.objects.filter(
                barangay_id=user.barangay_id,
                status=QueueTicket.Status.SERVING,
                called_at__isnull=True,
            ).update(called_at=now)
            QueueTicket.objects.filter(
                barangay_id=user.barangay_id,
                status=QueueTicket.Status.SERVING,
            ).update(status=QueueTicket.Status.COMPLETED, updated_at=now)

            served_today = QueueTicket.objects.filter(
                barangay_id=user.barangay_id,
                status__in=(
                    QueueTicket.Status.COMPLETED,
                    QueueTicket.Status.SERVING,
                ),
                called_at__gte=day_start,
                called_at__lt=next_day_start,
            )
            last_regular_call = (
                served_today.filter(is_priority=False)
                .order_by("-called_at", "-id")
                .values("called_at", "id")
                .first()
            )
            priority_calls_since_regular = served_today.filter(is_priority=True)
            if last_regular_call:
                priority_calls_since_regular = priority_calls_since_regular.filter(
                    Q(called_at__gt=last_regular_call["called_at"])
                    | Q(
                        called_at=last_regular_call["called_at"],
                        id__gt=last_regular_call["id"],
                    )
                )

            regular_ticket = (
                QueueTicket.objects.filter(
                    barangay_id=user.barangay_id,
                    status=QueueTicket.Status.WAITING,
                    is_priority=False,
                )
                .order_by("created_at", "id")
                .first()
            )
            priority_ticket = (
                QueueTicket.objects.filter(
                    barangay_id=user.barangay_id,
                    status=QueueTicket.Status.WAITING,
                    is_priority=True,
                )
                .order_by("created_at", "id")
                .first()
            )

            if regular_ticket and priority_ticket:
                next_ticket = (
                    regular_ticket
                    if priority_calls_since_regular.count() >= 2
                    else priority_ticket
                )
            else:
                next_ticket = regular_ticket or priority_ticket

            if not next_ticket:
                return Response(
                    {"detail": "No tickets waiting in queue."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            next_ticket.status = QueueTicket.Status.SERVING
            next_ticket.called_at = now
            next_ticket.save(
                update_fields=["status", "called_at", "updated_at"]
            )

            log_action(
                user=user,
                action_type=AuditLog.ActionType.QUEUE_ACTION,
                description=(
                    f"Advanced queue to ticket {next_ticket.ticket_number} "
                    f"(ID: {next_ticket.id})."
                ),
                request=request,
            )

            if (
                next_ticket.user_id is not None
                and self._has_notification_channel(next_ticket.user)
            ):
                user_id = next_ticket.user_id
                ticket_id = next_ticket.id
                ticket_number = next_ticket.ticket_number

                transaction.on_commit(
                    lambda: send_notification_to_user_task.delay(
                        user_id=user_id,
                        title="Queue Update",
                        body=(
                            f"Your ticket {ticket_number} is now being served!"
                        ),
                        data={"type": "queue", "ticket_id": str(ticket_id)},
                        # Typed payload lets the mobile client open the queue.
                        # Keep ticket details out of the notification body.
                    )
                )

            remaining_waiting = QueueTicket.objects.filter(
                barangay_id=user.barangay_id,
                status=QueueTicket.Status.WAITING,
            ).count()

            response_data = {
                "current_ticket": next_ticket.ticket_number,
                "remaining_waiting": remaining_waiting,
            }

        return Response(response_data, status=status.HTTP_200_OK)
