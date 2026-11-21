from rest_framework import serializers
from django.db import transaction
from django.db.models import Q
from django.urls import reverse
from gridy_auth.models import User, Resident, Barangay, RefreshSession
from gridy_auth.guardianship import guardian_account_is_eligible
from gridy_auth.lifecycle import (
    RESIDENT_PRIVATE_MEDIA_FIELDS,
    attempt_private_media_cleanup_safely,
    queue_private_media_cleanup,
)


MAX_IMAGE_UPLOAD_SIZE_BYTES = 5 * 1024 * 1024
MAX_RESIDENT_EVIDENCE_IMAGE_SIZE_BYTES = MAX_IMAGE_UPLOAD_SIZE_BYTES


def _validate_image_max_size(value, message):
    if value is not None and value.size > MAX_IMAGE_UPLOAD_SIZE_BYTES:
        raise serializers.ValidationError(message)
    return value


SIGN_IN_EMAIL_ROLES = (
    User.Role.ADMIN,
    User.Role.FIELD_OFFICIAL,
    User.Role.BARANGAY_OPERATOR,
)


def has_sign_in_identity_conflict(identifier, *, exclude_user_id=None):
    """Return True when identifier matches any existing username or official sign-in email."""
    conflicts = User.objects.filter(
        Q(username__iexact=identifier)
        | Q(email__iexact=identifier, role__in=SIGN_IN_EMAIL_ROLES)
    )
    if exclude_user_id is not None:
        conflicts = conflicts.exclude(pk=exclude_user_id)
    return conflicts.exists()


class ResidentEvidenceImageField(serializers.ImageField):
    """Reject oversized resident evidence before sending it to media storage."""

    def to_internal_value(self, data):
        uploaded_file = super().to_internal_value(data)
        return _validate_image_max_size(
            uploaded_file,
            "Resident ID and residency proof images must be 5 MiB or smaller.",
        )


class ResidentPrivateImageField(ResidentEvidenceImageField):
    def to_representation(self, value):
        if not value:
            return None

        resident = getattr(value, 'instance', None)
        if resident is None or resident.pk is None:
            return None

        url = reverse(
            'resident_private_media',
            kwargs={
                'resident_id': resident.pk,
                'field_name': self.field_name,
            },
        )
        return url.removeprefix('/api/v1/')


class BarangaySerializer(serializers.ModelSerializer):
    has_kiosk_staff_pin = serializers.SerializerMethodField()
    kiosk_staff_pin = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        max_length=12,
        trim_whitespace=True,
    )
    clear_kiosk_staff_pin = serializers.BooleanField(
        write_only=True,
        required=False,
        default=False,
    )

    class Meta:
        model = Barangay
        fields = [
            'id',
            'name',
            'municipality',
            'province',
            'logo',
            'city_seal', 
            'captain_name', 
            'office_contact',
            'primary_color',
            'has_kiosk_staff_pin',
            'kiosk_staff_pin',
            'clear_kiosk_staff_pin',
        ]
        read_only_fields = ['id', 'name', 'municipality', 'province', 'has_kiosk_staff_pin']

    def get_has_kiosk_staff_pin(self, obj) -> bool:
        return bool(obj.kiosk_staff_pin_hash)

    def validate_kiosk_staff_pin(self, value):
        cleaned = (value or '').strip()
        if not cleaned:
            return ''
        if len(cleaned) < 4 or len(cleaned) > 12:
            raise serializers.ValidationError(
                'Kiosk staff PIN must be between 4 and 12 characters.'
            )
        if not cleaned.isalnum():
            raise serializers.ValidationError(
                'Kiosk staff PIN must contain only letters and numbers.'
            )
        return cleaned

    def validate_logo(self, value):
        return _validate_image_max_size(value, "Barangay logo images must be 5 MiB or smaller.")

    def validate_city_seal(self, value):
        return _validate_image_max_size(value, "City seal images must be 5 MiB or smaller.")

    def update(self, instance, validated_data):
        raw_pin = validated_data.pop('kiosk_staff_pin', None)
        clear_pin = validated_data.pop('clear_kiosk_staff_pin', False)
        instance = super().update(instance, validated_data)
        if clear_pin:
            instance.set_kiosk_staff_pin('')
            instance.save(update_fields=['kiosk_staff_pin_hash'])
        elif raw_pin:
            instance.set_kiosk_staff_pin(raw_pin)
            instance.save(update_fields=['kiosk_staff_pin_hash'])
        return instance

class ResidentSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True, default='')
    email = serializers.CharField(source='user.email', read_only=True, default='')
    philsys_id_photo = ResidentPrivateImageField(required=False, allow_null=True)
    secondary_id_photo = ResidentPrivateImageField(required=False, allow_null=True)
    utility_billing_photo = ResidentPrivateImageField(required=False, allow_null=True)
    guardianship_evidence = ResidentPrivateImageField(read_only=True)
    guardian_name = serializers.CharField(source="guardian.full_name", read_only=True, allow_null=True)
    guardian_username = serializers.CharField(source="guardian.user.username", read_only=True, allow_null=True)

    remove_philsys_id_photo = serializers.BooleanField(required=False, write_only=True, default=False)
    remove_secondary_id_photo = serializers.BooleanField(required=False, write_only=True, default=False)
    remove_utility_billing_photo = serializers.BooleanField(required=False, write_only=True, default=False)

    class Meta:
        model = Resident
        fields = [
            'id', 'username', 'email', 'full_name', 'birth_date', 'voter_status', 
            'contact_number', 'purok', 'address_details', 'is_verified', 'guardian',
            'guardian_name', 'guardian_username', 'guardian_relationship', 'guardianship_evidence',
            'philsys_id_number', 'philsys_id_photo', 'remove_philsys_id_photo',
            'secondary_id_type', 'secondary_id_photo', 'remove_secondary_id_photo',
            'utility_billing_type', 'utility_billing_photo', 'remove_utility_billing_photo',
        ]
        read_only_fields = [
            'is_verified', 'guardian', 'guardian_relationship', 'guardianship_evidence',
        ]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if self.instance is not None:
            has_philsys = bool(self.instance.philsys_id_photo)
            has_secondary = bool(self.instance.secondary_id_photo)
            has_utility = bool(self.instance.utility_billing_photo)
            current_proof_count = sum([has_philsys, has_secondary, has_utility])

            # PhilSys
            if attrs.get('philsys_id_photo'):
                resulting_has_philsys = True
            elif attrs.get('remove_philsys_id_photo') or (
                'philsys_id_photo' in attrs and attrs.get('philsys_id_photo') is None
            ):
                resulting_has_philsys = False
            else:
                resulting_has_philsys = has_philsys

            # Secondary ID
            if attrs.get('secondary_id_photo'):
                resulting_has_secondary = True
            elif attrs.get('remove_secondary_id_photo') or (
                'secondary_id_photo' in attrs and attrs.get('secondary_id_photo') is None
            ):
                resulting_has_secondary = False
            else:
                resulting_has_secondary = has_secondary

            # Utility Billing
            if attrs.get('utility_billing_photo'):
                resulting_has_utility = True
            elif attrs.get('remove_utility_billing_photo') or (
                'utility_billing_photo' in attrs and attrs.get('utility_billing_photo') is None
            ):
                resulting_has_utility = False
            else:
                resulting_has_utility = has_utility

            resulting_proof_count = sum([
                resulting_has_philsys,
                resulting_has_secondary,
                resulting_has_utility,
            ])

            if current_proof_count > 0 and resulting_proof_count == 0:
                raise serializers.ValidationError({
                    'verification_documents': (
                        "Cannot remove the only proof document on file. Residents must "
                        "maintain at least one valid identity or residency proof document."
                    )
                })

        return attrs

    def update(self, instance, validated_data):
        # Never permit updating is_verified through resident profile updates
        validated_data.pop('is_verified', None)
        previous_private_files = {
            field_name: getattr(instance, field_name).name
            for field_name in RESIDENT_PRIVATE_MEDIA_FIELDS
            if getattr(instance, field_name, None) and getattr(instance, field_name).name
        }

        remove_philsys = validated_data.pop('remove_philsys_id_photo', False)
        remove_secondary = validated_data.pop('remove_secondary_id_photo', False)
        remove_utility = validated_data.pop('remove_utility_billing_photo', False)

        # 1. PhilSys ID
        if 'philsys_id_photo' in validated_data and validated_data['philsys_id_photo'] is not None:
            instance.philsys_id_photo = validated_data.pop('philsys_id_photo')
            if 'philsys_id_number' in validated_data:
                instance.philsys_id_number = validated_data.pop('philsys_id_number')
        elif remove_philsys or ('philsys_id_photo' in validated_data and validated_data['philsys_id_photo'] is None):
            instance.philsys_id_photo = None
            instance.philsys_id_number = None
            validated_data.pop('philsys_id_photo', None)
            validated_data.pop('philsys_id_number', None)

        # 2. Secondary ID
        if 'secondary_id_photo' in validated_data and validated_data['secondary_id_photo'] is not None:
            instance.secondary_id_photo = validated_data.pop('secondary_id_photo')
            if 'secondary_id_type' in validated_data:
                instance.secondary_id_type = validated_data.pop('secondary_id_type')
        elif remove_secondary or ('secondary_id_photo' in validated_data and validated_data['secondary_id_photo'] is None):
            instance.secondary_id_photo = None
            instance.secondary_id_type = None
            validated_data.pop('secondary_id_photo', None)
            validated_data.pop('secondary_id_type', None)

        # 3. Utility Billing
        if 'utility_billing_photo' in validated_data and validated_data['utility_billing_photo'] is not None:
            instance.utility_billing_photo = validated_data.pop('utility_billing_photo')
            if 'utility_billing_type' in validated_data:
                instance.utility_billing_type = validated_data.pop('utility_billing_type')
        elif remove_utility or ('utility_billing_photo' in validated_data and validated_data['utility_billing_photo'] is None):
            instance.utility_billing_photo = None
            instance.utility_billing_type = None
            validated_data.pop('utility_billing_photo', None)
            validated_data.pop('utility_billing_type', None)

        # Remaining fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        with transaction.atomic():
            instance.save()
            for field_name, old_file_name in previous_private_files.items():
                current_field = getattr(instance, field_name, None)
                new_file_name = current_field.name if current_field else None
                if old_file_name and old_file_name != new_file_name:
                    cleanup = queue_private_media_cleanup(
                        "gridy_auth.Resident",
                        field_name,
                        old_file_name,
                    )
                    transaction.on_commit(
                        lambda cleanup_id=cleanup.pk: attempt_private_media_cleanup_safely(
                            cleanup_id
                        )
                    )
        return instance

