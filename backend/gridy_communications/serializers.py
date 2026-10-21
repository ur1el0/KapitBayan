from rest_framework import serializers
from gridy_auth.models import User
from gridy_communications.models import (
    Announcement,
    ActivitySchedule,
    FCMDevice,
    EmergencyHotline,
    FAQ,
    AdminNotification,
    ResidentNotification,
)

class FCMDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = FCMDevice
        fields = ['id', 'token', 'created_at']


class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = '__all__'
        read_only_fields = ['created_by']

    def validate_image(self, value):
        if value:
            max_size = 5 * 1024 * 1024 # 5 Megabytes
            if value.size > max_size:
                raise serializers.ValidationError("Image file size cannot exceed 5MB. Please compress your image.")
            return value


class PublicAnnouncementSerializer(serializers.ModelSerializer):
    barangay_id = serializers.IntegerField(source="created_by.barangay_id", read_only=True)

    class Meta:
        model = Announcement
        fields = ["id", "barangay_id", "title", "content", "is_pinned", "created_at"]
        read_only_fields = fields


class ActivityScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivitySchedule
        fields = '__all__'
        read_only_fields = ['created_by']

class EmergencyHotlineSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(
        source='get_category_display', read_only=True
    )

    class Meta:
        model = EmergencyHotline
        fields = ['id', 'name', 'number', 'category', 'category_display', 'is_active', 'created_by']
        read_only_fields = ['created_by']

class FAQSerializer(serializers.ModelSerializer):
    barangay_id = serializers.IntegerField(read_only=True)
    barangay_name = serializers.CharField(source='barangay.name', read_only=True, allow_null=True)
    scope = serializers.SerializerMethodField()

    class Meta:
        model = FAQ
        fields = [
            'id', 'question', 'answer', 'order', 'audience', 'category',
            'is_published', 'barangay_id', 'barangay_name', 'scope',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'barangay_id', 'barangay_name', 'scope', 'created_at', 'updated_at']

    def get_scope(self, obj) -> str:
        return 'GLOBAL' if obj.barangay_id is None else 'BARANGAY'

    def validate_audience(self, value):
        request = self.context.get('request')
        if request and getattr(request.user, 'role', None) == User.Role.ADMIN and value != FAQ.Audience.RESIDENT:
            raise serializers.ValidationError('Barangay admins can manage resident FAQs only.')
        return value

class AdminNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminNotification
        fields = [
            'id', 'notification_type', 'title', 'message', 'is_read',
            'created_at',
        ]
        read_only_fields = fields


class AdminNotificationReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminNotification
        fields = ['is_read']


class ResidentNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResidentNotification
        fields = [
            'id', 'notification_type', 'title', 'message', 'data',
            'is_read', 'created_at',
        ]
        read_only_fields = fields
