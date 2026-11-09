from django.db.models import Q
from django.db.models.functions import Lower, Trim
from rest_framework.exceptions import ValidationError

from .models import DocumentRequest, OfficialReceiptSeries

MAX_SERIAL_NUMBER = 9_223_372_036_854_775_807


def assign_official_receipt_number(document_request):
    """Allocate the configured Barangay series number once, inside the caller's transaction."""
    if document_request.or_number:
        return document_request.or_number
    if document_request.fee_amount <= 0:
        raise ValidationError({"detail": "A receipt number is not required for a zero-fee request."})

    barangay_id = document_request.barangay_id or getattr(
        document_request.user, "barangay_id", None
    )
    if not barangay_id:
        raise ValidationError({"detail": "This request is not assigned to a Barangay receipt series."})

    series = (
        OfficialReceiptSeries.objects.select_for_update()
        .filter(barangay_id=barangay_id)
        .first()
    )
    if series is None or not series.is_configured:
        raise ValidationError({
            "detail": "Configure the Barangay's approved O.R. prefix and next unused serial in Barangay Settings before confirming payment."
        })

    serial = series.next_number
    if serial >= MAX_SERIAL_NUMBER:
        raise ValidationError({
            "detail": "This O.R. series has reached its supported limit. Configure a new approved prefix before confirming another payment."
        })
    or_number = series.format_number(serial)
    if len(or_number) > 50:
        raise ValidationError({
            "detail": "The configured O.R. prefix and serial exceed the supported 50-character receipt number."
        })

    same_barangay_requests = DocumentRequest.objects.filter(
        Q(barangay_id=barangay_id)
        | Q(barangay_id__isnull=True, is_walkin=False, user__barangay_id=barangay_id)
    )
    duplicate = (
        same_barangay_requests.annotate(
            normalized_or_number=Lower(Trim("or_number")),
        )
        .exclude(pk=document_request.pk)
        .filter(normalized_or_number=or_number.strip().lower())
        .exists()
    )
    if duplicate:
        raise ValidationError({
            "detail": "The configured next O.R. number is already recorded. Check the Barangay's receipt book and advance the next serial before confirming payment."
        })

    document_request.or_number = or_number
    series.last_issued_number = serial
    series.next_number = serial + 1
    series.save(update_fields=["last_issued_number", "next_number", "updated_at"])
    return or_number
