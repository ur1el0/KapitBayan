from django.test import RequestFactory, SimpleTestCase, override_settings

from gridy_audit.services import get_client_ip


class GetClientIPTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_uses_first_valid_forwarded_address(self):
        request = self.factory.get(
            "/",
            REMOTE_ADDR="10.0.0.8",
            HTTP_X_FORWARDED_FOR="203.0.113.14, 10.0.0.8",
        )

        self.assertEqual(get_client_ip(request), "203.0.113.14")

    def test_invalid_forwarded_value_falls_back_to_direct_address(self):
        request = self.factory.get(
            "/",
            REMOTE_ADDR="198.51.100.9",
            HTTP_X_FORWARDED_FOR="not-an-ip",
        )

        self.assertEqual(get_client_ip(request), "198.51.100.9")

    def test_invalid_or_missing_addresses_return_none(self):
        request = self.factory.get("/", REMOTE_ADDR="testserver")

        self.assertIsNone(get_client_ip(request))

    def test_ignores_spoofed_leftmost_forwarded_ip_when_proxy_trust_restricted(self):
        request = self.factory.get(
            "/",
            REMOTE_ADDR="192.0.2.50",
            HTTP_X_FORWARDED_FOR="198.51.100.1, 203.0.113.77",
        )

        with override_settings(TRUST_X_FORWARDED_FOR=False):
            self.assertEqual(get_client_ip(request), "192.0.2.50")

        with override_settings(TRUST_X_FORWARDED_FOR=True, TRUSTED_PROXY_COUNT=1):
            self.assertEqual(get_client_ip(request), "203.0.113.77")
