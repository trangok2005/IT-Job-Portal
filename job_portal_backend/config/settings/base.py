import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent.parent

def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


def require_env(*names: str) -> None:
    missing = [name for name in names if not os.getenv(name, "").strip()]
    if missing:
        raise ImproperlyConfigured(
            f"Missing required environment variables: {', '.join(sorted(missing))}"
        )


SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-dev-only-change-me")
DEBUG = False
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "apps.core",
    "apps.accounts",
    "apps.companies",
    "apps.candidates",
    "apps.skills",
    "apps.jobs",
    "apps.applications",
    "apps.notifications",
    "apps.dashboard",
    "apps.ai_analysis",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

if os.getenv("DATABASE_URL"):
    DATABASES = {
        "default": dj_database_url.parse(os.environ["DATABASE_URL"], conn_max_age=60)
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "job_portal"),
            "USER": os.getenv("DB_USER", "job_portal"),
            "PASSWORD": os.getenv("DB_PASSWORD", "job_portal"),
            "HOST": os.getenv("DB_HOST", "localhost"),
            "PORT": os.getenv("DB_PORT", "5432"),
            "CONN_MAX_AGE": 60,
        }
    }

AUTH_USER_MODEL = "accounts.User"

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "apps.accounts.authentication.ActiveUserJWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "common.pagination.DefaultPagination",
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "EXCEPTION_HANDLER": "common.exceptions.api_exception_handler",
}


# qua get_throttles() của từng View. Class nằm ở common/throttling.py.
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {
    # UC-03 E3: tìm kiếm việc làm
    "job_search_anon": "5/min",
    "job_search_user": "10/min",
    # UC-01/UC-02: upload file cho Gemini parse (mỗi user)
    "upload_parse_minute": "2/min",
    "upload_parse_daily": "10/day",
}

# Cache mặc định dùng bộ nhớ cục bộ của process. Production ghi đè rõ ràng cấu hình này.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

SPECTACULAR_SETTINGS = {
    "TITLE": "IT Job Portal API",
    "DESCRIPTION": "API contract for the IT Job Portal frontend.",
    "VERSION": "1.0.0",
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": r"/api",
    "ENUM_NAME_OVERRIDES": {
        "ApplicationStatusEnum": [
            "APPLIED", "SHORTLISTED", "INTERVIEWED", "REJECTED", "HIRED",
        ],
        "JobStatusEnum": ["DRAFT", "ACTIVE", "CLOSED", "EXPIRED"],
        "UserRoleEnum": ["CANDIDATE", "EMPLOYER", "ADMIN"],
    },
}

from datetime import timedelta

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.getenv("JWT_ACCESS_MINUTES", "60"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.getenv("JWT_REFRESH_DAYS", "7"))),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")

EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = os.getenv("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
EMAIL_USE_SSL = env_bool("EMAIL_USE_SSL", False)
EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT", "10"))
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "IT Job Portal <no-reply@example.com>")

# CORS được cấu hình theo từng môi trường.
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
MAX_RESUME_SIZE_BYTES = int(os.getenv("MAX_RESUME_SIZE_BYTES", str(5 * 1024 * 1024)))
MAX_JD_SIZE_BYTES = int(os.getenv("MAX_JD_SIZE_BYTES", str(5 * 1024 * 1024)))
PRIVATE_FILE_URL_TTL_SECONDS = int(os.getenv("R2_SIGNED_URL_TTL_SECONDS", "300"))

R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID", "")
R2_STORAGE_OPTIONS = {
    "access_key": os.getenv("R2_ACCESS_KEY_ID", ""),
    "secret_key": os.getenv("R2_SECRET_ACCESS_KEY", ""),
    "bucket_name": os.getenv("R2_BUCKET_NAME", ""),
    "endpoint_url": os.getenv(
        "R2_ENDPOINT_URL",
        f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com" if R2_ACCOUNT_ID else "",
    ),
    "region_name": "auto",
    "signature_version": "s3v4",
    "addressing_style": "path",
    "default_acl": None,
    "querystring_auth": True,
    "querystring_expire": PRIVATE_FILE_URL_TTL_SECONDS,
    "file_overwrite": False,
}

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_PARSER_MODEL = os.getenv("GEMINI_PARSER_MODEL", "gemini-3.6-flash")
GEMINI_EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
GEMINI_TIMEOUT_MS = int(os.getenv("GEMINI_TIMEOUT_MS", "10000"))
TASK_PROCESSING_LEASE_SECONDS = int(os.getenv("TASK_PROCESSING_LEASE_SECONDS", "60"))

BACKEND_PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "").rstrip("/")
QSTASH_DEV = env_bool("QSTASH_DEV")
QSTASH_URL = os.getenv("QSTASH_URL", "http://127.0.0.1:8080").rstrip("/")
QSTASH_TOKEN = os.getenv("QSTASH_TOKEN", "")
QSTASH_CURRENT_SIGNING_KEY = os.getenv("QSTASH_CURRENT_SIGNING_KEY", "")
QSTASH_NEXT_SIGNING_KEY = os.getenv("QSTASH_NEXT_SIGNING_KEY", "")

LANGUAGE_CODE = "vi"
TIME_ZONE = os.getenv("TIME_ZONE", "Asia/Ho_Chi_Minh")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
