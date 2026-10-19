from rest_framework import serializers
from django.db import transaction
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from gridy_auth.models import User, Resident, Barangay
from datetime import date
from django.conf import settings
from django.utils import timezone
from django.db.models import Q

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    full_name = serializers.CharField(write_only=True)
    birth_date = serializers.DateField(write_only=True)
    voter_status = serializers.BooleanField(write_only=True, default=False)
    privacy_consent = serializers.BooleanField(
        write_only=True,
        required=True,
    )
    privacy_consent_version = serializers.CharField(
        max_length=64,
        write_only=True,
        required=True,
    )
    contact_number = serializers.CharField(write_only=True, required=False, allow_blank=True)
    barangay_id = serializers.IntegerField(
        write_only=True,
        required=True,
        min_value=1,
    )
    guardian_id = serializers.CharField(write_only=True, required=False, allow_blank=True)
    philsys_id_number = serializers.CharField(write_only=True, required=False, allow_blank=True)
    philsys_id_photo = serializers.ImageField(write_only=True, required=False, allow_null=True)
    secondary_id_type = serializers.CharField(write_only=True, required=False, allow_blank=True)
    secondary_id_photo = serializers.ImageField(write_only=True, required=False, allow_null=True)
    utility_billing_type = serializers.CharField(write_only=True, required=False, allow_blank=True)
    utility_billing_photo = serializers.ImageField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'full_name', 'birth_date', 'voter_status', 
            'contact_number', 'barangay_id', 'guardian_id',
            'philsys_id_number', 'philsys_id_photo', 'secondary_id_type', 
            'secondary_id_photo', 'utility_billing_type', 'utility_billing_photo',
            'privacy_consent', 'privacy_consent_version',
        ]

    # 1. This validates JUST the password
    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    def validate_email(self, value):
        normalized_email = value.strip().lower()
        if not normalized_email:
            return normalized_email

        official_roles = (
            User.Role.ADMIN,
            User.Role.FIELD_OFFICIAL,
            User.Role.BARANGAY_OPERATOR,
        )
        conflicts_with_staff_identity = User.objects.filter(
            Q(username__iexact=normalized_email)
            | Q(email__iexact=normalized_email, role__in=official_roles)
        ).exists()
        if conflicts_with_staff_identity:
            raise serializers.ValidationError(
                "This email conflicts with an existing account sign-in identity."
            )
        return normalized_email

    # 2. This validates the ENTIRE payload (attrs)
    def validate(self, attrs):
        if attrs.get('privacy_consent') is not True:
            raise serializers.ValidationError({
                'privacy_consent': 'Consent is required to register a resident account.'
            })

        if attrs.get('privacy_consent_version') != settings.PRIVACY_CONSENT_VERSION:
            raise serializers.ValidationError({
                'privacy_consent_version': (
                    'The privacy notice changed. Review the current notice and submit again.'
                )
            })

        verification_image_fields = (
            'philsys_id_photo',
            'secondary_id_photo',
            'utility_billing_photo',
        )
        if not any(attrs.get(field) for field in verification_image_fields):
            raise serializers.ValidationError({
                'verification_documents': (
                    'Upload at least one ID or proof of residency photo to register.'
                )
            })

        birth_date = attrs.get('birth_date')
        guardian_id = attrs.get('guardian_id')

        # Calculate precise age server-side
        age = None
        if birth_date:
            today = date.today()
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

        # Enforce minor constraint barrier
        if age is not None and age < 18 and not guardian_id:
            raise serializers.ValidationError({"guardian_id": "Residents under 18 must provide a guardian's Registered ID."})
        
        barangay_id = attrs.get('barangay_id')
        if barangay_id:
            try:
                attrs['barangay_obj'] = Barangay.objects.get(id=barangay_id)
            except Barangay.DoesNotExist:
                raise serializers.ValidationError({"barangay_id": "Selected Barangay does not exist."})
            
        # Validate Guardian ID mapping
        if guardian_id:
            try:
                # The mobile app uses 'username' as the Barangay ID/Registered ID
                guardian_user = User.objects.get(username=guardian_id, role=User.Role.RESIDENT)
                # Stash the actual Resident object in attrs for the create() method
                attrs['guardian_resident'] = guardian_user.profile
            except (User.DoesNotExist, Resident.DoesNotExist):
                raise serializers.ValidationError({"guardian_id": "No resident found with this Registered ID."})
            
        return attrs

    def create(self, validated_data):
        validated_data.pop('privacy_consent')
        privacy_consent_version = validated_data.pop(
            'privacy_consent_version'
        )

        profile_data = {
            'full_name': validated_data.pop('full_name'),
            'birth_date': validated_data.pop('birth_date'),
            'voter_status': validated_data.pop('voter_status', False),
            'contact_number': validated_data.pop('contact_number', ''),
            'purok': validated_data.pop('purok', None),
            'philsys_id_number': validated_data.pop('philsys_id_number', None),
            'philsys_id_photo': validated_data.pop('philsys_id_photo', None),
            'secondary_id_type': validated_data.pop('secondary_id_type', None),
            'secondary_id_photo': validated_data.pop('secondary_id_photo', None),
            'utility_billing_type': validated_data.pop('utility_billing_type', None),
            'utility_billing_photo': validated_data.pop('utility_billing_photo', None),
        }
        
        # Extract the resolved guardian Resident objects
        guardian_resident = validated_data.pop('guardian_resident', None)
        validated_data.pop('guardian_id', None)
        barangay_obj = validated_data.pop('barangay_obj', None)
        validated_data.pop('barangay_id', None)

        with transaction.atomic():
            user = User.objects.create_user(
                username=validated_data['username'],
                email=validated_data.get('email', ''),
                password=validated_data['password'],
                role=User.Role.RESIDENT,
                barangay=barangay_obj
            )
            Resident.objects.create(
                user=user,
                guardian=guardian_resident,
                privacy_consent_version=privacy_consent_version,
                privacy_consent_at=timezone.now(),
                **profile_data,
            )

        return user
