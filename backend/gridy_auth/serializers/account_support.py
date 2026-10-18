from collections.abc import Mapping

from rest_framework import serializers

from gridy_auth.models import Resident, User


ACCOUNT_SUPPORT_ROLES = (
    User.Role.RESIDENT,
    User.Role.FIELD_OFFICIAL,
    User.Role.ADMIN,
)

ACCOUNT_SUPPORT_REASON_CHOICES = (
    ("INCORRECT_CONTACT", "Incorrect contact details"),
    ("LOCKED_OUT", "Account holder is locked out"),
    ("SECURITY_CONCERN", "Security concern"),
    ("STATUS_CORRECTION", "Account status correction"),
    ("OTHER_VERIFIED_SUPPORT", "Other verified support issue"),
)


class StrictSerializer(serializers.Serializer):
    """Reject unsupported fields instead of silently ignoring privileged input."""

    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            unexpected = set(data.keys()) - set(self.fields.keys())
            if unexpected:
                raise serializers.ValidationError({
                    "detail": "Unsupported fields were supplied.",
                    "fields": sorted(str(field) for field in unexpected),
                })
        return super().to_internal_value(data)


class DILGAccountDirectoryQuerySerializer(serializers.Serializer):
    search = serializers.CharField(required=False, allow_blank=True, max_length=120, trim_whitespace=True)
    role = serializers.ChoiceField(required=False, choices=ACCOUNT_SUPPORT_ROLES)
    active = serializers.BooleanField(required=False)

    def validate_search(self, value):
        if value and len(value) < 2:
            raise serializers.ValidationError("Enter at least two characters to search.")
        return value


class DILGAccountSummarySerializer(serializers.ModelSerializer):
    barangay_id = serializers.IntegerField(read_only=True, allow_null=True)
    full_name = serializers.SerializerMethodField()
    barangay_name = serializers.CharField(source="barangay.name", read_only=True, allow_null=True)
    barangay_municipality = serializers.CharField(source="barangay.municipality", read_only=True, allow_null=True)
    barangay_province = serializers.CharField(source="barangay.province", read_only=True, allow_null=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "role",
            "is_active",
            "barangay_id",
            "barangay_name",
            "barangay_municipality",
            "barangay_province",
        )
        read_only_fields = fields

    def get_full_name(self, obj) -> str:
        try:
            profile_name = obj.profile.full_name
        except Resident.DoesNotExist:
            profile_name = ""
        return profile_name or f"{obj.first_name} {obj.last_name}".strip() or obj.username


class DILGAccountEmailCorrectionSerializer(StrictSerializer):
    email = serializers.EmailField(max_length=254)
    contact_verified = serializers.BooleanField()
    reason = serializers.ChoiceField(choices=ACCOUNT_SUPPORT_REASON_CHOICES)

    def validate_email(self, value):
        normalized = value.strip().lower()
        user = self.context["target"]
        if User.objects.filter(email__iexact=normalized).exclude(pk=user.pk).exists():
            raise serializers.ValidationError("This email is already associated with another account.")
        return normalized

    def validate(self, attrs):
        if not attrs["contact_verified"]:
            raise serializers.ValidationError({
                "contact_verified": "Verify the account holder's contact through an official channel first."
            })
        if attrs["email"].casefold() == self.context["target"].email.casefold():
            raise serializers.ValidationError({
                "email": "Enter a different email address. Use the resend action for the current address."
            })
        return attrs


class DILGAccountRecoveryLinkSerializer(StrictSerializer):
    contact_verified = serializers.BooleanField()
    reason = serializers.ChoiceField(choices=ACCOUNT_SUPPORT_REASON_CHOICES)

    def validate(self, attrs):
        if not attrs["contact_verified"]:
            raise serializers.ValidationError({
                "contact_verified": "Verify the account holder's contact through an official channel first."
            })
        return attrs


class DILGAccountActiveStateSerializer(StrictSerializer):
    is_active = serializers.BooleanField()
    reason = serializers.ChoiceField(choices=ACCOUNT_SUPPORT_REASON_CHOICES)
