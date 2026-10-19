import uuid
from collections.abc import Mapping
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from gridy_auth.models import Barangay, BarangayApplication, User


class PublicBarangaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Barangay
        fields = ["id", "name", "municipality", "province", "primary_color"]
        read_only_fields = fields


class BarangayApplicationCreateSerializer(serializers.Serializer):
    """Create an inactive applicant account and a pending onboarding request."""

    name = serializers.CharField(min_length=2, max_length=255, trim_whitespace=True)
    municipality = serializers.CharField(min_length=2, max_length=120, trim_whitespace=True)
    province = serializers.CharField(min_length=2, max_length=120, trim_whitespace=True)
    applicant_name = serializers.CharField(min_length=2, max_length=255, trim_whitespace=True)
    applicant_position = serializers.CharField(min_length=2, max_length=120, trim_whitespace=True)
    applicant_email = serializers.EmailField(max_length=254)
    applicant_phone = serializers.CharField(min_length=7, max_length=30, trim_whitespace=True)
    proof_of_authority = serializers.FileField(write_only=True, allow_empty_file=False)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)
    applicant_authorized = serializers.BooleanField(write_only=True)
    contact_consent = serializers.BooleanField(write_only=True)

    def validate(self, attrs):
        if isinstance(self.initial_data, Mapping):
            allowed_fields = {
                "name", "municipality", "province", "applicant_name",
                "applicant_position", "applicant_email", "applicant_phone",
                "proof_of_authority", "password", "password_confirm",
                "applicant_authorized", "contact_consent",
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

        attrs["applicant_email"] = attrs["applicant_email"].strip().lower()

        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})

        password_user = User(
            email=attrs["applicant_email"],
            first_name=attrs["applicant_name"],
        )
        try:
            validate_password(attrs["password"], user=password_user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)}) from exc

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

        if User.objects.filter(
            Q(email__iexact=attrs["applicant_email"])
            | Q(username__iexact=attrs["applicant_email"])
        ).exists():
            raise serializers.ValidationError({
                "applicant_email": "That email is already associated with an account. Contact support if you need help."
            })

        if BarangayApplication.objects.filter(
            status=BarangayApplication.Status.PENDING,
            applicant_email__iexact=attrs["applicant_email"],
        ).exists():
            raise serializers.ValidationError({
                "applicant_email": "That email address is already proposed in another pending application."
            })

        return attrs

    def validate_proof_of_authority(self, uploaded_file):
        maximum_size = 5 * 1024 * 1024
        if uploaded_file.size > maximum_size:
            raise serializers.ValidationError("The authority document must be 5 MiB or smaller.")

        try:
            uploaded_file.seek(0)
            signature = uploaded_file.read(8)
            uploaded_file.seek(0)
        except (AttributeError, OSError) as exc:
            raise serializers.ValidationError("The authority document could not be read.") from exc

        if signature.startswith(b"%PDF-"):
            extension = "pdf"
        elif signature.startswith(b"\xff\xd8\xff"):
            extension = "jpg"
        elif signature.startswith(b"\x89PNG\r\n\x1a\n"):
            extension = "png"
        else:
            raise serializers.ValidationError(
                "Upload a PDF, JPEG, or PNG document with a valid file signature."
            )

        # Do not preserve applicant-supplied filenames in private storage paths.
        uploaded_file.name = f"authority-proof.{extension}"
        return uploaded_file

    def create(self, validated_data):
        password = validated_data.pop("password")
        validated_data.pop("password_confirm")
        applicant = User.objects.create_user(
            username=f"pending-admin-{uuid.uuid4().hex}",
            email=validated_data["applicant_email"],
            first_name=validated_data["applicant_name"],
            password=password,
            role=User.Role.ADMIN,
            barangay=None,
            is_active=False,
            is_staff=False,
            is_superuser=False,
        )
        validated_data["admin_username"] = ""
        validated_data["applicant_user"] = applicant
        validated_data["email_verification_sent_at"] = timezone.now()
        return BarangayApplication.objects.create(**validated_data)


class BarangayApplicationReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = BarangayApplication
        fields = ["id", "status", "created_at"]
        read_only_fields = fields


class BarangayApplicationOperatorSerializer(serializers.ModelSerializer):
    reviewed_by_username = serializers.CharField(source="reviewed_by.username", read_only=True, allow_null=True)
    created_admin_username = serializers.SerializerMethodField()
    created_admin_email = serializers.EmailField(source="created_admin.email", read_only=True, allow_null=True)
    has_applicant_account = serializers.SerializerMethodField()
    admin_can_sign_in = serializers.SerializerMethodField()
    created_barangay_id = serializers.IntegerField(read_only=True, allow_null=True)
    has_proof_of_authority = serializers.SerializerMethodField()

    class Meta:
        model = BarangayApplication
        fields = [
            "id", "name", "municipality", "province", "applicant_name",
            "applicant_position", "applicant_email", "applicant_phone",
            "admin_username", "applicant_authorized", "contact_consent",
            "email_verified_at", "has_proof_of_authority",
            "status", "review_note", "review_verified", "reviewed_by_username",
            "proof_reviewed",
            "reviewed_at", "created_barangay_id", "created_admin_username",
            "created_admin_email", "has_applicant_account", "admin_can_sign_in",
            "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_created_admin_username(self, obj):
        # Do not expose the generated internal username for new email-only accounts.
        if not obj.admin_username or obj.created_admin is None:
            return None
        return obj.created_admin.username

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_has_applicant_account(self, obj):
        return obj.applicant_user_id is not None

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_admin_can_sign_in(self, obj):
        admin = obj.created_admin or obj.applicant_user
        return bool(admin and admin.is_active and admin.has_usable_password())

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_has_proof_of_authority(self, obj):
        return bool(obj.proof_of_authority and obj.proof_of_authority.name)


class BarangayApplicationEmailVerificationSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=128, trim_whitespace=True)


class BarangayApplicationVerificationResendSerializer(serializers.Serializer):
    application_id = serializers.IntegerField(min_value=1)
    applicant_email = serializers.EmailField(max_length=254)

    def validate(self, attrs):
        if isinstance(self.initial_data, Mapping):
            unexpected = set(self.initial_data) - {"application_id", "applicant_email"}
            if unexpected:
                raise serializers.ValidationError({
                    "detail": f"Unexpected fields: {', '.join(sorted(unexpected))}."
                })
        attrs["applicant_email"] = attrs["applicant_email"].strip().lower()
        return attrs


class BarangayApplicationApproveSerializer(serializers.Serializer):
    contact_verified = serializers.BooleanField()
    proof_reviewed = serializers.BooleanField(required=False, default=False)
    review_note = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")

    def validate(self, attrs):
        if isinstance(self.initial_data, Mapping):
            unexpected = set(self.initial_data) - {"contact_verified", "proof_reviewed", "review_note"}
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
