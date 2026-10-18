from rest_framework import serializers
from django.urls import reverse
from gridy_auth.models import User, Resident, Barangay


class ResidentPrivateImageField(serializers.ImageField):
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
        ]
        read_only_fields = ['id', 'name', 'municipality', 'province']

class ResidentSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True, default='')
    email = serializers.CharField(source='user.email', read_only=True, default='')
    philsys_id_photo = ResidentPrivateImageField(required=False, allow_null=True)
    secondary_id_photo = ResidentPrivateImageField(required=False, allow_null=True)
    utility_billing_photo = ResidentPrivateImageField(required=False, allow_null=True)

    remove_philsys_id_photo = serializers.BooleanField(required=False, write_only=True, default=False)
    remove_secondary_id_photo = serializers.BooleanField(required=False, write_only=True, default=False)
    remove_utility_billing_photo = serializers.BooleanField(required=False, write_only=True, default=False)

    class Meta:
        model = Resident
        fields = [
            'id', 'username', 'email', 'full_name', 'birth_date', 'voter_status', 
            'contact_number', 'purok', 'is_verified', 'guardian', 
            'philsys_id_number', 'philsys_id_photo', 'remove_philsys_id_photo',
            'secondary_id_type', 'secondary_id_photo', 'remove_secondary_id_photo',
            'utility_billing_type', 'utility_billing_photo', 'remove_utility_billing_photo',
        ]
        read_only_fields = ['is_verified']

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

        instance.save()
        return instance

class ResidentAdminUpdateSerializer(ResidentSerializer):
    email = serializers.EmailField(
        source='user.email',
        required=False,
        allow_blank=False,
    )

    def validate_email(self, value):
        normalized_email = value.strip().lower()
        existing_users = User.objects.filter(email__iexact=normalized_email)

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

class UserSerializer(serializers.ModelSerializer):
    profile = ResidentSerializer(required=False)
    barangay = BarangaySerializer(read_only=True)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'role', 'barangay', 'profile', 'full_name',
            'email_alerts', 'push_alerts',
        ]
        read_only_fields = ['role', 'barangay', 'full_name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if isinstance(instance, User) and hasattr(instance, 'profile'):
            self.fields['profile'].instance = getattr(instance, 'profile', None)

    def get_full_name(self, obj):
        full_name = getattr(obj.profile, 'full_name', None) if hasattr(obj, 'profile') else None
        if not full_name:
            full_name = f"{obj.first_name} {obj.last_name}".strip() or obj.username
        return full_name

    def update(self, instance, validated_data):
        # Extract the profile dictionary from the request
        profile_data = validated_data.pop('profile', None)

        # Update standard User fields (username, email)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update nested Resident profile fields via ResidentSerializer
        if profile_data is not None and hasattr(instance, 'profile'):
            self.fields['profile'].update(instance.profile, profile_data)

        return instance
