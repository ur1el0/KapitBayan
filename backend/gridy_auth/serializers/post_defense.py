from rest_framework import serializers

from gridy_auth.models import Barangay, LoginEvent, ResidentTransferRequest, User


class LoginEventSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    role = serializers.CharField(source="user.role", read_only=True)

    class Meta:
        model = LoginEvent
        fields = ["id", "user_id", "username", "role", "ip_address", "user_agent", "created_at"]
        read_only_fields = fields


class ResidentTransferCreateSerializer(serializers.ModelSerializer):
    destination_barangay_id = serializers.PrimaryKeyRelatedField(
        source="destination_barangay",
        queryset=Barangay.get_eligible_for_registration(),
        write_only=True,
    )

    class Meta:
        model = ResidentTransferRequest
        fields = ["destination_barangay_id", "reason"]

    def validate_reason(self, value):
        reason = value.strip()
        if not reason:
            raise serializers.ValidationError("Explain why you are requesting this transfer.")
        return reason

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        destination = attrs["destination_barangay"]

        if not user or user.role != User.Role.RESIDENT or user.barangay_id is None:
            raise serializers.ValidationError({
                "detail": "Only a resident assigned to a Barangay can request a transfer."
            })
        if destination.pk == user.barangay_id:
            raise serializers.ValidationError({
                "destination_barangay_id": "Choose a different Barangay from your current one."
            })
        if ResidentTransferRequest.objects.filter(
            resident=user,
            status=ResidentTransferRequest.Status.PENDING,
        ).exists():
            raise serializers.ValidationError({
                "detail": "You already have a Barangay transfer request awaiting review."
            })
        return attrs


class ResidentTransferRequestSerializer(serializers.ModelSerializer):
    resident_name = serializers.CharField(source="resident.profile.full_name", read_only=True)
    resident_username = serializers.CharField(source="resident.username", read_only=True)
    source_barangay_name = serializers.CharField(source="source_barangay.name", read_only=True)
    destination_barangay_name = serializers.CharField(source="destination_barangay.name", read_only=True)

    class Meta:
        model = ResidentTransferRequest
        fields = [
            "id", "resident_name", "resident_username", "source_barangay_name",
            "destination_barangay_id", "destination_barangay_name", "reason", "status",
            "review_note", "residency_confirmed", "created_at", "reviewed_at",
        ]
        read_only_fields = fields


class ResidentTransferReviewSerializer(serializers.Serializer):
    residency_confirmed = serializers.BooleanField(required=False, default=False)
    review_note = serializers.CharField(max_length=500, required=False, allow_blank=True)

    def validate_review_note(self, value):
        return value.strip()
