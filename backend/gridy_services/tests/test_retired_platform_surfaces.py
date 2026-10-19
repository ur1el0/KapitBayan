from django.test import SimpleTestCase
from django.urls import Resolver404, resolve


class RetiredPlatformAnalyticsRouteTests(SimpleTestCase):
    def test_global_analytics_endpoint_is_not_routed(self):
        with self.assertRaises(Resolver404):
            resolve("/api/v1/barangay-operator-analytics/")
