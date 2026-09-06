import os
import subprocess
import sys

from django.conf import settings
from django.test import SimpleTestCase


PRODUCTION_ENV = {
    "SECRET_KEY": "Prod-Test!Key-2026-With-Enough-Length-And-Character-Variety-93x",
    "ALLOWED_HOSTS": "api.example.com",
    "CORS_ALLOWED_ORIGINS": "https://www.example.com",
    "CSRF_TRUSTED_ORIGINS": "https://www.example.com,https://api.example.com",
    "BACKEND_PUBLIC_URL": "https://api.example.com",
    "DATABASE_URL": "postgresql://user:password@database.internal/job_portal",
    "REDIS_URL": "rediss://default:password@redis.example.com:6379",
    "QSTASH_DEV": "false",
    "QSTASH_TOKEN": "qstash-token",
    "QSTASH_CURRENT_SIGNING_KEY": "sig_current",
    "QSTASH_NEXT_SIGNING_KEY": "sig_next",
    "R2_ENDPOINT_URL": "https://account.r2.cloudflarestorage.com",
    "R2_ACCESS_KEY_ID": "r2-access-key",
    "R2_SECRET_ACCESS_KEY": "r2-secret-key",
    "R2_BUCKET_NAME": "production-bucket",
    "GEMINI_API_KEY": "gemini-key",
    "GEMINI_PARSER_MODEL": "parser-model",
    "GEMINI_EMBEDDING_MODEL": "embedding-model",
    "GOOGLE_CLIENT_ID": "client.apps.googleusercontent.com",
    "EMAIL_HOST": "smtp.example.com",
    "EMAIL_PORT": "587",
    "EMAIL_HOST_USER": "smtp-user",
    "EMAIL_HOST_PASSWORD": "smtp-password",
    "DEFAULT_FROM_EMAIL": "no-reply@example.com",
}


class ProductionSettingsTests(SimpleTestCase):
    def run_import(self, overrides=None):
        environment = os.environ.copy()
        environment.update(PRODUCTION_ENV)
        environment.update(overrides or {})
        return subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "from config.settings import production as s; "
                    "print(s.DEBUG, s.CACHES['default']['LOCATION'])"
                ),
            ],
            cwd=settings.BASE_DIR,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_valid_environment_loads_production_settings(self):
        result = self.run_import()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("False rediss://", result.stdout)

    def test_missing_required_variable_fails_fast(self):
        result = self.run_import({"SECRET_KEY": ""})

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SECRET_KEY", result.stderr)

    def test_non_tls_redis_url_is_rejected(self):
        result = self.run_import({"REDIS_URL": "redis://redis.example.com:6379"})

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("rediss://", result.stderr)

    def test_weak_secret_key_is_rejected(self):
        result = self.run_import({"SECRET_KEY": "too-short"})

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not strong enough", result.stderr)
