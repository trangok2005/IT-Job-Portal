import os
from pathlib import Path

from dotenv import load_dotenv

_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(_BACKEND_DIR / ".env.local")

os.environ.setdefault("QSTASH_DEV", "true")
os.environ.setdefault("BACKEND_PUBLIC_URL", "http://127.0.0.1:8000")

from .base import *  # noqa: E402,F401,F403

DEBUG = True
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1,backend")
CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
)
CSRF_TRUSTED_ORIGINS = env_list(
    "CSRF_TRUSTED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
)

# Local development must not consume the production Redis quota.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": R2_STORAGE_OPTIONS,
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

require_env("R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET_NAME")
if not (os.getenv("R2_ENDPOINT_URL") or os.getenv("R2_ACCOUNT_ID")):
    raise ImproperlyConfigured("R2_ENDPOINT_URL or R2_ACCOUNT_ID is required for local R2.")
