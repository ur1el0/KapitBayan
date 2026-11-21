from django.db import transaction
from rest_framework import viewsets, permissions
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Q
from .models import IssueReport
from .serializers import IssueReportSerializer
from gridy_auth.permissions import IsBarangayOfficial, IsBarangayOfficialOrField, IsResident

from gridy_audit.services import log_action
from gridy_audit.models import AuditLog
from gridy_communications.admin_notifications import notify_barangay_admins


class IssueReportPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 50


class IssueReportViewSet(viewsets.ModelViewSet):
    lookup_value_regex = r"\d+"
    serializer_class = IssueReportSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    pagination_class = IssueReportPagination
    
    def get_permissions(self):
        # Only authenticated users can list/retrieve
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        # Strictly residents can file new community reports
        if self.action == 'create':
            return [IsResident()]
        # Strictly officials can update status, triage, and resolve
        return [IsBarangayOfficialOrField()]
    
    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return IssueReport.objects.none()

        # Barangay Officials only see reports from residents in their specific Barangay
        if user.role in ["ADMIN", "FIELD_OFFICIAL"]:
            if user.barangay_id is None:
                return IssueReport.objects.none()
            queryset = IssueReport.objects.filter(
                Q(barangay_id=user.barangay_id)
                | Q(barangay__isnull=True, reporter__barangay_id=user.barangay_id)
            )
        else:
            # Standard Residents only see their own reports
            queryset = IssueReport.objects.filter(reporter=user)

        status_param = (self.request.query_params.get('status') or '').strip().upper()
        if status_param in IssueReport.Status.values:
            queryset = queryset.filter(status=status_param)

        category_param = (self.request.query_params.get('category') or '').strip().upper()
        if category_param in IssueReport.Category.values:
            queryset = queryset.filter(category=category_param)

        urgency_param = (self.request.query_params.get('urgency') or '').strip().upper()
        if urgency_param in IssueReport.Urgency.values:
            queryset = queryset.filter(urgency=urgency_param)

        search_param = (self.request.query_params.get('search') or '').strip()
        if search_param:
            queryset = queryset.filter(
                Q(title__icontains=search_param)
                | Q(location__icontains=search_param)
                | Q(description__icontains=search_param)
            )

        return queryset.order_by('-created_at', '-id')

    @transaction.atomic
    def perform_create(self, serializer):
        serializer.save(
            reporter=self.request.user,
            barangay=self.request.user.barangay,
            status=IssueReport.Status.PENDING,
        )
        notify_barangay_admins(
            barangay_id=self.request.user.barangay_id,
            notification_type='report',
        )

    def perform_update(self, serializer):
        # Capture the fields that need an audit trail before saving.
        original_status = serializer.instance.status
        original_urgency = serializer.instance.urgency

        instance = serializer.save()
        changes = []

        if original_status != instance.status:
            changes.append(
                f"status from {original_status} to {instance.status}"
            )

        if original_urgency != instance.urgency:
            changes.append(
                f"urgency from {original_urgency} to {instance.urgency}"
            )

        if changes:
            log_action(
                user=self.request.user,
                action_type=AuditLog.ActionType.REPORT_ACTION,
                description=(
                    f"Updated issue report #{instance.id}: "
                    f"{'; '.join(changes)}."
                ),
                request=self.request
            )

    def perform_destroy(self, instance):
        log_action(
            user=self.request.user,
            action_type=AuditLog.ActionType.REPORT_ACTION,
            description=f"Deleted issue report #{instance.id} ('{instance.title}') with status {instance.status}.",
            request=self.request
        )
        instance.delete()
