import calendar
import csv
import io
import re
from datetime import date, datetime, time, timedelta
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

REPORT_METRIC_LABELS = {
    "new_registered_residents": "Newly Registered Residents",
    "rbi_transfers": "RBI Transfers & Active Resident Baseline",
    "documents_issued": "Documents & Clearances Issued",
    "incidents": "Community Issues / Incident Reports",
    "aid_requests": "Financial & Assistance (Aid) Requests",
    "equipment_borrowing": "Equipment & Facility Borrowing",
    "communications": "Announcements & Community Activities",
}
ALL_REPORT_METRICS = tuple(REPORT_METRIC_LABELS.keys())


def parse_report_metrics(metrics_param=None) -> list[str]:
    """Validate and resolve requested report metric filters, defaulting to all metrics."""
    if metrics_param in (None, "", "all", "ALL"):
        return list(ALL_REPORT_METRICS)
    if isinstance(metrics_param, (list, tuple)):
        raw_items = [str(item).strip().lower() for item in metrics_param if str(item).strip()]
    else:
        raw_items = [item.strip().lower() for item in str(metrics_param).split(",") if item.strip()]
    if not raw_items:
        return list(ALL_REPORT_METRICS)
    invalid = [item for item in raw_items if item not in REPORT_METRIC_LABELS]
    if invalid:
        raise ValueError(f"Unsupported report filter(s): {', '.join(invalid)}.")
    # Preserve canonical display order and deduplicate
    selected_set = set(raw_items)
    return [metric for metric in ALL_REPORT_METRICS if metric in selected_set]


def parse_report_period(
    year_param=None,
    month_param=None,
    start_date_param=None,
    end_date_param=None,
    now=None,
):
    """Resolve either an explicit Manila date range or a monthly (year, month) window."""
    if start_date_param or end_date_param:
        if not (start_date_param and end_date_param):
            raise ValueError("Both start_date and end_date are required for custom date filtering.")
        start_d = start_date_param if isinstance(start_date_param, date) else date.fromisoformat(str(start_date_param).strip())
        end_d = end_date_param if isinstance(end_date_param, date) else date.fromisoformat(str(end_date_param).strip())
        if end_d < start_d:
            raise ValueError("End date cannot be earlier than start date.")
        period_start = datetime.combine(start_d, time.min, tzinfo=MANILA_TIME_ZONE)
        period_end_exclusive = datetime.combine(end_d + timedelta(days=1), time.min, tzinfo=MANILA_TIME_ZONE)
        if start_d == end_d:
            period_label = start_d.strftime("%B %d, %Y")
        else:
            period_label = f"{start_d.strftime('%b %d, %Y')} – {end_d.strftime('%b %d, %Y')}"
        return {
            "mode": "range",
            "year": end_d.year,
            "month": end_d.month,
            "start_date": start_d.isoformat(),
            "end_date": end_d.isoformat(),
            "period_start": period_start,
            "period_end_exclusive": period_end_exclusive,
            "period_label": period_label,
        }

    resolved_year, resolved_month = parse_report_year_month(year_param, month_param, now=now)
    month_start, next_month_start = manila_month_bounds(resolved_year, resolved_month)
    month_name = calendar.month_name[resolved_month]
    return {
        "mode": "month",
        "year": resolved_year,
        "month": resolved_month,
        "start_date": month_start.date().isoformat(),
        "end_date": (next_month_start - timedelta(days=1)).date().isoformat(),
        "period_start": month_start,
        "period_end_exclusive": next_month_start,
        "period_label": f"{month_name} {resolved_year}",
    }


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


