import calendar
import csv
import io
import re
from datetime import datetime, time
from django.apps import apps
from django.db.models import Count, Q
from django.template.loader import get_template
from django.utils import timezone
from xhtml2pdf import pisa

from gridy_auth.models import Resident, ResidentTransferRequest, User
from gridy_communications.models import ActivitySchedule, Announcement
from gridy_reports.models import IssueReport
from gridy_services.models import (
    AidRequest,
    DocumentRequest,
    MANILA_TIME_ZONE,
)


def parse_report_year_month(year_param=None, month_param=None, now=None):
    """Validate and return ``(year, month)`` in Manila time, defaulting to current month."""
    manila_now = timezone.localtime(now or timezone.now(), MANILA_TIME_ZONE)
    year = manila_now.year if year_param in (None, "") else int(year_param)
    month = manila_now.month if month_param in (None, "") else int(month_param)
    if year < 2000 or year > 2100:
        raise ValueError("Year must be between 2000 and 2100.")
    if month < 1 or month > 12:
        raise ValueError("Month must be between 1 and 12.")
    return year, month


def manila_month_bounds(year: int, month: int):
    """Return aware ``(month_start, next_month_start)`` in Asia/Manila timezone."""
    month_start = datetime(year, month, 1, 0, 0, 0, tzinfo=MANILA_TIME_ZONE)
    if month == 12:
        next_month_start = datetime(year + 1, 1, 1, 0, 0, 0, tzinfo=MANILA_TIME_ZONE)
    else:
        next_month_start = datetime(year, month + 1, 1, 0, 0, 0, tzinfo=MANILA_TIME_ZONE)
    return month_start, next_month_start


def build_accomplishment_report(barangay, year: int | None = None, month: int | None = None):
    """Aggregate monthly accomplishment metrics strictly scoped to ``barangay``."""
    resolved_year, resolved_month = parse_report_year_month(year, month)
    month_start, next_month_start = manila_month_bounds(resolved_year, resolved_month)
    month_name = calendar.month_name[resolved_month]
    period_label = f"{month_name} {resolved_year}"

    # 1. Residents & RBI Updates
    new_registered_residents = User.objects.filter(
        role=User.Role.RESIDENT,
        barangay=barangay,
        date_joined__gte=month_start,
        date_joined__lt=next_month_start,
    ).count()

    new_verified_residents = Resident.objects.filter(
        user__role=User.Role.RESIDENT,
        user__barangay=barangay,
        is_verified=True,
        user__date_joined__gte=month_start,
        user__date_joined__lt=next_month_start,
    ).count()

    approved_rbi_transfers = ResidentTransferRequest.objects.filter(
        Q(destination_barangay=barangay) | Q(source_barangay=barangay),
        status=ResidentTransferRequest.Status.APPROVED,
        created_at__gte=month_start,
        created_at__lt=next_month_start,
    ).count()

    total_active_verified_residents = Resident.objects.filter(
        user__role=User.Role.RESIDENT,
        user__barangay=barangay,
        user__is_active=True,
        is_verified=True,
    ).count()

    # 2. Certificates & Document Issuance
    barangay_docs_in_month = DocumentRequest.objects.filter(
        Q(barangay=barangay) | Q(barangay__isnull=True, user__barangay=barangay),
        created_at__gte=month_start,
        created_at__lt=next_month_start,
    )
    doc_aggregates = barangay_docs_in_month.aggregate(
        total_requests=Count("id"),
        total_issued=Count("id", filter=Q(status=DocumentRequest.Status.RELEASED)),
        fee_waived_or_exempt_count=Count(
            "id",
            filter=Q(
                status=DocumentRequest.Status.RELEASED,
                fee_assessment_status__in=[
                    DocumentRequest.FeeAssessmentStatus.WAIVED,
                    DocumentRequest.FeeAssessmentStatus.STATUTORY_EXEMPT,
                ],
            ),
        ),
    )

    doc_type_rows = (
        barangay_docs_in_month.filter(status=DocumentRequest.Status.RELEASED)
        .values("document_type")
        .annotate(count=Count("id"))
        .order_by("-count", "document_type")
    )
    by_document_type = [
        {"document_type": row["document_type"], "count": row["count"]}
        for row in doc_type_rows
    ]

    # 3. Community Issues, Aid & Equipment Services
    issue_aggregates = IssueReport.objects.filter(
        reporter__barangay=barangay,
        created_at__gte=month_start,
        created_at__lt=next_month_start,
    ).aggregate(
        issues_submitted=Count("id"),
        issues_resolved=Count("id", filter=Q(status=IssueReport.Status.RESOLVED)),
    )

    aid_aggregates = AidRequest.objects.filter(
        barangay=barangay,
        created_at__gte=month_start,
        created_at__lt=next_month_start,
    ).aggregate(
        aid_requests_submitted=Count("id"),
        aid_requests_approved=Count("id", filter=Q(status=AidRequest.Status.APPROVED)),
    )

    equipment_requests_fulfilled = 0
    equipment_requests_returned = 0
    try:
        EquipmentBorrowRequest = apps.get_model("gridy_services", "EquipmentBorrowRequest")
    except LookupError:
        EquipmentBorrowRequest = None

    if EquipmentBorrowRequest is not None:
        equip_aggregates = EquipmentBorrowRequest.objects.filter(
            barangay=barangay,
            created_at__gte=month_start,
            created_at__lt=next_month_start,
        ).aggregate(
            fulfilled=Count(
                "id",
                filter=Q(
                    status__in=[
                        EquipmentBorrowRequest.Status.APPROVED,
                        EquipmentBorrowRequest.Status.RETURNED,
                    ]
                ),
            ),
            returned=Count(
                "id",
                filter=Q(status=EquipmentBorrowRequest.Status.RETURNED),
            ),
        )
        equipment_requests_fulfilled = equip_aggregates["fulfilled"] or 0
        equipment_requests_returned = equip_aggregates["returned"] or 0

    # 4. Public Communications & Activities
    announcements_published = Announcement.objects.filter(
        created_by__barangay=barangay,
        created_at__gte=month_start,
        created_at__lt=next_month_start,
    ).count()

    activities_conducted = ActivitySchedule.objects.filter(
        created_by__barangay=barangay,
        event_datetime__gte=month_start,
        event_datetime__lt=next_month_start,
    ).count()

    return {
        "barangay_name": barangay.name,
        "municipality": barangay.municipality or "",
        "province": barangay.province or "",
        "captain_name": barangay.captain_name or "Punong Barangay",
        "year": resolved_year,
        "month": resolved_month,
        "period_label": period_label,
        "generated_at": timezone.now().isoformat(),
        "residents_rbi": {
            "new_registered_residents": new_registered_residents,
            "new_verified_residents": new_verified_residents,
            "approved_rbi_transfers": approved_rbi_transfers,
            "total_active_verified_residents": total_active_verified_residents,
        },
        "certificates_issuance": {
            "total_requests": doc_aggregates["total_requests"] or 0,
            "total_issued": doc_aggregates["total_issued"] or 0,
            "fee_waived_or_exempt_count": doc_aggregates["fee_waived_or_exempt_count"] or 0,
            "by_document_type": by_document_type,
        },
        "community_services": {
            "issues_submitted": issue_aggregates["issues_submitted"] or 0,
            "issues_resolved": issue_aggregates["issues_resolved"] or 0,
            "aid_requests_submitted": aid_aggregates["aid_requests_submitted"] or 0,
            "aid_requests_approved": aid_aggregates["aid_requests_approved"] or 0,
            "equipment_requests_fulfilled": equipment_requests_fulfilled,
            "equipment_requests_returned": equipment_requests_returned,
        },
        "communications_activities": {
            "announcements_published": announcements_published,
            "activities_conducted": activities_conducted,
        },
    }


