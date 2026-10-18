from django.db.models import Q
from rest_framework import serializers

from gridy_auth.models import Barangay, BarangayApplication, User


class PublicBarangaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Barangay
        fields = ["id", "name", "municipality", "province", "primary_color"]
        read_only_fields = fields


class BarangayApplicationCreateSerializer(serializers.ModelSerializer):
    barangay_id = serializers.PrimaryKeyRelatedField(
        source="existing_barangay",
        queryset=Barangay.objects.all(),
        required=True,
        write_only=True,
    )

    class Meta:
        model = BarangayApplication
        fields = [
            "id",
            "application_type",
            "barangay_id",
            "name",
            "municipality",
            "province",
            "applicant_name",
            "applicant_position",
            "applicant_email",
            "applicant_phone",
        ]
        read_only_fields = ["id", "name", "municipality", "province"]

    def validate(self, attrs):
        application_type = attrs.get("application_type", BarangayApplication.ApplicationType.OFFICIAL)
        if application_type != BarangayApplication.ApplicationType.OFFICIAL:
            raise serializers.ValidationError({
                "application_type": "Barangay onboarding applications are no longer accepted. Only official account requests for existing barangays can be submitted."
            })
        attrs["application_type"] = application_type

        barangay = attrs.get("existing_barangay")
        if not barangay:
            raise serializers.ValidationError({"barangay_id": "Select an approved barangay."})
        attrs["name"] = barangay.name
        attrs["municipality"] = barangay.municipality
        attrs["province"] = barangay.province

        for field in ("applicant_name", "applicant_position"):
            attrs[field] = attrs[field].strip()
        attrs["applicant_email"] = attrs["applicant_email"].strip().lower()
        attrs["applicant_phone"] = attrs["applicant_phone"].strip()

        if User.objects.filter(email__iexact=attrs["applicant_email"]).exists():
            raise serializers.ValidationError({"applicant_email": "This email already belongs to an account."})

        return attrs


class BarangayApplicationReviewSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=(BarangayApplication.Status.APPROVED, BarangayApplication.Status.REJECTED)
    )
    review_note = serializers.CharField(
        max_length=1000,
        required=False,
        allow_blank=True,
        trim_whitespace=True,
    )

    def validate(self, attrs):
        if attrs["status"] == BarangayApplication.Status.REJECTED and not attrs.get("review_note"):
            raise serializers.ValidationError({
                "review_note": "A reason is required when rejecting an application."
            })
        return attrs


class BarangayApplicationReadSerializer(serializers.ModelSerializer):
    reviewed_by_name = serializers.CharField(
        source="reviewed_by.username",
        read_only=True,
        allow_null=True,
    )
    barangay_name = serializers.SerializerMethodField()

    def get_barangay_name(self, obj):
        if obj.created_barangay:
            return obj.created_barangay.name
        if obj.existing_barangay:
            return obj.existing_barangay.name
        return obj.name or None

    class Meta:
        model = BarangayApplication
        fields = [
            "id",
            "application_type",
            "name",
            "municipality",
            "province",
            "applicant_name",
            "applicant_position",
            "applicant_email",
            "applicant_phone",
            "status",
            "review_note",
            "reviewed_by_name",
            "reviewed_at",
            "barangay_name",
            "created_at",
        ]
        read_only_fields = fields
