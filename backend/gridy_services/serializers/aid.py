from rest_framework import serializers
from ..models import AidRequest


class AidRequestSerializer(serializers.ModelSerializer):
    requester_name = serializers.SerializerMethodField()

    class Meta:
        model = AidRequest
        fields = [
            "id",
            "requester_name",
            "assistance_type",
            "reason",
            "status",
            "staff_notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "status",
            "staff_notes",
            "created_at",
            "updated_at",
        ]

    def get_requester_name(self, obj) -> str:
        if obj.requester is None:
            return "Former resident"

        profile = getattr(obj.requester, "profile", None)
        return (
            profile.full_name
            if profile and profile.full_name
            else obj.requester.username
        )


class AidRequestReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = AidRequest
        fields = ["status", "staff_notes"]

    def validate_status(self, value):
        if value not in {
            AidRequest.Status.UNDER_REVIEW,
            AidRequest.Status.APPROVED,
            AidRequest.Status.DECLINED,
        }:
            raise serializers.ValidationError("Select a valid review status.")
        return value

    def validate(self, attrs):
        status_value = attrs.get(
            "status",
            getattr(self.instance, "status", None),
        )
        notes = attrs.get(
            "staff_notes",
            getattr(self.instance, "staff_notes", ""),
        )
        if status_value == AidRequest.Status.DECLINED and not notes.strip():
            raise serializers.ValidationError({
                "staff_notes": (
                    "A reason is required when declining an assistance request."
                )
            })
        return attrs
