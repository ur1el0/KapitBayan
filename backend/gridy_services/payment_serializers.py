from rest_framework import serializers

from gridy_services.models import OfficialReceiptSeries, PaymentRecipient


class PaymentRecipientSerializer(serializers.ModelSerializer):
    provider_label = serializers.CharField(source="get_provider_display", read_only=True)

    class Meta:
        model = PaymentRecipient
        fields = [
            "id",
            "provider",
            "provider_label",
            "display_name",
            "recipient_name",
            "recipient_identifier",
            "instructions",
            "is_active",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]

    def validate(self, attrs):
        for field in (
            "display_name",
            "recipient_name",
            "recipient_identifier",
            "instructions",
        ):
            if field in attrs and isinstance(attrs[field], str):
                attrs[field] = attrs[field].strip()
        return attrs


class OfficialReceiptSeriesSerializer(serializers.ModelSerializer):
    configured = serializers.BooleanField(source="is_configured", read_only=True)

    class Meta:
        model = OfficialReceiptSeries
        fields = [
            "prefix",
            "next_number",
            "number_width",
            "last_issued_number",
            "configured",
            "updated_at",
        ]
        read_only_fields = ["last_issued_number", "configured", "updated_at"]
        extra_kwargs = {
            "prefix": {"required": True, "allow_blank": False, "max_length": 40},
            "next_number": {"required": True, "min_value": 1},
            "number_width": {"required": True, "min_value": 0, "max_value": 12},
        }

    def validate_prefix(self, value):
        value = value.strip()
        if not value or any(ord(character) < 32 for character in value):
            raise serializers.ValidationError("Enter the exact prefix from the Barangay-approved receipt series.")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        instance = self.instance
        if instance is None:
            return attrs

        prefix_changed = attrs.get("prefix", instance.prefix) != instance.prefix
        if instance.last_issued_number is not None:
            if (
                attrs.get("number_width", instance.number_width) != instance.number_width
                and not prefix_changed
            ):
                raise serializers.ValidationError({
                    "number_width": "To change serial width, start a new approved series by changing its prefix."
                })

        requested_next = attrs.get("next_number", instance.next_number)
        if prefix_changed and "next_number" not in attrs:
            raise serializers.ValidationError({
                "next_number": "Enter the next unused serial when starting a new receipt series."
            })
        if not prefix_changed and requested_next < instance.next_number:
            raise serializers.ValidationError({
                "next_number": "The next serial cannot move backwards."
            })
        return attrs

    def update(self, instance, validated_data):
        if validated_data.get("prefix", instance.prefix) != instance.prefix:
            # Per-series state resets; historical numbers remain on their requests.
            validated_data["last_issued_number"] = None
        return super().update(instance, validated_data)
