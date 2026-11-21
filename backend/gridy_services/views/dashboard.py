from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from gridy_auth.models import Resident, User
from gridy_auth.permissions import IsBarangayOfficial
from gridy_reports.models import IssueReport
from gridy_services.accomplishment_report import (
    build_accomplishment_report,
    build_safe_report_filename,
    render_accomplishment_report_csv,
    render_accomplishment_report_pdf,
)
from gridy_services.models import DocumentRequest, QueueTicket, manila_day_bounds
from gridy_services.serializers import (
    AccomplishmentReportSerializer,
    DashboardSummarySerializer,
)


@extend_schema(
    summary="Get Dashboard Statistics",
    description="Returns pre-calculated counters and urgency distributions for reports, document queues, and clearances.",
    responses={200: DashboardSummarySerializer}
)
class DashboardSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsBarangayOfficial]

    def get(self, request, *args, **kwargs):
        user = request.user
        today = timezone.now().date()

        # 1. Total Residents for this Barangay (1 query)
        total_res = User.objects.filter(role=User.Role.RESIDENT, barangay=user.barangay).count()

        # 2. Document Request Statistics (Preserve historical origin after resident transfers)
        doc_stats = DocumentRequest.objects.filter(
            Q(barangay=user.barangay)
            | Q(barangay__isnull=True, is_walkin=False, user__barangay=user.barangay)
        ).aggregate(
            total=Count('id'),
            pending=Count('id', filter=Q(status=DocumentRequest.Status.PENDING)),
            approved=Count('id', filter=Q(status=DocumentRequest.Status.PROCESSING)),
            rejected=Count('id', filter=Q(status=DocumentRequest.Status.REJECTED)),
            released=Count('id', filter=Q(status=DocumentRequest.Status.RELEASED)),
            revenue=Sum('fee_amount', filter=Q(status=DocumentRequest.Status.RELEASED)),
        )

        # 3. Issue Reports Statistics, Urgency & Category Breakdown (1 SINGLE AGGREGATE QUERY instead of 15)
        issue_stats = IssueReport.objects.filter(
            Q(barangay=user.barangay)
            | Q(barangay__isnull=True, reporter__barangay=user.barangay)
        ).aggregate(
            total=Count('id'),
            pending=Count('id', filter=Q(status=IssueReport.Status.PENDING)),
            in_progress=Count('id', filter=Q(status=IssueReport.Status.IN_PROGRESS)),
            resolved=Count('id', filter=Q(status=IssueReport.Status.RESOLVED)),
            # Urgency Breakdown
            minor=Count('id', filter=Q(urgency=IssueReport.Urgency.MINOR)),
            moderate=Count('id', filter=Q(urgency=IssueReport.Urgency.MODERATE)),
            hazard=Count('id', filter=Q(urgency=IssueReport.Urgency.HAZARD)),
            emergency=Count('id', filter=Q(urgency=IssueReport.Urgency.EMERGENCY)),
            # Category Breakdown
            peace_and_order=Count('id', filter=Q(category=IssueReport.Category.PEACE_AND_ORDER)),
            public_health=Count('id', filter=Q(category=IssueReport.Category.PUBLIC_HEALTH)),
            infrastructure=Count('id', filter=Q(category=IssueReport.Category.INFRASTRUCTURE)),
            environment=Count('id', filter=Q(category=IssueReport.Category.ENVIRONMENT)),
            other=Count('id', filter=Q(category=IssueReport.Category.OTHER)),
            # Incident Timing Analysis (Night vs Day)
            night_time=Count('id', filter=Q(incident_datetime__hour__gte=22) | Q(incident_datetime__hour__lt=5)),
            day_time=Count('id', filter=Q(incident_datetime__hour__gte=5, incident_datetime__hour__lt=22)),
        )

        # 4. Live Queue Summary
        queue_day_start, queue_next_day_start = manila_day_bounds()
        today_queue = QueueTicket.objects.filter(
            barangay=user.barangay,
            created_at__gte=queue_day_start,
            created_at__lt=queue_next_day_start,
        )
        serving_ticket = today_queue.filter(status=QueueTicket.Status.SERVING).order_by("-created_at", "-id").first()
        serving_now_val = serving_ticket.ticket_number if serving_ticket else None
        waiting_in_queue_val = today_queue.filter(status=QueueTicket.Status.WAITING).count()

        # 5. Demographics (only report values present in the Barangay registry)
        purok_stats = Resident.objects.filter(user__barangay=user.barangay, purok__isnull=False).values('purok').annotate(count=Count('purok')).order_by('purok')

        purok_distribution = {
            item['purok'] if str(item['purok']).lower().startswith('purok') else f"Purok {item['purok']}": item['count']
            for item in purok_stats
        }

        # 6. Demographics (Age Distribution)
        def get_past_date(years):
            try:
                return today.replace(year=today.year - years)
            except ValueError:
                return today.replace(year=today.year - years, day=28)

        date_18_years_ago = get_past_date(18)
        date_36_years_ago = get_past_date(36)
        date_60_years_ago = get_past_date(60)

        age_demographics = Resident.objects.filter(user__barangay=user.barangay).aggregate(
            youth=Count('id', filter=Q(birth_date__gt=date_18_years_ago)),
            young_adult=Count('id', filter=Q(birth_date__lte=date_18_years_ago, birth_date__gt=date_36_years_ago)),
            adult=Count('id', filter=Q(birth_date__lte=date_36_years_ago, birth_date__gt=date_60_years_ago)),
            senior=Count('id', filter=Q(birth_date__lte=date_60_years_ago)),
        )

        # 7. Category / Incident Scenario Breakdown (only actual incident records)
        category_breakdown = {
            "peace_and_order": issue_stats['peace_and_order'] or 0,
            "public_health": issue_stats['public_health'] or 0,
            "infrastructure": issue_stats['infrastructure'] or 0,
            "environment": issue_stats['environment'] or 0,
            "other": issue_stats['other'] or 0,
        }

        data = {
            "total_residents": total_res,
            "document_requests": {
                "total": doc_stats['total'] or 0,
                "pending": doc_stats['pending'] or 0,
                "approved": doc_stats['approved'] or 0,
                "rejected": doc_stats['rejected'] or 0,
                "released": doc_stats['released'] or 0,
                "total_revenue": float(doc_stats['revenue'] or 0.0)
            },
            "issue_reports": {
                "total": issue_stats['total'] or 0,
                "pending": issue_stats['pending'] or 0,
                "in_progress": issue_stats['in_progress'] or 0,
                "resolved": issue_stats['resolved'] or 0,
                "urgency_breakdown": {
                    "minor": issue_stats['minor'] or 0,
                    "moderate": issue_stats['moderate'] or 0,
                    "hazard": issue_stats['hazard'] or 0,
                    "emergency": issue_stats['emergency'] or 0
                },
                "category_breakdown": category_breakdown,
                "scenario_breakdown": category_breakdown,
                "incident_timing": {
                    "day_time": issue_stats['day_time'] or 0,
                    "night_time": issue_stats['night_time'] or 0,
                }
            },
            "demographics": {
                "purok_distribution": purok_distribution,
                "age_demographics": age_demographics
            },
            "queue_activity": {
                "serving_now": serving_now_val,
                "waiting_in_queue": waiting_in_queue_val,
            }
        }
        return Response(data, status=status.HTTP_200_OK)


