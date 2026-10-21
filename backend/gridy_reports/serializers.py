from rest_framework import serializers
from .models import IssueReport

class IssueReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = IssueReport
        fields = '__all__'
        read_only_fields = [
            'reporter', 'barangay', 'walkin_name',
            'privacy_notice_version', 'privacy_acknowledged_at',
        ]

    def validate_image(self, value):
        if value:
            max_size = 5 * 1024 * 1024 # 5 Megabytes in bytes
            if value.size > max_size:
                raise serializers.ValidationError("Image file size cannot exceed 5MB. Please compress your image.")
        return value

