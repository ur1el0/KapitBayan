from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.utils import timezone
from uuid import uuid4
from pathlib import PurePosixPath

# Create your models here.


def barangay_authority_proof_upload_to(_instance, filename):
    """Use an opaque private path; the serializer has already checked the suffix."""
    suffix = PurePosixPath(filename).suffix.lower()
    if suffix not in {".pdf", ".jpg", ".png"}:
        suffix = ".bin"
    return f"barangay_onboarding/{uuid4().hex}{suffix}"

class Barangay(models.Model):
    name = models.CharField(max_length=255)
    municipality = models.CharField(max_length=120, blank=True, default="")
    province = models.CharField(max_length=120, blank=True, default="")
    primary_color = models.CharField(
        max_length=7,
        default="#082B66",
        validators=[
            RegexValidator(
                regex=r"^#[0-9A-Fa-f]{6}$",
                message="Enter a valid hex color in #RRGGBB format.",
            )
        ],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    logo = models.ImageField(upload_to='barangay_logos/', blank=True, null=True)
    city_seal = models.ImageField(upload_to='barangay_logos/', blank=True, null=True)
    captain_name = models.CharField(max_length=255, blank=True, null=True, help_text="Full name of the incumbent Punong Barangay")
    office_contact = models.CharField(max_length=255, blank=True, null=True, help_text="Office Address or Phone Number")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("name"),
                Lower("municipality"),
                Lower("province"),
                condition=~Q(municipality="") & ~Q(province=""),
                name="unique_barangay_locality",
            ),
        ]

    def __str__(self):
        if self.municipality and self.province:
            return f"{self.name} ({self.municipality}, {self.province})"
        return self.name


class BarangayApplication(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending review"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    name = models.CharField(max_length=255)
    municipality = models.CharField(max_length=120)
    province = models.CharField(max_length=120)
    applicant_name = models.CharField(max_length=255)
    applicant_position = models.CharField(max_length=120)
    applicant_email = models.EmailField()
    applicant_phone = models.CharField(max_length=30)
    proof_of_authority = models.FileField(
        upload_to=barangay_authority_proof_upload_to,
        blank=True,
        help_text="Private supporting evidence, removed after a review decision.",
    )
    email_verified_at = models.DateTimeField(null=True, blank=True)
    email_verification_sent_at = models.DateTimeField(null=True, blank=True)
    admin_username = models.CharField(max_length=150, blank=True, default="")
    applicant_user = models.OneToOneField(
        "gridy_auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="barangay_admin_application",
    )
    applicant_authorized = models.BooleanField(default=False)
    contact_consent = models.BooleanField(default=False)
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    review_note = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        "gridy_auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_barangay_applications",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_verified = models.BooleanField(default=False)
    proof_reviewed = models.BooleanField(default=False)
    created_barangay = models.ForeignKey(
        Barangay,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="onboarding_application",
    )
    created_admin = models.ForeignKey(
        "gridy_auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="first_admin_onboarding_applications",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                Lower("name"),
                Lower("municipality"),
                Lower("province"),
                condition=Q(status="PENDING"),
                name="unique_pending_barangay_application",
            ),
            models.UniqueConstraint(
                Lower("admin_username"),
                condition=Q(status="PENDING") & ~Q(admin_username=""),
                name="unique_pending_admin_username",
            ),
            models.UniqueConstraint(
                Lower("applicant_email"),
                condition=Q(status="PENDING") & ~Q(admin_username=""),
                name="unique_pending_admin_email",
            ),
            models.UniqueConstraint(
                Lower("applicant_email"),
                condition=Q(status="PENDING") & Q(applicant_user__isnull=False),
                name="unique_pending_linked_admin_email",
            ),
        ]

    def __str__(self):
        return f"{self.name}, {self.municipality} ({self.get_status_display()})"


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        RESIDENT = 'RESIDENT', 'Resident'
        FIELD_OFFICIAL = 'FIELD_OFFICIAL', 'Field Official'
        DILG_ADMIN = 'DILG_ADMIN', 'DILG Onboarding Reviewer'

    role = models.CharField(
        max_length=50,
        choices=Role.choices,
        default=Role.RESIDENT,
    )

    barangay = models.ForeignKey(
        Barangay,
        on_delete=models.CASCADE,
        null=True,
        related_name='users'
    )

    email_alerts = models.BooleanField(
        default=True,
        help_text="Receive daily queue and request email reports"
    )
    push_alerts = models.BooleanField(
        default=False,
        help_text="Receieve real-time FCM push notifications"
    )
        
class Resident(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    full_name = models.CharField(max_length=255)
    birth_date = models.DateField()
    voter_status = models.BooleanField(default=False)
    contact_number = models.CharField(max_length=20, null=True, blank=True)
    purok = models.CharField(max_length=100, null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    guardian = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='dependents')
    privacy_consent_version = models.CharField(
        max_length=64,
        null=True,
        blank=True,
    )
    privacy_consent_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    # Identification & Proof of Residency
    philsys_id_number = models.CharField(max_length=50, blank=True, null=True, help_text="PhilSys National ID Card Number")
    philsys_id_photo = models.ImageField(upload_to='resident_ids/', blank=True, null=True, help_text="Photo of National / PhilSys ID")
    secondary_id_type = models.CharField(max_length=50, blank=True, null=True, help_text="Optional secondary ID type (e.g. Passport, Driver's License, UMID, Postal ID)")
    secondary_id_photo = models.ImageField(upload_to='resident_ids/', blank=True, null=True, help_text="Optional secondary ID photo")
    utility_billing_type = models.CharField(max_length=50, blank=True, null=True, help_text="Optional utility billing proof type (e.g. Electric/Meralco, Water, Internet)")
    utility_billing_photo = models.ImageField(upload_to='resident_billings/', blank=True, null=True, help_text="Optional proof of billing photo")


    def __str__(self):
        return f'{self.full_name}'


class RefreshSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    refresh_token_jti = models.CharField(max_length=255, unique=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_revoked = models.BooleanField(default=False)

    def __str__(self):
        return f"Session for {self.user.username} (JTI: {self.refresh_token_jti[:8]})"


class PrivateMediaCleanup(models.Model):
    """Durable, non-user-linked work item for deleting private evidence."""

    class ResidentField(models.TextChoices):
        PHILSYS_ID_PHOTO = "philsys_id_photo", "PhilSys ID photo"
        SECONDARY_ID_PHOTO = "secondary_id_photo", "Secondary ID photo"
        UTILITY_BILLING_PHOTO = "utility_billing_photo", "Utility billing photo"
        PROOF_OF_AUTHORITY = "proof_of_authority", "Barangay authority proof"

    field_name = models.CharField(max_length=32, choices=ResidentField.choices)
    storage_model = models.CharField(
        max_length=64,
        default="gridy_auth.Resident",
        help_text="Allowlisted model that owns the private media storage field.",
    )
    encrypted_file_name = models.TextField()
    attempt_count = models.PositiveIntegerField(default=0)
    next_attempt_at = models.DateTimeField(default=timezone.now, db_index=True)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    last_error_code = models.CharField(max_length=128, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "pk"]

    def __str__(self):
        return f"Private media cleanup #{self.pk}"


class APIRateLimitWindow(models.Model):
    """Rolling-window request timestamps shared by all API workers.

    The primary key is a keyed digest of a throttle scope and client identity;
    raw IP addresses and user identifiers are not stored in this table.
    """

    window_key = models.CharField(max_length=64, primary_key=True)
    history = models.JSONField(default=list)
    expires_at = models.DateTimeField(db_index=True)

    class Meta:
        ordering = ["expires_at"]
