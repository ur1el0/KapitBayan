from unittest.mock import patch

from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class SystemHealthAPITests(APITestCase):
    @patch(
        "config.health_views.cache.get",
        side_effect=AssertionError("cache probe must not run"),
    )
    @patch(
        "config.health_views.cache.set",
        side_effect=AssertionError("cache probe must not run"),
    )
    @patch(
        "config.health_views.connection.cursor",
        side_effect=AssertionError("database probe must not run"),
    )
    def test_liveness_does_not_check_dependencies_or_authenticate(
        self,
        database_cursor,
        cache_set,
        cache_get,
    ):
        response = self.client.get(
            reverse("health_live"),
            HTTP_AUTHORIZATION="Bearer deliberately-invalid-token",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"status": "live"})
        database_cursor.assert_not_called()
        cache_set.assert_not_called()
        cache_get.assert_not_called()

    def test_readiness_and_legacy_health_routes_report_dependency_health(self):
        for route_name in ("health_ready", "health_check"):
            with self.subTest(route=route_name):
                response = self.client.get(reverse(route_name))

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.data["status"], "healthy")
                self.assertIn("timestamp", response.data)
                self.assertIn("database", response.data["services"])
                self.assertIn("cache", response.data["services"])
                self.assertEqual(response.data["services"]["database"]["status"], "healthy")
                self.assertEqual(response.data["services"]["cache"]["status"], "healthy")

    @patch(
        "config.health_views.connection.cursor",
        side_effect=RuntimeError("sensitive database detail"),
    )
    def test_readiness_returns_sanitized_unavailable_response_when_database_fails(
        self,
        database_cursor,
    ):
        response = self.client.get(reverse("health_ready"))

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(response.data["status"], "unhealthy")
        self.assertEqual(
            response.data["services"]["database"]["error"],
            "Database connectivity check failed.",
        )
        self.assertNotIn("sensitive database detail", str(response.data))
        database_cursor.assert_called_once()

    @patch(
        "config.health_views.cache.set",
        side_effect=RuntimeError("sensitive cache detail"),
    )
    def test_readiness_returns_sanitized_unavailable_response_when_cache_fails(
        self,
        cache_set,
    ):
        response = self.client.get(reverse("health_ready"))

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(response.data["status"], "unhealthy")
        self.assertEqual(
            response.data["services"]["cache"]["error"],
            "Cache connectivity check failed.",
        )
        self.assertNotIn("sensitive cache detail", str(response.data))
        cache_set.assert_called_once()

    def test_health_check_endpoint_success(self):
        url = reverse('health_check')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "healthy")
        self.assertIn("database", response.data["services"])
        self.assertIn("cache", response.data["services"])
        self.assertEqual(response.data["services"]["database"]["status"], "healthy")
        self.assertEqual(response.data["services"]["cache"]["status"], "healthy")

    @override_settings(
        CORS_ALLOWED_ORIGINS=["https://app.example.gov.ph"],
        CORS_ALLOW_CREDENTIALS=True,
    )
    def test_preflight_allows_configured_origin_with_credentials(self):
        origin = "https://app.example.gov.ph"
        response = self.client.options(
            reverse("health_check"),
            HTTP_ORIGIN=origin,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Access-Control-Allow-Origin"], origin)
        self.assertEqual(
            response["Access-Control-Allow-Credentials"],
            "true",
        )

    @override_settings(
        CORS_ALLOWED_ORIGINS=["https://app.example.gov.ph"],
        CORS_ALLOW_CREDENTIALS=True,
    )
    def test_preflight_allows_document_idempotency_header(self):
        response = self.client.options(
            reverse("health_check"),
            HTTP_ORIGIN="https://app.example.gov.ph",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization,content-type,idempotency-key",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("idempotency-key", response["Access-Control-Allow-Headers"].lower())

    @override_settings(
        CORS_ALLOWED_ORIGINS=["https://app.example.gov.ph"],
        CORS_ALLOW_CREDENTIALS=True,
    )
    def test_preflight_omits_cors_headers_for_unlisted_origin(self):
        response = self.client.options(
            reverse("health_check"),
            HTTP_ORIGIN="https://unlisted.example.net",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        )

        self.assertNotIn("Access-Control-Allow-Origin", response)
        self.assertNotIn("Access-Control-Allow-Credentials", response)
