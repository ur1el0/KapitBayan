import re
from collections.abc import Mapping

from rest_framework import serializers

from gridy_auth.models import Barangay, BarangayApplication


class PublicBarangaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Barangay
        fields = ["id", "name", "municipality", "province", "primary_color"]
        read_only_fields = fields


class BarangayApplicationCreateSerializer(serializers.Serializer):
    """Collect an onboarding request without creating a tenant or user."""

    name = serializers.CharField(min_length=2, max_length=255, trim_whitespace=True)
    municipality = serializers.CharField(min_length=2, max_length=120, trim_whitespace=True)
    province = serializers.CharField(min_length=2, max_length=120, trim_whitespace=True)
    applicant_name = serializers.CharField(min_length=2, max_length=255, trim_whitespace=True)
    applicant_position = serializers.CharField(min_length=2, max_length=120, trim_whitespace=True)
    applicant_email = serializers.EmailField(max_length=254)
    applicant_phone = serializers.CharField(min_length=7, max_length=30, trim_whitespace=True)
    admin_username = serializers.CharField(min_length=3, max_length=150, trim_whitespace=True)
    applicant_authorized = serializers.BooleanField(write_only=True)
    contact_consent = serializers.BooleanField(write_only=True)

    def validate(self, attrs):
        if isinstance(self.initial_data, Mapping):
            allowed_fields = {
                "name", "municipality", "province", "applicant_name",
                "applicant_position", "applicant_email", "applicant_phone",
                "admin_username", "applicant_authorized", "contact_consent",
            }
            unexpected = set(self.initial_data) - allowed_fields
            if unexpected:
                raise serializers.ValidationError(
                    {"detail": f"Unexpected fields: {', '.join(sorted(unexpected))}."}
                )

        if attrs.get("applicant_authorized") is not True:
            raise serializers.ValidationError({
                "applicant_authorized": "Confirm that you are authorized to submit this request on behalf of the Barangay."
            })
        if attrs.get("contact_consent") is not True:
            raise serializers.ValidationError({
                "contact_consent": "Consent is required to use the applicant contact details to review this request."
            })

        username = attrs["admin_username"].strip()
        if not re.fullmatch(r"[\w.@+-]{3,150}", username):
            raise serializers.ValidationError({
                "admin_username": "Use 3–150 letters, numbers, or @/./+/-/_ characters."
            })
        attrs["admin_username"] = username
        attrs["applicant_email"] = attrs["applicant_email"].strip().lower()

        duplicate_application = BarangayApplication.objects.filter(
            status=BarangayApplication.Status.PENDING,
            name__iexact=attrs["name"],
            municipality__iexact=attrs["municipality"],
            province__iexact=attrs["province"],
        ).exists()
        if duplicate_application:
            raise serializers.ValidationError({
                "detail": "A pending application already exists for this Barangay and locality."
            })

        if BarangayApplication.objects.filter(
            status=BarangayApplication.Status.PENDING,
            admin_username__iexact=username,
        ).exclude(admin_username="").exists():
            raise serializers.ValidationError({
                "admin_username": "That username is already proposed in another pending application."
            })
        if BarangayApplication.objects.filter(
            status=BarangayApplication.Status.PENDING,
            applicant_email__iexact=attrs["applicant_email"],
        ).exclude(admin_username="").exists():
            raise serializers.ValidationError({
                "applicant_email": "That email address is already proposed in another pending application."
            })

        return attrs

    def create(self, validated_data):
        return BarangayApplication.objects.create(**validated_data)


class BarangayApplicationReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = BarangayApplication
        fields = ["id", "status", "created_at"]
        read_only_fields = fields


class BarangayApplicationOperatorSerializer(serializers.ModelSerializer):
    reviewed_by_username = serializers.CharField(source="reviewed_by.username", read_only=True, allow_null=True)
    created_admin_username = serializers.CharField(source="created_admin.username", read_only=True, allow_null=True)
    created_barangay_id = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = BarangayApplication
        fields = [
            "id", "name", "municipality", "province", "applicant_name",
            "applicant_position", "applicant_email", "applicant_phone",
            "admin_username", "applicant_authorized", "contact_consent",
            "status", "review_note", "review_verified", "reviewed_by_username",
            "reviewed_at", "created_barangay_id", "created_admin_username",
            "created_at", "updated_at",
        ]
        read_only_fields = fields


class BarangayApplicationApproveSerializer(serializers.Serializer):
    contact_verified = serializers.BooleanField()
    review_note = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")

    def validate(self, attrs):
        if isinstance(self.initial_data, Mapping):
            unexpected = set(self.initial_data) - {"contact_verified", "review_note"}
            if unexpected:
                raise serializers.ValidationError({
                    "detail": f"Unexpected fields: {', '.join(sorted(unexpected))}."
                })
        return attrs

    def validate_contact_verified(self, value):
        if value is not True:
            raise serializers.ValidationError(
                "Confirm that the applicant and Barangay were verified through an official channel."
            )
        return value


class BarangayApplicationRejectSerializer(serializers.Serializer):
    reason = serializers.CharField(min_length=5, max_length=1000, trim_whitespace=True)

    def validate(self, attrs):
        if isinstance(self.initial_data, Mapping):
            unexpected = set(self.initial_data) - {"reason"}
            if unexpected:
                raise serializers.ValidationError({
                    "detail": f"Unexpected fields: {', '.join(sorted(unexpected))}."
                })
        return attrs
