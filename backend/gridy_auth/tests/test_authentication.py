from urllib.parse import urlencode
from datetime import timedelta

from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.tokens import RefreshToken

from gridy_auth.models import Barangay, RefreshSession, Resident, User
from .base import IsolatedAuthAPITestCase


class AuthAPITests(IsolatedAuthAPITestCase):
    def setUp(self):
        self.barangay = Barangay.objects.create(name="Auth Fixture Barangay")
        self.username = "resident_test"
        self.password = "SecurePassword123!"
        self.user = User.objects.create_user(
            username=self.username,
            password=self.password,
            email="resident@example.com",
            role=User.Role.RESIDENT,
        )

    def test_user_login_success(self):
        url = reverse('auth_login')
        payload = {
            "username": self.username,
            "password": self.password
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertNotIn('refresh', response.data)
        self.assertIn('refresh_token', response.cookies)
        cookie = response.cookies['refresh_token']
        self.assertTrue(cookie['httponly'])
        self.assertEqual(cookie['samesite'], 'Strict')
        self.assertEqual(cookie['path'], '/api/v1/auth/')

    def test_barangay_operator_can_login_and_access_only_onboarding_and_account_support(self):
        reviewer = User.objects.create_user(
            username="barangay-operator_reviewer",
            password=self.password,
            email="reviewer@example.test",
            role="BARANGAY_OPERATOR",
        )
        login_response = self.client.post(
            reverse("auth_login"),
            {"username": reviewer.email, "password": self.password},
            format="json",
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertTrue(RefreshSession.objects.filter(user=reviewer, is_revoked=False).exists())

        access = login_response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        profile_response = self.client.get(reverse("auth_me"))
        self.assertEqual(profile_response.status_code, status.HTTP_200_OK)
        self.assertEqual(profile_response.data["role"], User.Role.BARANGAY_OPERATOR)

        support_response = self.client.get("/api/v1/auth/platform/accounts/")
        self.assertEqual(support_response.status_code, status.HTTP_200_OK)

        service_response = self.client.get("/api/v1/auth/pending-residents/")
        self.assertEqual(service_response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.credentials()
        refresh = login_response.cookies["refresh_token"].value
        refresh_response = self.client.post(
            reverse("auth_token_refresh"),
            {"refresh": refresh},
            format="json",
        )
        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)

    def test_production_login_blocks_configured_username_and_email_identifier(self):
        with self.settings(
            DEBUG=False,
            BLOCKED_PRODUCTION_LOGIN_USERNAMES={self.username.upper()},
        ):
            for identifier in (self.username, self.user.email):
                response = self.client.post(
                    reverse('auth_login'),
                    {"username": identifier, "password": self.password},
                    format='json',
                )
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.assertFalse(
            RefreshSession.objects.filter(user=self.user, is_revoked=False).exists()
        )

    def test_production_login_blocks_reserved_demo_email_domain(self):
        self.user.email = "seeded@gridy.local"
        self.user.save(update_fields=["email"])

        with self.settings(DEBUG=False, BLOCKED_PRODUCTION_LOGIN_USERNAMES=()):
            response = self.client.post(
                reverse('auth_login'),
                {"username": self.username, "password": self.password},
                format='json',
            )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_production_login_allows_user_not_in_test_account_blocklist(self):
        with self.settings(
            DEBUG=False,
            BLOCKED_PRODUCTION_LOGIN_USERNAMES={"another_test_user"},
        ):
            response = self.client.post(
                reverse('auth_login'),
                {"username": self.username, "password": self.password},
                format='json',
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_production_blocked_account_cannot_refresh_or_use_existing_access_token(self):
        login_response = self.client.post(
            reverse('auth_login'),
            {"username": self.username, "password": self.password},
            format='json',
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        access_token = login_response.data["access"]
        refresh_token = login_response.cookies["refresh_token"].value

        with self.settings(
            DEBUG=False,
            BLOCKED_PRODUCTION_LOGIN_USERNAMES={self.username},
        ):
            self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
            protected_response = self.client.get(reverse("auth_me"))
            self.assertEqual(
                protected_response.status_code,
                status.HTTP_401_UNAUTHORIZED,
            )

            self.client.credentials()
            refresh_response = self.client.post(
                reverse("auth_token_refresh"),
                {"refresh": refresh_token},
                format="json",
            )
            self.assertEqual(
                refresh_response.status_code,
                status.HTTP_401_UNAUTHORIZED,
            )

        self.assertFalse(
            RefreshSession.objects.filter(user=self.user, is_revoked=False).exists()
        )

    def test_production_blocked_account_cannot_start_django_session(self):
        with self.settings(
            DEBUG=False,
            BLOCKED_PRODUCTION_LOGIN_USERNAMES={self.username},
        ):
            self.assertFalse(
                self.client.login(username=self.username, password=self.password)
            )

    def test_local_debug_mode_allows_configured_demo_account(self):
        with self.settings(
            DEBUG=True,
            BLOCKED_PRODUCTION_LOGIN_USERNAMES={self.username},
        ):
            response = self.client.post(
                reverse('auth_login'),
                {"username": self.username, "password": self.password},
                format='json',
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_password_reset_revokes_all_existing_refresh_sessions(self):
        login_url = reverse("auth_login")
        login_payload = {
            "username": self.username,
            "password": self.password,
        }

        first_login = self.client.post(
            login_url,
            login_payload,
            format="json",
        )
        self.assertEqual(first_login.status_code, status.HTTP_200_OK)
        first_refresh_token = first_login.cookies["refresh_token"].value

        second_login = self.client.post(
            login_url,
            login_payload,
            format="json",
        )
        self.assertEqual(second_login.status_code, status.HTTP_200_OK)
        second_refresh_token = second_login.cookies["refresh_token"].value

        self.assertEqual(
            RefreshSession.objects.filter(
                user=self.user,
                is_revoked=False,
            ).count(),
            2,
        )

        reset_response = self.client.post(
            reverse("password_reset_confirm"),
            {
                "uidb64": urlsafe_base64_encode(force_bytes(self.user.pk)),
                "token": default_token_generator.make_token(self.user),
                "new_password": "NewSecurePassword123!",
            },
            format="json",
        )
        self.assertEqual(reset_response.status_code, status.HTTP_200_OK)

        self.assertEqual(
            RefreshSession.objects.filter(
                user=self.user,
                is_revoked=False,
            ).count(),
            0,
        )

        active_outstanding_tokens = OutstandingToken.objects.filter(
            user=self.user,
            expires_at__gt=timezone.now(),
        )
        self.assertTrue(active_outstanding_tokens.exists())

        for outstanding_token in active_outstanding_tokens:
            self.assertTrue(
                BlacklistedToken.objects.filter(
                    token=outstanding_token,
                ).exists()
            )

        self.client.cookies.pop("refresh_token", None)
        for old_refresh_token in (
            first_refresh_token,
            second_refresh_token,
        ):
            refresh_response = self.client.post(
                reverse("auth_token_refresh"),
                {"refresh": old_refresh_token},
                format="json",
            )
            self.assertEqual(
                refresh_response.status_code,
                status.HTTP_401_UNAUTHORIZED,
            )

        new_login = self.client.post(
            login_url,
            {
                "username": self.username,
                "password": "NewSecurePassword123!",
            },
            format="json",
        )
        self.assertEqual(new_login.status_code, status.HTTP_200_OK)
        self.assertEqual(
            RefreshSession.objects.filter(
                user=self.user,
                is_revoked=False,
            ).count(),
            1,
        )

    def test_token_refresh_denied_after_resident_verification_revoked(self):
        resident_profile = Resident.objects.create(
            user=self.user,
            full_name="Verification Test Resident",
            birth_date="1995-05-15",
            is_verified=True,
        )

        login_response = self.client.post(
            reverse("auth_login"),
            {
                "username": self.username,
                "password": self.password,
            },
            format="json",
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

        resident_profile.is_verified = False
        resident_profile.save(update_fields=["is_verified"])

        refresh_response = self.client.post(reverse("auth_token_refresh"))

        self.assertEqual(
            refresh_response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_token_refresh_via_cookie_success(self):
        # 1. Login to establish cookie
        login_url = reverse('auth_login')
        login_payload = {
            "username": self.username,
            "password": self.password
        }

        Resident.objects.create(
            user=self.user,
            full_name="Verified Test Resident",
            birth_date="1995-05-15",
            is_verified=True,
        )

        login_response = self.client.post(login_url, login_payload, format='json')
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

        # Get initial session count
        self.assertEqual(RefreshSession.objects.filter(user=self.user, is_revoked=False).count(), 1)
        old_session = RefreshSession.objects.filter(user=self.user, is_revoked=False).first()

        # 2. Call refresh endpoint (attaches cookies automatically)
        refresh_url = reverse('auth_token_refresh')
        refresh_response = self.client.post(refresh_url)
        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        self.assertIn('access', refresh_response.data)

        # Verify old JTI session is revoked and a new active one is created
        old_session.refresh_from_db()
        self.assertTrue(old_session.is_revoked)
        self.assertEqual(RefreshSession.objects.filter(user=self.user, is_revoked=False).count(), 1)
        self.assertIn('refresh_token', refresh_response.cookies)
        refresh_cookie = refresh_response.cookies['refresh_token']
        self.assertTrue(refresh_cookie['httponly'])
        self.assertEqual(refresh_cookie['samesite'], 'Strict')
        self.assertEqual(refresh_cookie['path'], '/api/v1/auth/')

    def test_refresh_cookie_samesite_policy_is_configurable(self):
        login_url = reverse('auth_login')
        login_payload = {
            "username": self.username,
            "password": self.password,
        }
        with self.settings(REFRESH_COOKIE_SAMESITE='Lax'):
            response = self.client.post(login_url, login_payload, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.cookies['refresh_token']['samesite'], 'Lax')

        with self.settings(REFRESH_COOKIE_SAMESITE='None'):
            response = self.client.post(login_url, login_payload, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.cookies['refresh_token']['samesite'], 'None')

    def test_token_refresh_fails_with_revoked_session(self):
        # 1. Login to establish cookie
        login_url = reverse('auth_login')
        login_payload = {
            "username": self.username,
            "password": self.password
        }
        login_response = self.client.post(login_url, login_payload, format='json')
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        # 2. Revoke the session in database
        RefreshSession.objects.filter(user=self.user).update(is_revoked=True)
        # 3. Call refresh endpoint and verify rejection
        refresh_url = reverse('auth_token_refresh')
        refresh_response = self.client.post(refresh_url)
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_password_reset_rejects_numeric_passwords(self):
        response = self.client.post(
            reverse("password_reset_confirm"),
            {
                "uidb64": urlsafe_base64_encode(force_bytes(self.user.pk)),
                "token": default_token_generator.make_token(self.user),
                "new_password": "12345678",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("new_password", response.data)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.password))

    def test_logout_invalidates_cookie_and_session(self):
        # 1. Login to establish cookie
        login_url = reverse('auth_login')
        login_payload = {
            "username": self.username,
            "password": self.password
        }
        login_response = self.client.post(login_url, login_payload, format='json')
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        # 2. Call logout view
        logout_url = reverse('auth_logout')
        logout_response = self.client.post(logout_url)
        self.assertEqual(logout_response.status_code, status.HTTP_200_OK)
        # Verify cookie is cleared and both scoped and legacy paths are expired
        cookie = logout_response.cookies.get('refresh_token')
        self.assertTrue(not cookie or not cookie.value or cookie['max-age'] == 0)
        cookie_paths = {c['path'] for c in logout_response.cookies.values() if c.key == 'refresh_token'}
        self.assertEqual(cookie_paths, {'/api/v1/auth/', '/'})
        # Verify active session is revoked in database
        self.assertEqual(RefreshSession.objects.filter(user=self.user, is_revoked=False).count(), 0)

    def test_logout_expires_legacy_root_path_cookie(self):
        login_url = reverse('auth_login')
        login_payload = {
            "username": self.username,
            "password": self.password,
        }
        login_response = self.client.post(login_url, login_payload, format='json')
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

        # Simulate a client presenting a legacy cookie set with root path (Path=/)
        legacy_refresh = RefreshToken.for_user(self.user)
        legacy_session = RefreshSession.objects.create(
            user=self.user,
            refresh_token_jti=legacy_refresh['jti'],
            user_agent="Legacy Browser",
            ip_address="127.0.0.1",
            expires_at=timezone.now() + timezone.timedelta(days=7),
            is_revoked=False,
        )
        self.client.cookies['refresh_token'] = str(legacy_refresh)

        logout_url = reverse('auth_logout')
        logout_response = self.client.post(logout_url)
        self.assertEqual(logout_response.status_code, status.HTTP_200_OK)

        # Confirm legacy database session was revoked
        legacy_session.refresh_from_db()
        self.assertTrue(legacy_session.is_revoked)

        # Confirm the response emits both expiry instructions
        morsels = [c for c in logout_response.cookies.values() if c.key == 'refresh_token']
        self.assertEqual(len(morsels), 2)
        emitted_paths = {c['path'] for c in morsels}
        self.assertEqual(emitted_paths, {'/api/v1/auth/', '/'})
        for morsel in morsels:
            self.assertEqual(morsel['max-age'], 0)
            self.assertTrue(morsel['httponly'])

        # Confirm serialized Set-Cookie output contains both path instructions
        serialized = logout_response.cookies.output()
        self.assertIn('Path=/api/v1/auth/', serialized)
        self.assertIn('Path=/', serialized)

    def test_logout_revokes_duplicate_tokens_from_multiple_paths(self):
        # 1. Provision two distinct refresh tokens and active database sessions for the user
        scoped_refresh = RefreshToken.for_user(self.user)
        scoped_session = RefreshSession.objects.create(
            user=self.user,
            refresh_token_jti=scoped_refresh['jti'],
            user_agent="Browser Scoped",
            ip_address="127.0.0.1",
            expires_at=timezone.now() + timezone.timedelta(days=7),
            is_revoked=False,
        )

        legacy_refresh = RefreshToken.for_user(self.user)
        legacy_session = RefreshSession.objects.create(
            user=self.user,
            refresh_token_jti=legacy_refresh['jti'],
            user_agent="Browser Legacy",
            ip_address="127.0.0.1",
            expires_at=timezone.now() + timezone.timedelta(days=7),
            is_revoked=False,
        )

        # 2. Simulate raw browser request containing duplicate cookie names from overlapping paths
        raw_cookie_header = f"refresh_token={scoped_refresh}; refresh_token={legacy_refresh}"
        logout_url = reverse('auth_logout')
        logout_response = self.client.post(logout_url, HTTP_COOKIE=raw_cookie_header)
        self.assertEqual(logout_response.status_code, status.HTTP_200_OK)

        # 3. Verify BOTH sessions were revoked in database and both JTIs blacklisted
        scoped_session.refresh_from_db()
        self.assertTrue(scoped_session.is_revoked)

        legacy_session.refresh_from_db()
        self.assertTrue(legacy_session.is_revoked)

        self.assertTrue(
            BlacklistedToken.objects.filter(token__jti=scoped_refresh['jti']).exists()
        )
        self.assertTrue(
            BlacklistedToken.objects.filter(token__jti=legacy_refresh['jti']).exists()
        )

        # 4. Verify that remaining active sessions count for user is 0
        self.assertEqual(RefreshSession.objects.filter(user=self.user, is_revoked=False).count(), 0)

        # 5. Verify both cookie paths were expired in response
        morsels = [c for c in logout_response.cookies.values() if c.key == 'refresh_token']
        self.assertEqual(len(morsels), 2)
        emitted_paths = {c['path'] for c in morsels}
        self.assertEqual(emitted_paths, {'/api/v1/auth/', '/'})
        for morsel in morsels:
            self.assertEqual(morsel['max-age'], 0)
            self.assertTrue(morsel['httponly'])

    def test_logout_succeeds_with_malformed_json_body_and_revokes_cookie_session(self):
        refresh = RefreshToken.for_user(self.user)
        session = RefreshSession.objects.create(
            user=self.user,
            refresh_token_jti=refresh['jti'],
            user_agent="Browser Test",
            ip_address="127.0.0.1",
            expires_at=timezone.now() + timezone.timedelta(days=7),
            is_revoked=False,
        )
        self.client.cookies['refresh_token'] = str(refresh)

        logout_url = reverse('auth_logout')
        logout_response = self.client.post(
            logout_url,
            data="invalid-json-body{",
            content_type="application/json",
        )
        self.assertEqual(logout_response.status_code, status.HTTP_200_OK)

        session.refresh_from_db()
        self.assertTrue(session.is_revoked)
        self.assertTrue(BlacklistedToken.objects.filter(token__jti=refresh['jti']).exists())

        cookie_paths = {c['path'] for c in logout_response.cookies.values() if c.key == 'refresh_token'}
        self.assertEqual(cookie_paths, {'/api/v1/auth/', '/'})

    def test_logout_ignores_non_string_refresh_values_in_body(self):
        logout_url = reverse('auth_logout')
        non_string_payloads = [
            {"refresh": 12345},
            {"refresh": ["token_a", "token_b"]},
            {"refresh": {"nested": "token"}},
            {"refresh": True},
        ]
        for payload in non_string_payloads:
            iter_refresh = RefreshToken.for_user(self.user)
            iter_session = RefreshSession.objects.create(
                user=self.user,
                refresh_token_jti=iter_refresh['jti'],
                user_agent="Browser Test",
                ip_address="127.0.0.1",
                expires_at=timezone.now() + timezone.timedelta(days=7),
                is_revoked=False,
            )
            self.client.cookies['refresh_token'] = str(iter_refresh)
            logout_response = self.client.post(logout_url, payload, format='json')
            self.assertEqual(logout_response.status_code, status.HTTP_200_OK)
            iter_session.refresh_from_db()
            self.assertTrue(iter_session.is_revoked)

    def test_logout_succeeds_with_unsupported_content_type(self):
        refresh = RefreshToken.for_user(self.user)
        session = RefreshSession.objects.create(
            user=self.user,
            refresh_token_jti=refresh['jti'],
            user_agent="Browser Test",
            ip_address="127.0.0.1",
            expires_at=timezone.now() + timezone.timedelta(days=7),
            is_revoked=False,
        )
        self.client.cookies['refresh_token'] = str(refresh)

        logout_url = reverse('auth_logout')
        logout_response = self.client.post(
            logout_url,
            data="<xml>unsupported</xml>",
            content_type="application/xml",
        )
        self.assertEqual(logout_response.status_code, status.HTTP_200_OK)
        session.refresh_from_db()
        self.assertTrue(session.is_revoked)

    def test_logout_revokes_session_from_form_encoded_body(self):
        # 1. Test application/x-www-form-urlencoded with QueryDict parsing
        refresh = RefreshToken.for_user(self.user)
        session = RefreshSession.objects.create(
            user=self.user,
            refresh_token_jti=refresh['jti'],
            user_agent="Form-Encoded Client",
            ip_address="127.0.0.1",
            expires_at=timezone.now() + timezone.timedelta(days=7),
            is_revoked=False,
        )

        logout_url = reverse('auth_logout')
        logout_response = self.client.post(
            logout_url,
            data=urlencode({'refresh': str(refresh)}),
            content_type='application/x-www-form-urlencoded',
        )
        self.assertEqual(logout_response.status_code, status.HTTP_200_OK)
        session.refresh_from_db()
        self.assertTrue(session.is_revoked)
        self.assertTrue(
            BlacklistedToken.objects.filter(token__jti=refresh['jti']).exists()
        )

        # 2. Test multipart form data
        refresh_mp = RefreshToken.for_user(self.user)
        session_mp = RefreshSession.objects.create(
            user=self.user,
            refresh_token_jti=refresh_mp['jti'],
            user_agent="Multipart Client",
            ip_address="127.0.0.1",
            expires_at=timezone.now() + timezone.timedelta(days=7),
            is_revoked=False,
        )
        logout_response_mp = self.client.post(
            logout_url,
            data={'refresh': str(refresh_mp)},
            format='multipart',
        )
        self.assertEqual(logout_response_mp.status_code, status.HTTP_200_OK)
        session_mp.refresh_from_db()
        self.assertTrue(session_mp.is_revoked)
        self.assertTrue(
            BlacklistedToken.objects.filter(token__jti=refresh_mp['jti']).exists()
        )
