import re
from collections.abc import Mapping
from rest_framework import serializers
from gridy_auth.models import User


class StaffUserListSerializer(serializers.ModelSerializer):
    """
    Represents an authorized peer administrator or Field Official in the administrator's Barangay.
    """
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "role",
            "is_active",
            "date_joined",
            "last_login",
        ]
        read_only_fields = fields

    def get_full_name(self, obj) -> str:
        name = f"{obj.first_name} {obj.last_name}".strip()
        return name or obj.username


class StaffUserCreateSerializer(serializers.Serializer):
    """
    Validates payload for onboarding a new Field Official.
    Enforces strict field boundaries and case-insensitive uniqueness. New
    field officials set their own password through the private setup flow.
    """
    username = serializers.CharField(
        min_length=3,
        max_length=150,
        trim_whitespace=True,
    )
    email = serializers.EmailField(
        max_length=254,
    )
    first_name = serializers.CharField(
        min_length=1,
        max_length=150,
        trim_whitespace=True,
    )
    last_name = serializers.CharField(
        min_length=1,
        max_length=150,
        trim_whitespace=True,
    )

    def validate(self, attrs):
        # Strict rejection of disallowed extra fields (e.g. role, barangay, is_staff, is_superuser)
        if isinstance(self.initial_data, Mapping):
            allowed_fields = {"username", "email", "first_name", "last_name"}
            disallowed = set(self.initial_data.keys()) - allowed_fields
            if disallowed:
                raise serializers.ValidationError(
                    f"Disallowed fields in request payload: {', '.join(sorted(disallowed))}."
                )

        username = attrs.get("username", "").strip()
        if not re.match(r"^[\w.@+-]+$", username):
            raise serializers.ValidationError(
                {"username": "Enter a valid username containing letters, numbers, and @/./+/-/_ characters."}
            )

        if User.objects.filter(username__iexact=username).exists():
            raise serializers.ValidationError(
                {"username": "A user with that username already exists."}
            )

        email = attrs.get("email", "").strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError(
                {"email": "A user with that email address already exists."}
            )

        return attrs


class BarangayAdminCreateSerializer(StaffUserCreateSerializer):
    """Validate the identity fields for a peer Barangay Admin invitation."""


class StaffUserUpdateSerializer(serializers.Serializer):
    """Validate the small set of profile fields a Barangay Admin may edit."""

    def __init__(self, *args, **kwargs):
        partial = kwargs.get("partial", False)
        super().__init__(*args, **kwargs)
        if not partial:
            for field_name in ("first_name", "last_name", "email"):
                self.fields[field_name].required = True

    first_name = serializers.CharField(
        required=False,
        min_length=1,
        max_length=150,
        trim_whitespace=True,
    )
    last_name = serializers.CharField(
        required=False,
        min_length=1,
        max_length=150,
        trim_whitespace=True,
    )
    email = serializers.EmailField(required=False, max_length=254)

    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save(update_fields=list(validated_data.keys()))
        return instance

    def validate(self, attrs):
        if isinstance(self.initial_data, Mapping):
            allowed_fields = {"first_name", "last_name", "email"}
            disallowed = set(self.initial_data.keys()) - allowed_fields
            if disallowed:
                raise serializers.ValidationError(
                    f"Disallowed fields in request payload: {', '.join(sorted(disallowed))}."
                )

        if not attrs:
            raise serializers.ValidationError(
                {"detail": "Provide at least one profile field to update."}
            )

        email = attrs.get("email")
        if email is not None:
            email = email.strip().lower()
            if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
                raise serializers.ValidationError(
                    {"email": "A user with that email address already exists."}
                )
            attrs["email"] = email

        return attrs
