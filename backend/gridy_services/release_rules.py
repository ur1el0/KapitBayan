from rest_framework.exceptions import ValidationError

from gridy_services.models import DocumentRequest


def validate_document_release_requirements(document_request):
    """Enforce the staff-reviewed fee and payment rules for release."""
    if document_request.status in (
        DocumentRequest.Status.READY_FOR_PICKUP,
        DocumentRequest.Status.RELEASED,
    ) and document_request.fee_assessment_status == (
        DocumentRequest.FeeAssessmentStatus.AWAITING_ASSESSMENT
    ):
        raise ValidationError({
            "fee_assessment_status": (
                "Document fee must be assessed or explicitly waived before "
                "marking ready for pickup."
            )
        })

    if document_request.status != DocumentRequest.Status.RELEASED:
        return document_request

    if document_request.fee_amount <= 0:
        document_request.payment_status = DocumentRequest.PaymentStatus.NOT_REQUIRED
        return document_request

    if not (document_request.or_number or "").strip():
        raise ValidationError({
            "or_number": "An official receipt number is required before release."
        })

    if document_request.payment_method == DocumentRequest.PaymentMethod.CASH:
        if (
            document_request.is_walkin
            and document_request.payment_status
            != DocumentRequest.PaymentStatus.VERIFIED
        ):
            raise ValidationError({
                "payment_status": (
                    "Record the walk-in cash payment as received before releasing "
                    "this document."
                )
            })
        document_request.payment_status = DocumentRequest.PaymentStatus.VERIFIED
    elif document_request.payment_method in {
        DocumentRequest.PaymentMethod.GCASH,
        DocumentRequest.PaymentMethod.MAYA,
        DocumentRequest.PaymentMethod.BANK,
        DocumentRequest.PaymentMethod.OTHER,
    }:
        if document_request.payment_status != DocumentRequest.PaymentStatus.VERIFIED:
            raise ValidationError({
                "payment_status": "Verify the transfer before releasing this document."
            })
    else:
        raise ValidationError({
            "payment_method": "Record cash or a verified electronic transfer."
        })

    return document_request