def _get_scoped_accomplishment_report_for_request(request):
    user = request.user
    if not user or not user.barangay_id or not user.barangay:
        raise PermissionDenied(
            "Your account must be assigned to a barangay to access accomplishment reports."
        )
    try:
        return build_accomplishment_report(
            barangay=user.barangay,
            year=request.query_params.get("year"),
            month=request.query_params.get("month"),
            start_date=request.query_params.get("start_date"),
            end_date=request.query_params.get("end_date"),
            metrics=request.query_params.get("metrics"),
        )
    except (TypeError, ValueError) as exc:
        raise ValidationError({"detail": str(exc)})


@extend_schema(
    summary="Get Monthly Barangay Accomplishment Report",
    description="Returns tenant-scoped monthly or custom-range executive summary metrics for the Barangay Admin's barangay.",
    parameters=[
        OpenApiParameter(name="year", type=int, required=False, description="Report year (YYYY)"),
        OpenApiParameter(name="month", type=int, required=False, description="Report month (1-12)"),
        OpenApiParameter(name="start_date", type=str, required=False, description="Custom range start (YYYY-MM-DD)"),
        OpenApiParameter(name="end_date", type=str, required=False, description="Custom range end (YYYY-MM-DD)"),
        OpenApiParameter(name="metrics", type=str, required=False, description="Comma-separated report metric filters"),
    ],
    responses={200: AccomplishmentReportSerializer},
)
class AccomplishmentReportView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsBarangayOfficial]

    def get(self, request, *args, **kwargs):
        report = _get_scoped_accomplishment_report_for_request(request)
        return Response(report, status=status.HTTP_200_OK)


@extend_schema(
    summary="Export Monthly Barangay Accomplishment Report (CSV or PDF)",
    description="Exports the filtered accomplishment report for the Barangay Admin's barangay as CSV or PDF.",
    parameters=[
        OpenApiParameter(name="year", type=int, required=False, description="Report year (YYYY)"),
        OpenApiParameter(name="month", type=int, required=False, description="Report month (1-12)"),
        OpenApiParameter(name="start_date", type=str, required=False, description="Custom range start (YYYY-MM-DD)"),
        OpenApiParameter(name="end_date", type=str, required=False, description="Custom range end (YYYY-MM-DD)"),
        OpenApiParameter(name="metrics", type=str, required=False, description="Comma-separated report metric filters"),
        OpenApiParameter(name="export_format", type=str, required=False, enum=["csv", "pdf"]),
    ],
    responses={200: bytes},
)
class AccomplishmentReportExportView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsBarangayOfficial]

    def get(self, request, *args, **kwargs):
        report = _get_scoped_accomplishment_report_for_request(request)
        export_format = (
            request.query_params.get("export_format")
            or request.query_params.get("format_type")
            or "csv"
        ).strip().lower()

        if export_format == "csv":
            payload = render_accomplishment_report_csv(report)
            filename = build_safe_report_filename(
                report["barangay_name"],
                report["year"],
                report["month"],
                "csv",
                start_date=report.get("start_date"),
                end_date=report.get("end_date"),
                period_mode=report.get("period_mode", "month"),
            )
            response = HttpResponse(payload, content_type="text/csv; charset=utf-8")
        elif export_format == "pdf":
            payload = render_accomplishment_report_pdf(report)
            filename = build_safe_report_filename(
                report["barangay_name"],
                report["year"],
                report["month"],
                "pdf",
                start_date=report.get("start_date"),
                end_date=report.get("end_date"),
                period_mode=report.get("period_mode", "month"),
            )
            response = HttpResponse(payload, content_type="application/pdf")
        else:
            raise ValidationError({"export_format": "Select 'csv' or 'pdf'."})

        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response["Cache-Control"] = "private, no-store, max-age=0"
        response["X-Content-Type-Options"] = "nosniff"
        return response
