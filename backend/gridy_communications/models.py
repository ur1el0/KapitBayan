from django.db import models
from django.conf import settings


# Create your models here.

class Announcement(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    image = models.ImageField(upload_to='announcements/', blank=True, null=True)
    is_pinned = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='announcements')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        indexes = [
            models.Index(fields=['is_pinned', 'created_at']),
        ]


class ActivitySchedule(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    event_datetime = models.DateTimeField()
    location = models.CharField(max_length=255)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='activities')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class FCMDevice(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name="fcm_devices"
    )

    # FCM reg tokens are typically long strs (up to 255+ chars)
    token = models.TextField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s Device ({self.token[:20]}...)"

class EmergencyHotline(models.Model):
    class Category(models.TextChoices):
        POLICE = 'POLICE', 'Police'
        FIRE = 'FIRE', 'Fire Department'
        MEDICAL = 'MEDICAL', 'Medical / Hospital'
        BARANGAY = 'BARANGAY', 'Barangay Desk'
        OTHER = 'OTHER', 'Other'

    name = models.CharField(max_length=255)
    number = models.CharField(max_length=50)
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.OTHER
    )
    # Security: Track which barangay admin created this hotline
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='hotlines'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.number}"
    
    class Meta:
        ordering = ['category', 'name']


class FAQ(models.Model):
    class Audience(models.TextChoices):
        RESIDENT = 'RESIDENT', 'Residents'
        STAFF = 'STAFF', 'Staff'

    class Category(models.TextChoices):
        GETTING_STARTED = 'GETTING_STARTED', 'Getting started'
        ACCOUNT = 'ACCOUNT', 'Account access'
        DOCUMENTS = 'DOCUMENTS', 'Documents and clearances'
        PAYMENTS = 'PAYMENTS', 'Fees and payments'
        QUEUE = 'QUEUE', 'Queue and schedules'
        ASSISTANCE = 'ASSISTANCE', 'Assistance and programs'
        COMMUNITY = 'COMMUNITY', 'Community notices'
        ACCESSIBILITY = 'ACCESSIBILITY', 'Accessibility and older adults'
        PRIVACY = 'PRIVACY', 'Privacy and safety'
        OTHER = 'OTHER', 'Other'

    question = models.CharField(max_length=255)
    answer = models.TextField()
    order = models.IntegerField(default=0, help_text="Order in which the FAQ appears")
    audience = models.CharField(
        max_length=16,
        choices=Audience.choices,
        default=Audience.STAFF,
        db_index=True,
    )
    category = models.CharField(
        max_length=24,
        choices=Category.choices,
        default=Category.OTHER,
        db_index=True,
    )
    is_published = models.BooleanField(default=False, db_index=True)
    barangay = models.ForeignKey(
        'gridy_auth.Barangay',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='faqs',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.question
    
    class Meta:
        ordering = ['order', 'created_at', 'id']
        indexes = [
            models.Index(fields=['audience', 'is_published', 'category']),
            models.Index(fields=['barangay', 'audience', 'is_published']),
        ]

class AdminNotification(models.Model):
    class Type(models.TextChoices):
        QUEUE = 'queue', 'Queue Alert'
        DOCUMENT = 'document', 'Document Request'
        REPORT = 'report', 'Issue Report'
        REGISTRATION = 'registration', 'Resident Registration'
        SYSTEM = 'system', 'System Update'
        ALERT = 'alert', 'Security/Verification Alert'
        
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='admin_notifications',
        help_text="The specific admin receiving the alert"
    )
    notification_type = models.CharField(
        max_length=20,
        choices=Type.choices,
        default=Type.SYSTEM
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.get_notification_type_display()}] {self.title} for {self.user.username}"
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', '-created_at']),
        ]


class ResidentNotification(models.Model):
    class Type(models.TextChoices):
        QUEUE = 'queue', 'Queue Alert'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='resident_notifications',
    )
    notification_type = models.CharField(
        max_length=20,
        choices=Type.choices,
        default=Type.QUEUE,
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    data = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.get_notification_type_display()}] {self.title}"

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(
                fields=['user', 'is_read', '-created_at'],
                name='gridy_res_user_read_idx',
            ),
        ]
