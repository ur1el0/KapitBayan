from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from gridy_auth.models import Barangay
from gridy_services.models import QueueTicket, manila_day_bounds
from gridy_services.serializers import PublicQueueStatusSerializer

class PublicQueueStatusView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Get public queue status for one barangay",
        description=(
            "Returns only public lobby fields for the specified barangay. "
            "Resident names and ticket records are not exposed."
        ),
        responses=PublicQueueStatusSerializer
    )
    def get(self, request, barangay_id: int):
        barangay = get_object_or_404(
            Barangay.objects.only("id", "name", "primary_color"),
            pk=barangay_id,
        )
        day_start, next_day_start = manila_day_bounds()
        barangay_tickets = QueueTicket.objects.filter(
            barangay_id=barangay.pk,
            created_at__gte=day_start,
            created_at__lt=next_day_start,
        )
        current_ticket = (
            barangay_tickets
            .filter(status=QueueTicket.Status.SERVING)
            .order_by("-updated_at", "-pk")
            .values_list("ticket_number", flat=True)
            .first()
        )
        total_waiting = barangay_tickets.filter(
            status=QueueTicket.Status.WAITING,
        ).count()

        serializer = PublicQueueStatusSerializer(
            {
                "barangay_name": barangay.name,
                "primary_color": barangay.primary_color,
                "current_ticket": current_ticket,
                "total_waiting": total_waiting,
            }
        )
        return Response(serializer.data)
