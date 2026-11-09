from rest_framework import serializers

from gridy_auth.models import Barangay, LoginEvent, ResidentTransferRequest, User
from gridy_auth.serializers.base import ResidentEvidenceImageField


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
    purok = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        default="",
    )
    address_details = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        default="",
    )
    proof_of_residency = ResidentEvidenceImageField(
        required=True,
        allow_null=False,
    )

    class Meta:
        model = ResidentTransferRequest
        fields = [
            "destination_barangay_id",
            "reason",
            "purok",
            "address_details",
            "proof_of_residency",
        ]

    def validate_reason(self, value):
        reason = value.strip()
        if not reason:
            raise serializers.ValidationError("Explain why you are requesting this transfer.")
        return reason

    def validate_purok(self, value):
        return value.strip()

    def validate_address_details(self, value):
        return value.strip()

    def validate_proof_of_residency(self, value):
        if not value:
            raise serializers.ValidationError(
                "Upload proof of residency to request a Barangay transfer."
            )
        return value

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
    resident_id = serializers.IntegerField(source="resident.id", read_only=True)
    resident_name = serializers.CharField(source="resident.profile.full_name", read_only=True)
    resident_username = serializers.CharField(source="resident.username", read_only=True)
    source_barangay_id = serializers.IntegerField(source="source_barangay.id", read_only=True)
    source_barangay_name = serializers.CharField(source="source_barangay.name", read_only=True)
    destination_barangay_id = serializers.IntegerField(source="destination_barangay.id", read_only=True)
    destination_barangay_name = serializers.CharField(source="destination_barangay.name", read_only=True)
    has_proof_of_residency = serializers.SerializerMethodField()

    class Meta:
        model = ResidentTransferRequest
        fields = [
            "id", "resident_id", "resident_name", "resident_username",
            "source_barangay_id", "source_barangay_name",
            "destination_barangay_id", "destination_barangay_name",
            "purok", "address_details", "has_proof_of_residency",
            "reason", "status", "review_note", "residency_confirmed",
            "created_at", "reviewed_at",
        ]
        read_only_fields = fields

    def get_has_proof_of_residency(self, obj) -> bool:
        return bool(obj.proof_of_residency and obj.proof_of_residency.name)


class ResidentTransferReviewSerializer(serializers.Serializer):
    residency_confirmed = serializers.BooleanField(required=False, default=False)
    review_note = serializers.CharField(max_length=500, required=False, allow_blank=True)

    def validate_review_note(self, value):
        return value.strip()