def build_accomplishment_report(
    barangay,
    year: int | None = None,
    month: int | None = None,
    start_date=None,
    end_date=None,
    metrics=None,
):
    """Aggregate filtered accomplishment metrics strictly scoped to ``barangay``."""
    period = parse_report_period(
        year_param=year,
        month_param=month,
        start_date_param=start_date,
        end_date_param=end_date,
    )
    included_metrics = parse_report_metrics(metrics)
    included_set = set(included_metrics)
    period_start = period["period_start"]
    period_end = period["period_end_exclusive"]

    # 1. Residents & RBI Updates
    new_registered_residents = User.objects.filter(
        role=User.Role.RESIDENT,
        barangay=barangay,
        date_joined__gte=period_start,
        date_joined__lt=period_end,
    ).count()

    new_verified_residents = Resident.objects.filter(
        user__role=User.Role.RESIDENT,
        user__barangay=barangay,
        is_verified=True,
        user__date_joined__gte=period_start,
        user__date_joined__lt=period_end,
    ).count()

    approved_rbi_transfers = ResidentTransferRequest.objects.filter(
        Q(destination_barangay=barangay) | Q(source_barangay=barangay),
        status=ResidentTransferRequest.Status.APPROVED,
        created_at__gte=period_start,
        created_at__lt=period_end,
    ).count()

    total_active_verified_residents = Resident.objects.filter(
        user__role=User.Role.RESIDENT,
        user__barangay=barangay,
        user__is_active=True,
        is_verified=True,
    ).count()

    # 2. Certificates & Document Issuance
    barangay_docs_in_period = DocumentRequest.objects.filter(
        Q(barangay=barangay)
        | Q(barangay__isnull=True, is_walkin=False, user__barangay=barangay),
        created_at__gte=period_start,
        created_at__lt=period_end,
    )
    doc_aggregates = barangay_docs_in_period.aggregate(
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
        barangay_docs_in_period.filter(status=DocumentRequest.Status.RELEASED)
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
        Q(barangay=barangay)
        | Q(barangay__isnull=True, reporter__barangay=barangay),
        created_at__gte=period_start,
        created_at__lt=period_end,
    ).aggregate(
        issues_submitted=Count("id"),
        issues_resolved=Count("id", filter=Q(status=IssueReport.Status.RESOLVED)),
    )

    aid_aggregates = AidRequest.objects.filter(
        barangay=barangay,
        created_at__gte=period_start,
        created_at__lt=period_end,
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
            created_at__gte=period_start,
            created_at__lt=period_end,
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
        created_at__gte=period_start,
        created_at__lt=period_end,
    ).count()

    activities_conducted = ActivitySchedule.objects.filter(
        created_by__barangay=barangay,
        event_datetime__gte=period_start,
        event_datetime__lt=period_end,
    ).count()

    is_full_report = len(included_metrics) == len(ALL_REPORT_METRICS)
    filter_summary = (
        "All Report Categories"
        if is_full_report
        else ", ".join(REPORT_METRIC_LABELS[key] for key in included_metrics)
    )

    return {
        "barangay_name": barangay.name,
        "municipality": barangay.municipality or "",
        "province": barangay.province or "",
        "captain_name": barangay.captain_name or "Punong Barangay",
        "year": period["year"],
        "month": period["month"],
        "period_mode": period["mode"],
        "start_date": period["start_date"],
        "end_date": period["end_date"],
        "period_label": period["period_label"],
        "generated_at": timezone.now().isoformat(),
        "included_metrics": included_metrics,
        "filter_summary": filter_summary,
        "sections_visible": {
            "residents_rbi": "new_registered_residents" in included_set or "rbi_transfers" in included_set,
            "certificates_issuance": "documents_issued" in included_set,
            "community_services": bool(
                {"incidents", "aid_requests", "equipment_borrowing"} & included_set
            ),
            "communications_activities": "communications" in included_set,
        },
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


def build_safe_report_filename(
    barangay_name: str,
    year: int,
    month: int,
    ext: str,
    start_date: str | None = None,
    end_date: str | None = None,
    period_mode: str = "month",
) -> str:
    safe_brgy = re.sub(r"[^A-Za-z0-9_-]+", "_", (barangay_name or "Barangay").strip()).strip("_") or "Barangay"
    if period_mode == "range" and start_date and end_date:
        return f"Accomplishment_Report_{safe_brgy}_{start_date}_to_{end_date}.{ext}"
    return f"Accomplishment_Report_{safe_brgy}_{year}_{month:02d}.{ext}"


_CSV_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _sanitize_csv_cell(value):
    """Neutralize spreadsheet formula payloads while leaving non-formula values unchanged."""
    if not isinstance(value, str) or not value:
        return value
    if value[0] in _CSV_FORMULA_PREFIXES or value.lstrip(" \t\r\n").startswith(
        ("=", "+", "-", "@")
    ):
        return f"'{value}"
    return value


def render_accomplishment_report_csv(report: dict) -> bytes:
    """Render a UTF-8 BOM-encoded CSV suitable for Excel and DILG submission."""
    included = set(report.get("included_metrics") or ALL_REPORT_METRICS)
    buffer = io.StringIO()
    buffer.write("\ufeff")
    writer = csv.writer(buffer)

    def write_row(row):
        writer.writerow([_sanitize_csv_cell(cell) for cell in row])

    write_row(["MONTHLY BARANGAY ACCOMPLISHMENT REPORT"])
    write_row(["Barangay", report["barangay_name"]])
    if report.get("municipality") or report.get("province"):
        locality = ", ".join(filter(None, [report.get("municipality"), report.get("province")]))
        write_row(["Locality", locality])
    write_row(["Period Covered", report["period_label"]])
    write_row(["Filter Scope", report.get("filter_summary", "All Report Categories")])
    write_row(["Generated At", report["generated_at"]])
    write_row([])

    write_row(["Category", "Metric", "Count"])

    res = report["residents_rbi"]
    if "new_registered_residents" in included:
        write_row(["1. Residents & RBI Updates", "New Registered Residents", res["new_registered_residents"]])
        write_row(["1. Residents & RBI Updates", "New Verified Residents", res["new_verified_residents"]])
    if "rbi_transfers" in included:
        write_row(["1. Residents & RBI Updates", "Approved Resident Transfers / RBI Updates", res["approved_rbi_transfers"]])
        write_row(["1. Residents & RBI Updates", "Total Active Verified Residents (Cumulative)", res["total_active_verified_residents"]])

    cert = report["certificates_issuance"]
    if "documents_issued" in included:
        write_row(["2. Certificates & Document Issuance", "Total Certificates / Clearances Issued", cert["total_issued"]])
        write_row(["2. Certificates & Document Issuance", "Fee-Waived / Statutory Exempt Certificates Issued", cert["fee_waived_or_exempt_count"]])
        for item in cert["by_document_type"]:
            write_row([
                "2. Certificates & Document Issuance (Breakdown)",
                item["document_type"],
                item["count"],
            ])

    svc = report["community_services"]
    if "incidents" in included:
        write_row(["3. Community Issues, Aid & Equipment", "Community Issues Submitted", svc["issues_submitted"]])
        write_row(["3. Community Issues, Aid & Equipment", "Community Issues Resolved", svc["issues_resolved"]])
    if "aid_requests" in included:
        write_row(["3. Community Issues, Aid & Equipment", "Aid Requests Submitted", svc.get("aid_requests_submitted", 0)])
        write_row(["3. Community Issues, Aid & Equipment", "Aid Requests Approved / Fulfilled", svc["aid_requests_approved"]])
    if "equipment_borrowing" in included:
        write_row(["3. Community Issues, Aid & Equipment", "Equipment / Facility Requests Approved or Returned", svc["equipment_requests_fulfilled"]])
        write_row(["3. Community Issues, Aid & Equipment", "Equipment / Facility Requests Returned", svc.get("equipment_requests_returned", 0)])

    comm = report["communications_activities"]
    if "communications" in included:
        write_row(["4. Public Communications & Activities", "Public Announcements Published", comm["announcements_published"]])
        write_row(["4. Public Communications & Activities", "Community Activities Conducted", comm["activities_conducted"]])

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
