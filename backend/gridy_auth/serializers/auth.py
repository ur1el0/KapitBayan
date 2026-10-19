from django.db import transaction
from django.utils import timezone
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from gridy_auth.models import User, RefreshSession

EMAIL_SIGN_IN_ROLES = {
    User.Role.ADMIN,
    User.Role.FIELD_OFFICIAL,
    User.Role.BARANGAY_OPERATOR,
}

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.email if user.role in EMAIL_SIGN_IN_ROLES else user.username
        full_name = getattr(user.profile, 'full_name', None) if hasattr(user, 'profile') else None
        if not full_name:
            identity = user.email if user.role in EMAIL_SIGN_IN_ROLES else user.username
            full_name = f"{user.first_name} {user.last_name}".strip() or identity
        token['full_name'] = full_name
        token['role'] = user.role
        token['barangay_id'] = user.barangay.id if user.barangay else None
        return token

    def validate(self, attrs):
        # Prefer email matches so official accounts use their formal sign-in identity.
        identifier = attrs.get(self.username_field, '').strip()
        if identifier:
            email_matches = list(
                User.objects.filter(email__iexact=identifier).order_by('pk')[:2]
            )
            if len(email_matches) > 1:
                # Resident households may intentionally share an email address.
                # Never pick an arbitrary account when that address is used to log in.
                username_matches = list(
                    User.objects.filter(username__iexact=identifier).order_by('pk')[:2]
                )
                if (
                    len(username_matches) != 1
                    or username_matches[0].role in EMAIL_SIGN_IN_ROLES
                ):
                    raise AuthenticationFailed(
                        'No active account found with the given credentials.'
                    )
                matched_user = username_matches[0]
            elif email_matches:
                matched_user = email_matches[0]
            else:
                matched_user = User.objects.filter(username__iexact=identifier).order_by('pk').first()
            if matched_user:
                if (
                    matched_user.role in EMAIL_SIGN_IN_ROLES
                    and identifier.casefold() != matched_user.email.strip().casefold()
                ):
                    raise serializers.ValidationError({
                        'detail': 'Official accounts must sign in with their email address.'
                    })
                attrs[self.username_field] = matched_user.username

        data = super().validate(attrs)
        if self.user.role not in {
            User.Role.ADMIN,
            User.Role.RESIDENT,
            User.Role.FIELD_OFFICIAL,
            User.Role.BARANGAY_OPERATOR,
        }:
            raise serializers.ValidationError({"detail": "This account role is no longer supported."})
        full_name = getattr(self.user.profile, 'full_name', None) if hasattr(self.user, 'profile') else None
        if not full_name:
            identity = self.user.email if self.user.role in EMAIL_SIGN_IN_ROLES else self.user.username
            full_name = f"{self.user.first_name} {self.user.last_name}".strip() or identity
        data['user'] = {
            'id': self.user.id,
            'username': self.user.email if self.user.role in EMAIL_SIGN_IN_ROLES else self.user.username,
            'email': self.user.email,
            'role': self.user.role,
            'barangay_id': self.user.barangay.id if self.user.barangay else None,
            'is_superuser': self.user.is_superuser,
            'full_name': full_name,
        }
        return data


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

class PasswordResetConfirmSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True, min_length=8)
    uidb64 = serializers.CharField(write_only=True)
    token = serializers.CharField(write_only=True)

    def validate(self, data):
        try:
            uid = force_str(urlsafe_base64_decode(data['uidb64']))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError({"uidb64": "Invalid user ID"})
        
        if not default_token_generator.check_token(user, data['token']):
            raise serializers.ValidationError({"token": "Invalid or expired token"})

        try:
            validate_password(data['new_password'], user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"new_password": list(exc.messages)})
        
        self.context['user'] = user
        return data
    
    def save(self):
        user = self.context['user']
        new_password = self.validated_data['new_password']

        with transaction.atomic():
            user.set_password(new_password)
            user.save(update_fields=['password'])

            RefreshSession.objects.filter(
                user=user,
                is_revoked=False,
            ).update(is_revoked=True)

            active_outstanding_tokens = OutstandingToken.objects.filter(
                user=user,
                expires_at__gt=timezone.now(),
            )
            for outstanding_token in active_outstanding_tokens:
                BlacklistedToken.objects.get_or_create(
                    token=outstanding_token,
                )
        return user


class RefreshSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RefreshSession
        fields = ['id', 'ip_address', 'user_agent', 'created_at', 'expires_at', 'is_revoked']
        read_only_fields = fields
