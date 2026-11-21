from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

from django.db import connections
from django.test import TransactionTestCase, override_settings, skipUnlessDBFeature
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIRequestFactory

from gridy_auth.models import APIRateLimitWindow
from gridy_auth.throttling import SharedDatabaseScopedRateThrottle
from gridy_auth.views.staff import StaffManagementViewSet

from .base import IsolatedAuthAPITestCase


class AuthScopedThrottleTests(IsolatedAuthAPITestCase):
    def _rates_patch(self, throttle_class, **rates):
        configured_rates = dict(throttle_class.THROTTLE_RATES)
        configured_rates.update(rates)
        return patch.object(throttle_class, 'THROTTLE_RATES', configured_rates)

    def test_default_throttle_rates_are_loaded_by_drf(self):
        self.assertEqual(
            SharedDatabaseScopedRateThrottle.THROTTLE_RATES['auth_login'],
            '10/minute',
        )
        self.assertEqual(
            SharedDatabaseScopedRateThrottle.THROTTLE_RATES['auth_register'],
            '20/hour',
        )
        self.assertEqual(
            SharedDatabaseScopedRateThrottle.THROTTLE_RATES['auth_admin_register'],
            '5/hour',
        )
        self.assertEqual(
            SharedDatabaseScopedRateThrottle.THROTTLE_RATES['password_reset_request'],
            '5/hour',
        )
        self.assertEqual(
            SharedDatabaseScopedRateThrottle.THROTTLE_RATES['password_reset_confirm'],
            '10/hour',
        )
        self.assertEqual(
            SharedDatabaseScopedRateThrottle.THROTTLE_RATES['staff_management'],
            '30/minute',
        )
        self.assertEqual(
            SharedDatabaseScopedRateThrottle.THROTTLE_RATES['auth_token_refresh'],
            '60/minute',
        )

    def test_staff_management_uses_shared_database_throttle(self):
        self.assertEqual(
            StaffManagementViewSet.throttle_classes,
            [SharedDatabaseScopedRateThrottle],
        )

    def test_authentication_and_recovery_routes_enforce_scoped_limits(self):
        endpoints = [
            (
                'auth_login',
                reverse('auth_login'),
                {'username': 'unknown-user', 'password': 'WrongPassword123!'},
            ),
            ('auth_register', reverse('auth_register'), {}),
            (
                'password_reset_request',
                reverse('password_reset_request'),
                {'email': 'unregistered@example.com'},
            ),
            ('password_reset_confirm', reverse('password_reset_confirm'), {}),
            ('auth_token_refresh', reverse('auth_token_refresh'), {}),
        ]

        for scope, url, payload in endpoints:
            with self.subTest(scope=scope):
                APIRateLimitWindow.objects.all().delete()
                with self._rates_patch(SharedDatabaseScopedRateThrottle, **{scope: '1/minute'}):
                    first_response = self.client.post(url, payload, format='json')
                    self.assertNotEqual(
                        first_response.status_code,
                        status.HTTP_429_TOO_MANY_REQUESTS,
                    )

                    second_response = self.client.post(url, payload, format='json')
                    self.assertEqual(
                        second_response.status_code,
                        status.HTTP_429_TOO_MANY_REQUESTS,
                    )

    def test_login_and_password_reset_have_independent_budgets(self):
        APIRateLimitWindow.objects.all().delete()
        with self._rates_patch(
            SharedDatabaseScopedRateThrottle,
            auth_login='1/minute',
            password_reset_request='1/minute',
        ):
            login_url = reverse('auth_login')
            reset_url = reverse('password_reset_request')

            login_payload = {
                'username': 'unknown-user',
                'password': 'WrongPassword123!',
            }
            reset_payload = {'email': 'unregistered@example.com'}
            login_first = self.client.post(login_url, login_payload, format='json')
            reset_first = self.client.post(reset_url, reset_payload, format='json')
            self.assertNotEqual(
                login_first.status_code,
                status.HTTP_429_TOO_MANY_REQUESTS,
            )
            self.assertNotEqual(
                reset_first.status_code,
                status.HTTP_429_TOO_MANY_REQUESTS,
            )

            login_second = self.client.post(login_url, login_payload, format='json')
            reset_second = self.client.post(reset_url, reset_payload, format='json')
            self.assertEqual(
                login_second.status_code,
                status.HTTP_429_TOO_MANY_REQUESTS,
            )
            self.assertEqual(
                reset_second.status_code,
                status.HTTP_429_TOO_MANY_REQUESTS,
            )

    def test_client_ip_uses_first_forwarded_address_and_key_is_hashed(self):
        request = APIRequestFactory().get(
            '/',
            HTTP_X_FORWARDED_FOR='203.0.113.42, 10.0.0.8',
            REMOTE_ADDR='10.0.0.8',
        )
        throttle = SharedDatabaseScopedRateThrottle()
        throttle.scope = 'test_scope'

        key = throttle.get_cache_key(request, None)

        self.assertEqual(throttle.get_ident(request), '203.0.113.42')
        self.assertEqual(len(key), 64)
        self.assertNotIn('203.0.113.42', key)

        request.META['HTTP_X_FORWARDED_FOR'] = 'not-an-ip, 10.0.0.8'
        self.assertEqual(throttle.get_ident(request), '10.0.0.8')

    def test_forwarded_header_proxy_trust_settings(self):
        request = APIRequestFactory().get(
            '/',
            HTTP_X_FORWARDED_FOR='1.2.3.4, 203.0.113.42',
            REMOTE_ADDR='10.0.0.8',
        )
        throttle = SharedDatabaseScopedRateThrottle()

        with override_settings(TRUST_X_FORWARDED_FOR=False):
            self.assertEqual(throttle.get_ident(request), '10.0.0.8')

        with override_settings(TRUST_X_FORWARDED_FOR=True, TRUSTED_PROXY_COUNT=1):
            self.assertEqual(throttle.get_ident(request), '203.0.113.42')

        with override_settings(TRUST_X_FORWARDED_FOR=True, TRUSTED_PROXY_COUNT=2):
            multi_hop = APIRequestFactory().get(
                '/',
                HTTP_X_FORWARDED_FOR='1.2.3.4, 198.51.100.7, 10.0.0.9',
                REMOTE_ADDR='127.0.0.1',
            )
            self.assertEqual(throttle.get_ident(multi_hop), '198.51.100.7')

    def test_separate_throttle_instances_share_a_scope_window(self):
        request = APIRequestFactory().get('/', REMOTE_ADDR='192.0.2.10')
        view = type('ScopedView', (), {'throttle_scope': 'shared_test'})()
        with self._rates_patch(SharedDatabaseScopedRateThrottle, shared_test='1/minute'):
            self.assertTrue(SharedDatabaseScopedRateThrottle().allow_request(request, view))
            second_throttle = SharedDatabaseScopedRateThrottle()
            self.assertFalse(second_throttle.allow_request(request, view))
            self.assertGreater(second_throttle.wait(), 0)


@skipUnlessDBFeature('has_select_for_update')
class SharedThrottleConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def test_concurrent_requests_to_one_key_consume_one_available_slot(self):
        barrier = Barrier(2)
        view = type('ScopedView', (), {'throttle_scope': 'concurrent_test'})()

        def make_request():
            try:
                request = APIRequestFactory().get('/', REMOTE_ADDR='192.0.2.20')
                barrier.wait(timeout=10)
                return SharedDatabaseScopedRateThrottle().allow_request(request, view)
            finally:
                connections.close_all()

        with patch.object(
            SharedDatabaseScopedRateThrottle,
            'THROTTLE_RATES',
            {'concurrent_test': '1/minute'},
        ):
            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(lambda _: make_request(), range(2)))

        self.assertEqual(results.count(True), 1)
        self.assertEqual(results.count(False), 1)
        self.assertEqual(APIRateLimitWindow.objects.count(), 1)
