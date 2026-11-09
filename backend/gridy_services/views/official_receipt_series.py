from django.db import transaction
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from gridy_audit.models import AuditLog
from gridy_audit.services import log_action
from gridy_auth.models import Barangay
from gridy_auth.permissions import IsBarangayOfficial
from gridy_services.models import OfficialReceiptSeries
from gridy_services.payment_serializers import OfficialReceiptSeriesSerializer


class OfficialReceiptSeriesView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsBarangayOfficial]

    def _barangay_id(self, request):
        barangay_id = request.user.barangay_id
        if not barangay_id:
            raise PermissionDenied("Your account must belong to a Barangay to configure its receipt series.")
        return barangay_id

    def get(self, request):
        barangay_id = self._barangay_id(request)
        series = OfficialReceiptSeries.objects.filter(barangay_id=barangay_id).first()
        if series is None:
            return Response({
                "configured": False,
                "prefix": "",
                "next_number": None,
                "number_width": 0,
                "last_issued_number": None,
            })
        return Response(OfficialReceiptSeriesSerializer(series).data)

    @transaction.atomic
    def patch(self, request):
        barangay_id = self._barangay_id(request)
        barangay = Barangay.objects.select_for_update().get(pk=barangay_id)
        series = (
            OfficialReceiptSeries.objects.select_for_update()
            .filter(barangay_id=barangay_id)
            .first()
        )
        serializer = OfficialReceiptSeriesSerializer(
            instance=series,
            data=request.data,
            partial=series is not None,
        )
        serializer.is_valid(raise_exception=True)
        previous_prefix = series.prefix if series is not None else None
        previous_next_number = series.next_number if series is not None else None
        series = serializer.save(barangay=barangay)
        rotation_note = (
            f" Started a new series after prefix {previous_prefix!r} (previous next serial {previous_next_number})."
            if previous_prefix is not None and previous_prefix != series.prefix
            else ""
        )
        log_action(
            user=request.user,
            action_type=AuditLog.ActionType.USER_ACTION,
            description=(
                f"Configured the Barangay-approved official receipt series for Barangay ID {barangay_id}; "
                f"prefix {series.prefix!r}, next serial {series.next_number}."
                f"{rotation_note}"
            ),
            request=request,
        )
        return Response(OfficialReceiptSeriesSerializer(series).data, status=status.HTTP_200_OK)
