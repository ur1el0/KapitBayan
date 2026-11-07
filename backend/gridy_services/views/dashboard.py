from django.db.models import Count, Q, Sum
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from gridy_auth.models import Resident, User
from gridy_auth.permissions import IsBarangayOfficial
from gridy_reports.models import IssueReport
from gridy_services.models import DocumentRequest, QueueTicket
from gridy_services.serializers import DashboardSummarySerializer


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

        # 2. Document Request Statistics (Include digital resident and walk-in records)
        doc_stats = DocumentRequest.objects.filter(
            Q(user__barangay=user.barangay) | Q(barangay=user.barangay)
        ).aggregate(
            total=Count('id'),
            pending=Count('id', filter=Q(status=DocumentRequest.Status.PENDING)),
            approved=Count('id', filter=Q(status=DocumentRequest.Status.PROCESSING)),
            rejected=Count('id', filter=Q(status=DocumentRequest.Status.REJECTED)),
            released=Count('id', filter=Q(status=DocumentRequest.Status.RELEASED)),
            revenue=Sum('fee_amount', filter=Q(status=DocumentRequest.Status.RELEASED)),
        )

        # 3. Issue Reports Statistics, Urgency & Category Breakdown (1 SINGLE AGGREGATE QUERY instead of 15)
        issue_stats = IssueReport.objects.filter(reporter__barangay=user.barangay).aggregate(
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
        serving_ticket = QueueTicket.objects.filter(barangay=user.barangay, status=QueueTicket.Status.SERVING).first()
        serving_now_val = serving_ticket.ticket_number if serving_ticket else None
        waiting_in_queue_val = QueueTicket.objects.filter(barangay=user.barangay, status=QueueTicket.Status.WAITING).count()

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
