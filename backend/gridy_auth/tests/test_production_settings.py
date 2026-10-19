import os
import subprocess
import sys
import tempfile
from pathlib import Path
from django.test import SimpleTestCase


class ProductionSettingsValidationTests(SimpleTestCase):
    def setUp(self):
        self.backend_dir = Path(__file__).resolve().parents[2]
        self.script = (
            "import os, sys\n"
            "sys.argv = ['manage.py', 'check']\n"
            "import config.settings as s\n"
            "print(s.STORAGES['default']['BACKEND'])\n"
        )
        self.temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        self.temp_file.write('{"type": "service_account"}')
        self.temp_file.close()

    def tearDown(self):
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)

    def _run_subprocess(self, env_overrides):
        env = os.environ.copy()
        env["SECRET_KEY"] = "production-test-secret-key-32-chars-long!!"
        env["DEBUG"] = "False"
        env["EMAIL_HOST"] = "smtp.gmail.com"
        env["EMAIL_HOST_USER"] = "alerts@kapitbayan.gov.ph"
        env["EMAIL_HOST_PASSWORD"] = "app-password"
        env["DEFAULT_FROM_EMAIL"] = "alerts@kapitbayan.gov.ph"
        env["FIREBASE_SERVICE_ACCOUNT_JSON_PATH"] = self.temp_file.name
        env["CLOUDINARY_CLOUD_NAME"] = "dummy-cloud"
        env["CLOUDINARY_API_KEY"] = "123456789"
        env["CLOUDINARY_API_SECRET"] = "dummy-secret"
        env["DATABASE_URL"] = "postgres://gridy:pass@localhost:5432/gridy_db"
        env["FRONTEND_URL"] = "https://kapitbayan.gov.ph"

        for key, val in env_overrides.items():
            if val is None:
                env.pop(key, None)
            else:
                env[key] = val

        return subprocess.run(
            [sys.executable, "-c", self.script],
            cwd=str(self.backend_dir),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_production_fails_when_database_url_missing(self):
        result = self._run_subprocess({"DATABASE_URL": None})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DATABASE_URL", result.stderr)

    def test_production_fails_when_database_is_not_postgresql(self):
        result = self._run_subprocess({"DATABASE_URL": "sqlite:///local.db"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("PostgreSQL", result.stderr)

    def test_production_fails_when_frontend_url_is_cleartext_http(self):
        result = self._run_subprocess({"FRONTEND_URL": "http://insecure-site.gov.ph"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("HTTPS FRONTEND_URL", result.stderr)

    def test_production_fails_when_frontend_url_is_missing(self):
        result = self._run_subprocess({"FRONTEND_URL": ""})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("HTTPS FRONTEND_URL", result.stderr)

    def test_normal_production_startup_still_requires_cloudinary(self):
        result = self._run_subprocess({
            "CLOUDINARY_CLOUD_NAME": None,
            "CLOUDINARY_API_KEY": None,
            "CLOUDINARY_API_SECRET": None,
        })
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("CLOUDINARY_CLOUD_NAME", result.stderr)

    def test_production_succeeds_with_valid_postgresql_and_https_frontend_url(self):
        result = self._run_subprocess({
            "DATABASE_URL": "postgres://gridy:pass@localhost:5432/gridy_db",
            "FRONTEND_URL": "https://kapitbayan.gov.ph",
        })
        self.assertEqual(result.returncode, 0, f"Failed with stderr: {result.stderr}")

    def test_migration_only_runtime_uses_filesystem_storage_without_external_media_secrets(self):
        with tempfile.TemporaryDirectory() as runner_temp:
            result = self._run_subprocess({
                "KAPITBAYAN_MIGRATION_ONLY": "true",
                "GITHUB_ACTIONS": "true",
                "RUNNER_TEMP": runner_temp,
                "CLOUDINARY_CLOUD_NAME": None,
                "CLOUDINARY_API_KEY": None,
                "CLOUDINARY_API_SECRET": None,
                "FIREBASE_SERVICE_ACCOUNT_JSON_PATH": None,
                "EMAIL_HOST_USER": None,
                "EMAIL_HOST_PASSWORD": None,
                "DEFAULT_FROM_EMAIL": None,
            })

        self.assertEqual(result.returncode, 0, f"Failed with stderr: {result.stderr}")
        self.assertIn("django.core.files.storage.FileSystemStorage", result.stdout)

    def test_migration_only_runtime_is_rejected_outside_github_actions(self):
        with tempfile.TemporaryDirectory() as runner_temp:
            result = self._run_subprocess({
                "KAPITBAYAN_MIGRATION_ONLY": "true",
                "GITHUB_ACTIONS": None,
                "RUNNER_TEMP": runner_temp,
            })

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("reserved for non-debug GitHub Actions", result.stderr)
