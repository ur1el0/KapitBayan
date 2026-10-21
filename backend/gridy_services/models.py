from gridy_auth.models import Barangay
from django.conf import settings
from django.utils import timezone

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.core.exceptions import ValidationError
from django.db import models, transaction

MANILA_TIME_ZONE = ZoneInfo("Asia/Manila")

# Create your models here.

class PaymentRecipient(models.Model):
    class Provider(models.TextChoices):
        GCASH = "GCASH", "GCash"
        MAYA = "MAYA", "Maya"
        BANK = "BANK", "Bank transfer"
        OTHER = "OTHER", "Other"

    barangay = models.ForeignKey(
        Barangay,
        on_delete=models.CASCADE,
        related_name="payment_recipients",
    )
    provider = models.CharField(max_length=16, choices=Provider.choices)
    display_name = models.CharField(max_length=100)
    recipient_name = models.CharField(max_length=255)
    recipient_identifier = models.CharField(max_length=100)
    instructions = models.TextField(blank=True, max_length=1000)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["provider", "display_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["barangay", "provider", "display_name"],
                name="unique_payment_recipient_per_barangay",
            ),
        ]

    def __str__(self):
        return f"{self.get_provider_display()} — {self.display_name}"


class DocumentRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PROCESSING = 'PROCESSING', 'Processing'
        READY_FOR_PICKUP = 'READY_FOR_PICKUP', 'Ready for Pickup'
        REJECTED = 'REJECTED', 'Rejected'
        RELEASED = 'RELEASED', 'Released'

    class UrgencyTag(models.TextChoices):
        REGULAR = 'REGULAR', 'Regular'
        URGENT = 'URGENT', 'Urgent'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='document_requests'
    )
    barangay = models.ForeignKey(
        Barangay,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='document_requests'
    )
    # Walk-in & Legacy Support
    is_walkin = models.BooleanField(default=False, db_index=True)
    walkin_name = models.CharField(max_length=255, blank=True, null=True)
    walkin_purok = models.CharField(max_length=100, blank=True, null=True)
    privacy_notice_version = models.CharField(max_length=64, blank=True, null=True)
    privacy_acknowledged_at = models.DateTimeField(blank=True, null=True)

    document_type = models.CharField(max_length=100)
    purpose = models.TextField(blank=True, null=True)
    urgency_tag = models.CharField(
        max_length=20,
        choices=UrgencyTag.choices,
        default=UrgencyTag.REGULAR,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    admin_notes = models.TextField(blank=True, null=True)

    class PaymentMethod(models.TextChoices):
        CASH = "CASH", "Cash"
        GCASH = "GCASH", "GCash"
        MAYA = "MAYA", "Maya"
        BANK = "BANK", "Bank transfer"
        OTHER = "OTHER", "Other"

    class PaymentStatus(models.TextChoices):
        NOT_REQUIRED = "NOT_REQUIRED", "Not required"
        UNPAID = "UNPAID", "Unpaid"
        PENDING_VERIFICATION = "PENDING_VERIFICATION", "Pending verification"
        VERIFIED = "VERIFIED", "Verified"
        REJECTED = "REJECTED", "Rejected"

    # Official Receipt (OR) & Fee Auditing
    or_number = models.CharField(max_length=50, blank=True, null=True, help_text="Official Receipt Number issued by Barangay Treasurer")
    fee_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0.00, help_text="Clearance issuance fee in PHP")

    class FeeAssessmentStatus(models.TextChoices):
        AWAITING_ASSESSMENT = "AWAITING_ASSESSMENT", "Awaiting Assessment"
        ASSESSED = "ASSESSED", "Staff-Assessed Fee"
        WAIVED = "WAIVED", "Staff-Approved Waiver"
        STATUTORY_EXEMPT = "STATUTORY_EXEMPT", "Statutory Exemption"

    fee_assessment_status = models.CharField(
        max_length=25,
        choices=FeeAssessmentStatus.choices,
        default=FeeAssessmentStatus.AWAITING_ASSESSMENT,
        help_text="Explicit provenance of clearance fee determination.",
    )
    fee_assessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assessed_document_requests",
        help_text="Barangay staff member who assessed or waived the clearance fee.",
    )
    fee_assessed_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Timestamp when the clearance fee was assessed or waived.",
    )
    fee_waiver_reason = models.TextField(
        blank=True,
        help_text="Mandatory written justification when an ordinary fee is waived by staff.",
    )

    payment_method = models.CharField(
        max_length=12,
        choices=PaymentMethod.choices,
        blank=True,
    )
    payment_recipient = models.ForeignKey(
        PaymentRecipient,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="document_requests",
    )
    payment_recipient_name_snapshot = models.CharField(max_length=255, blank=True)
    payment_recipient_identifier_snapshot = models.CharField(max_length=100, blank=True)
    payment_instructions_snapshot = models.TextField(blank=True)
    payment_reference = models.CharField(max_length=100, blank=True)
    payment_status = models.CharField(
        max_length=25,
        choices=PaymentStatus.choices,
        default=PaymentStatus.NOT_REQUIRED,
    )
    payment_review_note = models.TextField(blank=True)
    payment_proof_image = models.ImageField(
        upload_to="payment_proofs/",
        blank=True,
        null=True,
        help_text="Private receipt screenshot for manual electronic payment verification.",
    )
    payment_transacted_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Resident-reported timestamp of the fund transfer.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        super().clean()
        if (
            self.status == self.Status.RELEASED
            and self.fee_amount > 0
            and not (self.or_number or "").strip()
        ):
            raise ValidationError({
                "or_number": (
                    "An Official Receipt (O.R.) number is required before releasing a document with a fee."
                )
            })

    def __str__(self):
        applicant = self.user.username if self.user else f"Walk-in: {self.walkin_name}"
        return f"{self.document_type} - {applicant} ({self.status})"

    class Meta:
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['barangay', 'status']),
            models.Index(fields=['status']),
        ]

class AidRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending review"
        UNDER_REVIEW = "UNDER_REVIEW", "Under review"
        APPROVED = "APPROVED", "Approved"
        DECLINED = "DECLINED", "Declined"

    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="aid_requests",
    )
    barangay = models.ForeignKey(
        Barangay,
        on_delete=models.CASCADE,
        related_name="aid_requests",
    )
    assistance_type = models.CharField(max_length=100)
    reason = models.TextField(max_length=2000)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    staff_notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_aid_requests",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["barangay", "status", "created_at"]),
            models.Index(fields=["requester", "created_at"]),
        ]
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.assistance_type} request by {self.requester_id} ({self.status})"


class QueueTicket(models.Model):
    class Status(models.TextChoices):
        WAITING = 'WAITING', 'Waiting'
        SERVING = 'SERVING', 'Serving'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    class Priority(models.TextChoices):
        REGULAR = 'regular', 'Regular'
        PRIORITY = 'priority', 'Priority/Senior/PWD/Pregnant'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='queue_tickets'
    )

    barangay = models.ForeignKey(
        Barangay,
        on_delete=models.CASCADE,
        null=True,
        related_name='queue_tickets'
    )
    ticket_number = models.CharField(max_length=20)
    service_type = models.CharField(max_length=100)
    # New Fields for Manual Entry
    walkin_name = models.CharField(max_length=255, blank=True, null=True)
    priority_status = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.REGULAR,
    )
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.WAITING,
    )
    is_priority = models.BooleanField(default=False)
    privacy_notice_version = models.CharField(max_length=64, blank=True, null=True)
    privacy_acknowledged_at = models.DateTimeField(blank=True, null=True)
    called_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Ticket {self.ticket_number} ({self.status})"


    def save(self, *args, **kwargs):
        if self.ticket_number:
            return super().save(*args, **kwargs)

        if self.barangay_id is None:
            raise ValidationError(
                "A barangay is required to assign a queue ticket number."
            )

        with transaction.atomic():
            Barangay.objects.select_for_update().get(pk=self.barangay_id)

            manila_now = timezone.localtime(
                timezone.now(),
                MANILA_TIME_ZONE,
            )
            manila_day_start = datetime.combine(
                manila_now.date(),
                time.min,
                tzinfo=MANILA_TIME_ZONE,
            )
            next_manila_day_start = manila_day_start + timedelta(days=1)

            existing_numbers = QueueTicket.objects.filter(
                barangay_id=self.barangay_id,
                created_at__gte=manila_day_start,
                created_at__lt=next_manila_day_start,
            ).values_list("ticket_number", flat=True)

            highest_number = max(
                (
                    int(number[1:])
                    for number in existing_numbers
                    if number.startswith("T") and number[1:].isdigit()
                ),
                default=0,
            )

            self.ticket_number = f"T{highest_number + 1:03d}"
            super().save(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['created_at']),
            models.Index(fields=['barangay', 'called_at'], name='gridy_queue_call_idx'),
        ]
            
