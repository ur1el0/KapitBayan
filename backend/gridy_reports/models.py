from random import choices
from django.db import models
from django.conf import settings
from django.utils import timezone

class IssueReport(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        RESOLVED = 'RESOLVED', 'Resolved'

    class Urgency(models.TextChoices):
        MINOR = 'MINOR', 'Minor'
        MODERATE = 'MODERATE', 'Moderate'
        HAZARD = 'HAZARD', 'Hazard'
        EMERGENCY = 'EMERGENCY', 'Emergency'

    class Category(models.TextChoices):
        PEACE_AND_ORDER = 'PEACE_AND_ORDER', 'Peace & Order (Riots, Noise, Curfew)'
        PUBLIC_HEALTH = 'PUBLIC_HEALTH', 'Public Health (Vaccinations, Medical)'
        INFRASTRUCTURE = 'INFRASTRUCTURE', 'Infrastructure (Potholes, Outages)'
        ENVIRONMENT = 'ENVIRONMENT', 'Environment (Floods, Waste)'
        OTHER = 'OTHER', 'Other'

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='issue_reports'
    )
    barangay = models.ForeignKey(
        'gridy_auth.Barangay',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='issue_reports',
    )
    walkin_name = models.CharField(max_length=255, blank=True, null=True)
    privacy_notice_version = models.CharField(max_length=64, blank=True, null=True)
    privacy_acknowledged_at = models.DateTimeField(blank=True, null=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    location = models.CharField(max_length=255, help_text="A brief description of where the issue is located.")
    # Image uploads will be handled by Cloudinary because of DEFAULT_FILE_STORAGE
    image = models.ImageField(upload_to='issue_reports/', blank=True, null=True)
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.PENDING
    )
    urgency = models.CharField(max_length=20, choices=Urgency.choices, default=Urgency.MINOR)
    category = models.CharField(max_length=50, choices=Category.choices, default=Category.OTHER)
    incident_datetime = models.DateTimeField(null=True, blank=True, help_text="Exact time the scenario occurred.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"[{self.get_category_display()}] {self.title} - {self.get_status_display()}"


