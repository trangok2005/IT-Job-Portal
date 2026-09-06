import os
import ssl
from urllib.parse import urlparse

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: E402,F401,F403

DEBUG = False
SECRET_KEY = os.environ.get("SECRET_KEY", "")
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS")
RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")

require_env(
    "SECRET_KEY",
    "ALLOWED_HOSTS",
    "CORS_ALLOWED_ORIGINS",
    "CSRF_TRUSTED_ORIGINS",
    "REDIS_URL",
    "BACKEND_PUBLIC_URL",
    "QSTASH_TOKEN",
    "QSTASH_CURRENT_SIGNING_KEY",
    "QSTASH_NEXT_SIGNING_KEY",
    "R2_ACCESS_KEY_ID",
    "R2_SECRET_ACCESS_KEY",
    "R2_BUCKET_NAME",
    "GEMINI_API_KEY",
    "GEMINI_PARSER_MODEL",
    "GEMINI_EMBEDDING_MODEL",
    "GOOGLE_CLIENT_ID",
    "EMAIL_HOST",
    "EMAIL_PORT",
    "EMAIL_HOST_USER",
    "EMAIL_HOST_PASSWORD",
    "DEFAULT_FROM_EMAIL",
)
if not os.getenv("DATABASE_URL"):
    require_env("DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT")
if not (os.getenv("R2_ENDPOINT_URL") or os.getenv("R2_ACCOUNT_ID")):
    raise ImproperlyConfigured("R2_ENDPOINT_URL or R2_ACCOUNT_ID is required.")
if env_bool("QSTASH_DEV"):
    raise ImproperlyConfigured("QSTASH_DEV must be false in production.")
if (
    len(SECRET_KEY) < 50
    or len(set(SECRET_KEY)) < 5
    or SECRET_KEY.startswith("django-insecure-")
):
    raise ImproperlyConfigured("SECRET_KEY is not strong enough for production.")
if not os.environ["REDIS_URL"].startswith("rediss://"):
    raise ImproperlyConfigured("REDIS_URL must use rediss:// in production.")
if "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured("ALLOWED_HOSTS cannot contain '*' in production.")
if any("/" in host or "://" in host for host in ALLOWED_HOSTS):
    raise ImproperlyConfigured("ALLOWED_HOSTS entries must be hostnames, not URLs.")
if urlparse(os.environ["BACKEND_PUBLIC_URL"]).scheme != "https":
    raise ImproperlyConfigured("BACKEND_PUBLIC_URL must use https:// in production.")
if any(urlparse(origin).scheme != "https" for origin in CORS_ALLOWED_ORIGINS):
    raise ImproperlyConfigured("CORS_ALLOWED_ORIGINS must use https:// in production.")
if any(urlparse(origin).scheme != "https" for origin in CSRF_TRUSTED_ORIGINS):
    raise ImproperlyConfigured("CSRF_TRUSTED_ORIGINS must use https:// in production.")
if EMAIL_USE_TLS and EMAIL_USE_SSL:
    raise ImproperlyConfigured("EMAIL_USE_TLS and EMAIL_USE_SSL cannot both be enabled.")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.environ["REDIS_URL"],
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KEEPALIVE": True,
            "SSL_CERT_REQS": ssl.CERT_REQUIRED,
        },
    }
}
DJANGO_REDIS_IGNORE_EXCEPTIONS = False

STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": R2_STORAGE_OPTIONS,
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MIDDLEWARE.insert(2, "whitenoise.middleware.WhiteNoiseMiddleware")
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env_bool("ENABLE_HTTPS_REDIRECT")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

if env_bool("ENABLE_HSTS"):
    SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", True)
    SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", True)
else:
    SECURE_HSTS_SECONDS = 0

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
