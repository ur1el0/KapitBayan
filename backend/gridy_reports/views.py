from rest_framework import viewsets, permissions
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .models import IssueReport
from .serializers import IssueReportSerializer
from gridy_auth.permissions import IsBarangayOfficial, IsBarangayOfficialOrField, IsResident

from gridy_audit.services import log_action
from gridy_audit.models import AuditLog

class IssueReportViewSet(viewsets.ModelViewSet):
    serializer_class = IssueReportSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
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
            return IssueReport.objects.filter(reporter__barangay_id=user.barangay_id).order_by('-created_at')
        
        # Standard Residents only see their own reports (and we fixed the created_by typo)
        return IssueReport.objects.filter(reporter=user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(
            reporter=self.request.user,
            status=IssueReport.Status.PENDING,
            urgency=IssueReport.Urgency.MINOR
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
