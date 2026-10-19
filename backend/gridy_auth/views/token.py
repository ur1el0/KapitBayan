from datetime import datetime

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from gridy_audit.services import get_client_ip
from gridy_auth.authentication import is_production_test_account
from gridy_auth.models import RefreshSession, User
from gridy_auth.serializers import CustomTokenObtainPairSerializer


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    throttle_scope = 'auth_login'

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            refresh_token_str = response.data.get('refresh')

            # Extract UUID JTI identifier and expiration date from refresh token payload
            try:
                refresh_token = RefreshToken(refresh_token_str)
                jti = refresh_token['jti']
                exp_timestamp = refresh_token['exp']
                expires_at = datetime.fromtimestamp(exp_timestamp, tz=timezone.UTC)
            except Exception:
                return Response({"detail": "Token structure invalid."}, status=status.HTTP_400_BAD_REQUEST)

            # Get user agent and client connection IP
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            ip_address = get_client_ip(request)

            # Fetch the user instance based on token claim
            user_id = refresh_token['user_id']
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

            # 1. Enforce Resident Verification Status
            if user.role == User.Role.RESIDENT:
                if hasattr(user, 'profile') and not user.profile.is_verified:
                    return Response(
                        {"detail": "Your resident account is pending verification by the admin. Please try again later."},
                        status=status.HTTP_403_FORBIDDEN
                    )

            # Reject legacy or unknown roles even if an old database row still exists.
            if user.role not in {
                User.Role.ADMIN,
                User.Role.RESIDENT,
                User.Role.FIELD_OFFICIAL,
                User.Role.BARANGAY_OPERATOR,
            }:
                RefreshSession.objects.filter(user=user, is_revoked=False).update(is_revoked=True)
                return Response(
                    {"detail": "This account role is no longer supported. Contact your Barangay administrator."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            # 2. SECURITY: Enforce Active Status for Barangay Admins & Field Officials
            if user.role in [User.Role.ADMIN, User.Role.FIELD_OFFICIAL]:
                if not user.is_active:
                    return Response(
                        {"detail": "Your official account is pending verification. Only active, verified barangay personnel can log in."},
                        status=status.HTTP_403_FORBIDDEN
                    )

            # Create session in the database
            RefreshSession.objects.create(
                user=user,
                refresh_token_jti=jti,
                ip_address=ip_address,
                user_agent=user_agent,
                expires_at=expires_at
            )

            # Set refresh token in HttpOnly SameSite secure cookie
            secure_cookie = not settings.DEBUG
            samesite_policy = getattr(settings, 'REFRESH_COOKIE_SAMESITE', 'Strict')
            response.set_cookie(
                key='refresh_token',
                value=refresh_token_str,
                httponly=True,
                secure=secure_cookie,
                samesite=samesite_policy,
                expires=expires_at,
                path='/api/v1/auth/',
            )

            # Delete the raw refresh token string from the JSON payload
            del response.data['refresh']

        return response


class CustomTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        # Retrieve refresh token from browser cookies or request payload
        refresh_token_str = request.COOKIES.get('refresh_token') or request.data.get('refresh')
        if not refresh_token_str:
            return Response({"detail": "Session cookie or refresh token missing."}, status=status.HTTP_401_UNAUTHORIZED)

        # Validate the token and find its active session before rotating it.
        try:
            old_token = RefreshToken(refresh_token_str)
            old_jti = old_token['jti']
            session = RefreshSession.objects.filter(
                refresh_token_jti=old_jti,
                is_revoked=False,
            ).first()
            if not session:
                return Response(
                    {"detail": "Session is revoked or invalid."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
        except (TokenError, InvalidToken):
            return Response(
                {"detail": "Session token invalid or expired."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        except Exception:
            return Response(
                {"detail": "Invalid token details."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if is_production_test_account(session.user):
            RefreshSession.objects.filter(
                user=session.user,
                is_revoked=False,
            ).update(is_revoked=True)
            return Response(
                {"detail": "Session is revoked or invalid."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if session.user.role not in {
            User.Role.ADMIN,
            User.Role.RESIDENT,
            User.Role.FIELD_OFFICIAL,
            User.Role.BARANGAY_OPERATOR,
        }:
            session.is_revoked = True
            session.save(update_fields=["is_revoked"])
            return Response(
                {"detail": "Session is revoked or invalid."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if session.user.role == User.Role.RESIDENT:
            resident_profile = getattr(session.user, "profile", None)
            if resident_profile is None or not resident_profile.is_verified:
                session.is_revoked = True
                session.save(update_fields=["is_revoked"])
                return Response(
                    {
                        "detail": (
                            "Your resident account is not verified. "
                            "Please contact your barangay administrator."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        # Let SimpleJWT validate and rotate only after the session passes the guard.
        serializer = self.get_serializer(data={'refresh': refresh_token_str})
        try:
            serializer.is_valid(raise_exception=True)
        except (TokenError, InvalidToken):
            return Response(
                {"detail": "Session token invalid or expired."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        access_token_str = serializer.validated_data.get('access')
        new_refresh_token_str = serializer.validated_data.get('refresh')

        # Handle token rotation boundary checks
        if new_refresh_token_str:
            try:
                new_token = RefreshToken(new_refresh_token_str)
                new_jti = new_token['jti']
                new_exp = new_token['exp']
                new_expires_at = datetime.fromtimestamp(new_exp, tz=timezone.UTC)

                with transaction.atomic():
                    # Revoke the old session mapping and save the new active rotated JTI session
                    session.is_revoked = True
                    session.save()

                    RefreshSession.objects.create(
                        user=session.user,
                        refresh_token_jti=new_jti,
                        ip_address=session.ip_address,
                        user_agent=session.user_agent,
                        expires_at=new_expires_at
                    )
            except Exception:
                return Response({"detail": "Rotation credentials failed."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        response_data = {"access": access_token_str}
        response = Response(response_data, status=status.HTTP_200_OK)

        # Update cookie with the rotated refresh token
        if new_refresh_token_str:
            secure_cookie = not settings.DEBUG
            samesite_policy = getattr(settings, 'REFRESH_COOKIE_SAMESITE', 'Strict')
            response.set_cookie(
                key='refresh_token',
                value=new_refresh_token_str,
                httponly=True,
                secure=secure_cookie,
                samesite=samesite_policy,
                expires=new_expires_at,
                path='/api/v1/auth/',
            )

        return response
