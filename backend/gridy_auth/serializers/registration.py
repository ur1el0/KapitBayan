from rest_framework import serializers
from django.db import transaction
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from gridy_auth.models import User, Resident, Barangay
from django.conf import settings
from django.utils import timezone
from django.db.models import Q
from gridy_communications.admin_notifications import notify_barangay_admins
from .base import ResidentEvidenceImageField

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
    purok = serializers.CharField(write_only=True, max_length=100)
    address_details = serializers.CharField(
        write_only=True, required=False, allow_blank=True, max_length=255
    )
    barangay_id = serializers.IntegerField(
        write_only=True,
        required=True,
        min_value=1,
    )
    guardian_id = serializers.CharField(write_only=True, required=False, allow_blank=True)
    guardian_relationship = serializers.ChoiceField(
        choices=Resident.GuardianRelationship.choices,
        write_only=True,
        required=False,
    )
    guardianship_evidence = ResidentEvidenceImageField(
        write_only=True,
        required=False,
        allow_null=True,
    )
    philsys_id_number = serializers.CharField(write_only=True, required=False, allow_blank=True)
    philsys_id_photo = ResidentEvidenceImageField(write_only=True, required=False, allow_null=True)
    secondary_id_type = serializers.CharField(write_only=True, required=False, allow_blank=True)
    secondary_id_photo = ResidentEvidenceImageField(write_only=True, required=False, allow_null=True)
    utility_billing_type = serializers.CharField(write_only=True, required=False, allow_blank=True)
    utility_billing_photo = ResidentEvidenceImageField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'full_name', 'birth_date', 'voter_status', 
            'contact_number', 'purok', 'address_details', 'barangay_id', 'guardian_id',
            'guardian_relationship', 'guardianship_evidence',
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

    def validate_username(self, value):
        # Authentication treats resident usernames case-insensitively. Store
        # self-service names in one canonical form and reject existing variants
        # so a later login cannot resolve to an arbitrary account.
        username = value.strip().lower()
        if User.objects.filter(username__iexact=username).exists():
            raise serializers.ValidationError(
                "This username is already in use, regardless of capitalization."
            )
        return username

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
        guardian_relationship = attrs.get('guardian_relationship')
        guardianship_evidence = attrs.get('guardianship_evidence')

        today = timezone.localdate()
        if birth_date and birth_date > today:
            raise serializers.ValidationError({"birth_date": "Birth date cannot be in the future."})
        age = (
            today.year - birth_date.year
            - ((today.month, today.day) < (birth_date.month, birth_date.day))
        ) if birth_date else None
        
        barangay_obj = None
        barangay_id = attrs.get('barangay_id')
        if barangay_id:
            try:
                barangay_obj = Barangay.objects.get(id=barangay_id)
            except Barangay.DoesNotExist:
                raise serializers.ValidationError({"barangay_id": "Selected Barangay does not exist."})
            
            if not barangay_obj.is_approved_and_active():
                raise serializers.ValidationError({
                    "barangay_id": "Selected Barangay is not approved or is currently inactive for registration."
                })
            attrs['barangay_obj'] = barangay_obj
            
        # Minors require a linked adult, a stated relationship, and evidence for a
        # Barangay Admin to review. These fields support human review; they do not
        # make a legal determination automatically.
        if age is not None and age < 18:
            missing_guardian_data = {}
            if not guardian_id:
                missing_guardian_data["guardian_id"] = (
                    "Residents under 18 must provide a verified adult guardian's Registered ID."
                )
            if not guardian_relationship:
                missing_guardian_data["guardian_relationship"] = (
                    "Select the parent or guardian's relationship to the resident."
                )
            if not guardianship_evidence:
                missing_guardian_data["guardianship_evidence"] = (
                    "Upload supporting evidence for the Barangay Admin to review."
                )
            if missing_guardian_data:
                raise serializers.ValidationError(missing_guardian_data)
        if age is not None and age >= 18 and guardian_id:
            raise serializers.ValidationError({
                "guardian_id": "A guardian account may only be linked for residents under 18."
            })
        if age is not None and age >= 18 and (guardian_relationship or guardianship_evidence):
            raise serializers.ValidationError({
                "guardian_relationship": "Guardian details are only used for residents under 18."
            })

        if guardian_id:
            guardians = User.objects.filter(
                username__iexact=guardian_id.strip(),
                role=User.Role.RESIDENT,
            ).select_related("profile")
            guardian_user = guardians.first()
            if guardian_user is None or guardians.count() > 1 or not hasattr(guardian_user, "profile"):
                raise serializers.ValidationError({
                    "guardian_id": "No resident found with this Registered ID."
                })

            guardian_resident = guardian_user.profile
            guardian_age = today.year - guardian_resident.birth_date.year - (
                (today.month, today.day)
                < (guardian_resident.birth_date.month, guardian_resident.birth_date.day)
            )
            if not guardian_user.is_active or not guardian_resident.is_verified:
                raise serializers.ValidationError({
                    "guardian_id": "The guardian account must be active and verified."
                })
            if guardian_age < 18:
                raise serializers.ValidationError({
                    "guardian_id": "The guardian must be at least 18 years old."
                })
            if barangay_obj is None or guardian_user.barangay_id != barangay_obj.pk:
                raise serializers.ValidationError({
                    "guardian_id": "The guardian must be registered in the selected Barangay."
                })
            attrs['guardian_resident'] = guardian_resident
            
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
            'purok': validated_data.pop('purok'),
            'address_details': validated_data.pop('address_details', ''),
            'philsys_id_number': validated_data.pop('philsys_id_number', None),
            'philsys_id_photo': validated_data.pop('philsys_id_photo', None),
            'secondary_id_type': validated_data.pop('secondary_id_type', None),
            'secondary_id_photo': validated_data.pop('secondary_id_photo', None),
            'utility_billing_type': validated_data.pop('utility_billing_type', None),
            'utility_billing_photo': validated_data.pop('utility_billing_photo', None),
            'guardian_relationship': validated_data.pop('guardian_relationship', ''),
            'guardianship_evidence': validated_data.pop('guardianship_evidence', None),
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
            notify_barangay_admins(
                barangay_id=user.barangay_id,
                notification_type='registration',
            )

        return user