class ResidentAdminUpdateSerializer(ResidentSerializer):
    email = serializers.EmailField(
        source='user.email',
        required=False,
        allow_blank=False,
    )

    def validate_email(self, value):
        normalized_email = value.strip().lower()
        existing_users = User.objects.filter(
            Q(email__iexact=normalized_email) | Q(username__iexact=normalized_email)
        )

        if self.instance is not None:
            existing_users = existing_users.exclude(
                pk=self.instance.user_id,
            )

        if existing_users.exists():
            raise serializers.ValidationError(
                "An account with this email already exists."
            )

        return normalized_email

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        email = user_data.get('email')

        if email is not None:
            instance.user.email = email
            instance.user.save(update_fields=['email'])

        return super().update(instance, validated_data)


class ResidentAdminReviewSerializer(ResidentSerializer):
    guardian_account_eligible = serializers.SerializerMethodField()

    class Meta(ResidentSerializer.Meta):
        fields = ResidentSerializer.Meta.fields + ['guardian_account_eligible']

    def get_guardian_account_eligible(self, obj):
        return guardian_account_is_eligible(
            obj.guardian,
            barangay_id=obj.user.barangay_id,
        )


class UserSerializer(serializers.ModelSerializer):
    profile = ResidentSerializer(required=False)
    barangay = BarangaySerializer(read_only=True)
    full_name = serializers.SerializerMethodField()
    is_superuser = serializers.BooleanField(read_only=True)
    profile_picture = serializers.ImageField(required=False, allow_null=True)
    remove_profile_picture = serializers.BooleanField(required=False, write_only=True, default=False)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'role', 'barangay', 'profile', 'full_name', 'is_superuser',
            'email_alerts', 'push_alerts', 'profile_picture', 'remove_profile_picture',
        ]
        read_only_fields = ['role', 'barangay', 'full_name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if isinstance(instance, User) and instance.role in SIGN_IN_EMAIL_ROLES:
            self.fields['username'].read_only = True
        if isinstance(instance, User) and hasattr(instance, 'profile'):
            self.fields['profile'].instance = getattr(instance, 'profile', None)

    def get_full_name(self, obj):
        full_name = getattr(obj.profile, 'full_name', None) if hasattr(obj, 'profile') else None
        if not full_name:
            identity = obj.email if obj.role in SIGN_IN_EMAIL_ROLES else obj.username
            full_name = f"{obj.first_name} {obj.last_name}".strip() or identity
        return full_name

    def validate_username(self, value):
        username = value.strip().lower()
        if not username:
            raise serializers.ValidationError("Username cannot be blank.")
        exclude_id = self.instance.pk if isinstance(self.instance, User) else None
        if has_sign_in_identity_conflict(username, exclude_user_id=exclude_id):
            raise serializers.ValidationError(
                "This username conflicts with an existing account sign-in identity."
            )
        return username

    def validate_email(self, value):
        normalized_email = value.strip().lower()
        exclude_id = self.instance.pk if isinstance(self.instance, User) else None
        is_official = (
            isinstance(self.instance, User)
            and self.instance.role in SIGN_IN_EMAIL_ROLES
        )
        if is_official:
            if not normalized_email:
                raise serializers.ValidationError(
                    "Official accounts must have an email sign-in identity."
                )
            conflicting_accounts = User.objects.filter(
                Q(email__iexact=normalized_email) | Q(username__iexact=normalized_email)
            ).exclude(pk=exclude_id)
            if conflicting_accounts.exists():
                raise serializers.ValidationError(
                    "This email must be unique across accounts because it is the official sign-in identity."
                )
            return normalized_email

        if not normalized_email:
            return normalized_email

        if has_sign_in_identity_conflict(normalized_email, exclude_user_id=exclude_id):
            raise serializers.ValidationError(
                "This email conflicts with an existing account sign-in identity."
            )

        current_email = (
            (self.instance.email or "").strip().lower()
            if isinstance(self.instance, User)
            else ""
        )
        if normalized_email != current_email:
            conflicting_email = User.objects.filter(email__iexact=normalized_email)
            if exclude_id is not None:
                conflicting_email = conflicting_email.exclude(pk=exclude_id)
            if conflicting_email.exists():
                raise serializers.ValidationError(
                    "An account with this email already exists."
                )
        return normalized_email

    def validate_profile_picture(self, value):
        return _validate_image_max_size(value, "Profile pictures must be 5 MB or smaller.")

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.role in {User.Role.ADMIN, User.Role.FIELD_OFFICIAL, User.Role.BARANGAY_OPERATOR}:
            # The model needs an internal unique username, but officials sign in by email.
            representation['username'] = instance.email
        return representation

    def update(self, instance, validated_data):
        # Extract the profile dictionary from the request
        profile_data = validated_data.pop('profile', None)
        remove_profile_picture = validated_data.pop('remove_profile_picture', False)
        old_profile_picture_name = instance.profile_picture.name if instance.profile_picture else None
        if remove_profile_picture:
            validated_data['profile_picture'] = None
        email_changed = (
            'email' in validated_data
            and validated_data['email'].strip().casefold() != instance.email.strip().casefold()
        )

        # Update standard User fields (username, email)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        new_profile_picture_name = instance.profile_picture.name if instance.profile_picture else None
        if old_profile_picture_name and old_profile_picture_name != new_profile_picture_name:
            instance.profile_picture.storage.delete(old_profile_picture_name)
        if email_changed:
            RefreshSession.objects.filter(user=instance, is_revoked=False).update(is_revoked=True)

        # Update nested Resident profile fields via ResidentSerializer
        if profile_data is not None and hasattr(instance, 'profile'):
            self.fields['profile'].update(instance.profile, profile_data)

        return instance
