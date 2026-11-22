from pathlib import PurePosixPath
from PIL import Image, UnidentifiedImageError
from rest_framework import serializers
from .models import IssueReport

ALLOWED_REPORT_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}
ALLOWED_REPORT_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_REPORT_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MiB


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
            if value.size > MAX_REPORT_IMAGE_SIZE_BYTES:
                raise serializers.ValidationError(
                    "Image file size cannot exceed 5MB. Please compress your image."
                )

            filename = getattr(value, "name", "")
            if filename:
                if "\x00" in filename:
                    raise serializers.ValidationError("Invalid image filename.")
                ext = PurePosixPath(filename).suffix.lower()
                if ext not in ALLOWED_REPORT_IMAGE_EXTENSIONS:
                    raise serializers.ValidationError(
                        "Unsupported image file extension. Allowed extensions are .jpg, .jpeg, .png, .webp."
                    )

            try:
                with Image.open(value) as img:
                    img_format = img.format
                if img_format not in ALLOWED_REPORT_IMAGE_FORMATS:
                    raise serializers.ValidationError(
                        "Unsupported image format. Allowed formats are JPEG, PNG, and WebP."
                    )
            except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
                raise serializers.ValidationError("Uploaded file is not a valid image.")
            finally:
                if hasattr(value, "seek"):
                    value.seek(0)
        return value
