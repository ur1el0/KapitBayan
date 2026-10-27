import datetime
import os
from django.utils import timezone
from PIL import Image
from rest_framework import serializers

from ..models import DocumentRequest


class PaymentChoiceSerializer(serializers.Serializer):
    payment_method = serializers.ChoiceField(
        choices=(DocumentRequest.PaymentMethod.CASH,),
        required=False,
    )
    payment_recipient_id = serializers.IntegerField(min_value=1, required=False)

    def validate(self, attrs):
        selects_cash = attrs.get("payment_method") == DocumentRequest.PaymentMethod.CASH
        selects_electronic_recipient = "payment_recipient_id" in attrs
        if selects_cash == selects_electronic_recipient:
            raise serializers.ValidationError(
                "Select cash or one active e-payment recipient configured by your barangay."
            )
        return attrs


class PaymentReferenceSerializer(serializers.Serializer):
    payment_recipient_id = serializers.IntegerField(min_value=1)
    payment_reference = serializers.CharField(
        max_length=100,
        min_length=3,
        allow_blank=False,
        trim_whitespace=True,
    )
    payment_transacted_at = serializers.DateTimeField()
    payment_proof_image = serializers.ImageField()

    def validate_payment_transacted_at(self, value):
        now = timezone.now()
        if value > now + datetime.timedelta(minutes=5):
            raise serializers.ValidationError("Transaction timestamp cannot be in the future.")
        return value

    def validate_payment_proof_image(self, value):
        max_size = 5 * 1024 * 1024  # 5 MB
        if value.size > max_size:
            raise serializers.ValidationError("Payment proof image must not exceed 5 MB.")

        try:
            value.seek(0)
            img = Image.open(value)
            fmt = img.format
            width, height = img.size
            img.verify()
            if fmt not in ("JPEG", "PNG", "WEBP"):
                raise serializers.ValidationError(
                    "Only JPEG, PNG, and WEBP image formats are supported."
                )
            if width <= 0 or height <= 0:
                raise serializers.ValidationError("Image must have valid positive dimensions.")
            extension = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}[fmt]
            filename = os.path.basename(value.name or "payment-proof")
            stem = os.path.splitext(filename)[0] or "payment-proof"
            value.name = f"{stem}{extension}"
            value.seek(0)
        except serializers.ValidationError:
            raise
        except Exception:
            raise serializers.ValidationError("Invalid or unreadable image file.")
        return value


class PaymentReviewSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=(
            DocumentRequest.PaymentStatus.VERIFIED,
            DocumentRequest.PaymentStatus.REJECTED,
        )
    )
    note = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        trim_whitespace=True,
    )
    or_number = serializers.CharField(
        max_length=50,
        required=False,
        allow_blank=True,
        trim_whitespace=True,
    )

    def validate(self, attrs):
        if (
            attrs["status"] == DocumentRequest.PaymentStatus.REJECTED
            and not attrs.get("note", "").strip()
        ):
            raise serializers.ValidationError({
                "note": "A reason is required when rejecting a transfer."
            })
        return attrs