def build_safe_report_filename(barangay_name: str, year: int, month: int, ext: str) -> str:
    safe_brgy = re.sub(r"[^A-Za-z0-9_-]+", "_", (barangay_name or "Barangay").strip()).strip("_") or "Barangay"
    return f"Accomplishment_Report_{safe_brgy}_{year}_{month:02d}.{ext}"


def render_accomplishment_report_csv(report: dict) -> bytes:
    """Render a UTF-8 BOM-encoded CSV suitable for Excel and DILG submission."""
    buffer = io.StringIO()
    buffer.write("\ufeff")
    writer = csv.writer(buffer)

    writer.writerow(["MONTHLY BARANGAY ACCOMPLISHMENT REPORT"])
    writer.writerow(["Barangay", report["barangay_name"]])
    if report.get("municipality") or report.get("province"):
        locality = ", ".join(filter(None, [report.get("municipality"), report.get("province")]))
        writer.writerow(["Locality", locality])
    writer.writerow(["Period Covered", report["period_label"]])
    writer.writerow(["Generated At", report["generated_at"]])
    writer.writerow([])

    writer.writerow(["Category", "Metric", "Count"])

    res = report["residents_rbi"]
    writer.writerow(["1. Residents & RBI Updates", "New Registered Residents", res["new_registered_residents"]])
    writer.writerow(["1. Residents & RBI Updates", "New Verified Residents", res["new_verified_residents"]])
    writer.writerow(["1. Residents & RBI Updates", "Approved Resident Transfers / RBI Updates", res["approved_rbi_transfers"]])
    writer.writerow(["1. Residents & RBI Updates", "Total Active Verified Residents (Cumulative)", res["total_active_verified_residents"]])

    cert = report["certificates_issuance"]
    writer.writerow(["2. Certificates & Document Issuance", "Total Certificates / Clearances Issued", cert["total_issued"]])
    writer.writerow(["2. Certificates & Document Issuance", "Fee-Waived / Statutory Exempt Certificates Issued", cert["fee_waived_or_exempt_count"]])
    for item in cert["by_document_type"]:
        writer.writerow([
            "2. Certificates & Document Issuance (Breakdown)",
            item["document_type"],
            item["count"],
        ])

    svc = report["community_services"]
    writer.writerow(["3. Community Issues, Aid & Equipment", "Community Issues Submitted", svc["issues_submitted"]])
    writer.writerow(["3. Community Issues, Aid & Equipment", "Community Issues Resolved", svc["issues_resolved"]])
    writer.writerow(["3. Community Issues, Aid & Equipment", "Aid Requests Approved / Fulfilled", svc["aid_requests_approved"]])
    writer.writerow(["3. Community Issues, Aid & Equipment", "Equipment / Facility Requests Approved or Returned", svc["equipment_requests_fulfilled"]])

    comm = report["communications_activities"]
    writer.writerow(["4. Public Communications & Activities", "Public Announcements Published", comm["announcements_published"]])
    writer.writerow(["4. Public Communications & Activities", "Community Activities Conducted", comm["activities_conducted"]])

    return buffer.getvalue().encode("utf-8")


def render_accomplishment_report_pdf(report: dict) -> bytes:
    """Render an A4 PDF accomplishment report using xhtml2pdf."""
    template = get_template("gridy_services/accomplishment_report_pdf.html")
    html = template.render({"report": report})
    pdf_buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=pdf_buffer)
    if pisa_status.err:
        raise RuntimeError("Failed to generate Accomplishment Report PDF.")
    return pdf_buffer.getvalue()
