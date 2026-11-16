from rest_framework import serializers
from ..models import EquipmentBorrowRequest


class EquipmentBorrowRequestSerializer(serializers.ModelSerializer):
    resident_name = serializers.SerializerMethodField()
    reviewed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = EquipmentBorrowRequest
        fields = [
            "id",
            "resident",
            "resident_name",
            "item_type",
            "quantity",
            "borrow_date",
            "return_date",
            "time_slot",
            "purpose",
            "status",
            "admin_notes",
            "reviewed_by",
            "reviewed_by_name",
            "reviewed_at",
            "returned_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "resident",
            "resident_name",
            "status",
            "admin_notes",
            "reviewed_by",
            "reviewed_by_name",
            "reviewed_at",
            "returned_at",
            "created_at",
            "updated_at",
        ]

    def get_resident_name(self, obj) -> str:
        if obj.resident is None:
            return "Former resident"

        profile = getattr(obj.resident, "profile", None)
        return (
            profile.full_name
            if profile and profile.full_name
            else obj.resident.username
        )

    def get_reviewed_by_name(self, obj) -> str | None:
        if obj.reviewed_by is None:
            return None
        profile = getattr(obj.reviewed_by, "profile", None)
        return (
            profile.full_name
            if profile and profile.full_name
            else obj.reviewed_by.username
        )

    def validate_quantity(self, value):
        if value is None or value < 1:
            raise serializers.ValidationError("Quantity must be at least 1.")
        return value

    def validate_purpose(self, value):
        cleaned = (value or "").strip()
        if not cleaned:
            raise serializers.ValidationError("Purpose is required.")
        return cleaned

    def validate(self, attrs):
        borrow_date = attrs.get(
            "borrow_date",
            getattr(self.instance, "borrow_date", None),
        )
        return_date = attrs.get(
            "return_date",
            getattr(self.instance, "return_date", None),
        )
        if borrow_date and return_date and return_date < borrow_date:
            raise serializers.ValidationError({
                "return_date": "Return date must be on or after the borrow date."
            })
        return attrs


class EquipmentBorrowRequestReviewSerializer(EquipmentBorrowRequestSerializer):
    class Meta(EquipmentBorrowRequestSerializer.Meta):
        read_only_fields = [
            "id",
            "resident",
            "resident_name",
            "item_type",
            "quantity",
            "borrow_date",
            "return_date",
            "time_slot",
            "purpose",
            "reviewed_by",
            "reviewed_by_name",
            "reviewed_at",
            "returned_at",
            "created_at",
            "updated_at",
        ]

    def validate_status(self, value):
        if value not in {
            EquipmentBorrowRequest.Status.APPROVED,
            EquipmentBorrowRequest.Status.DECLINED,
            EquipmentBorrowRequest.Status.RETURNED,
        }:
            raise serializers.ValidationError("Select a valid review status.")
        return value

    def validate(self, attrs):
        status_value = attrs.get(
            "status",
            getattr(self.instance, "status", None),
        )
        notes = attrs.get(
            "admin_notes",
            getattr(self.instance, "admin_notes", ""),
        )
        if (
            status_value == EquipmentBorrowRequest.Status.DECLINED
            and not (notes or "").strip()
        ):
            raise serializers.ValidationError({
                "admin_notes": (
                    "A reason is required when declining an equipment borrowing request."
                )
            })
        return attrs
