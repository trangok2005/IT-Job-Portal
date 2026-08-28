# Base settings shared across all environments.
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-dev-only-change-me")
DEBUG = env_bool("DEBUG", True)
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "*")

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
    "django_q",
    "apps.core",
    "apps.accounts",
    "apps.companies",
    "apps.candidates",
    "apps.skills",
    "apps.jobs",
    "apps.applications",
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

# ---------------------------------------------------------------------------
# Database (PostgreSQL + pgvector). Override via environment / .env
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# DRF + JWT
# ---------------------------------------------------------------------------
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

# Lưu ý: KHÔNG đặt DEFAULT_THROTTLE_CLASSES — throttle chỉ áp dụng có chủ đích
# qua get_throttles() của từng View. Class nằm ở common/throttling.py.
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {
    # UC-03 E3: tìm kiếm việc làm
    "job_search_anon": "5/min",
    "job_search_user": "10/min",
    # UC-01/UC-02: upload file cho Gemini parse (mỗi user)
    "upload_parse_minute": "2/min",
    "upload_parse_daily": "10/day",
}

# ---------------------------------------------------------------------------
# Cache — lịch sử throttle (UC-03 E3) dùng Redis thật khi có REDIS_URL,
# fallback LocMemCache cho máy dev không có Redis.
# ---------------------------------------------------------------------------
if os.getenv("REDIS_URL"):
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": os.getenv("REDIS_URL"),
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "CONNECTION_POOL_KEEPALIVE": True,
                "SSL_CERT_REQS": None,
            },
        }
    }
    # Redis chập chờn không được làm sập search; throttle tạm mất tác dụng.
    DJANGO_REDIS_IGNORE_EXCEPTIONS = True
else:
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

# ---------------------------------------------------------------------------
# CORS — local dev allows the Next.js dev server.
# ---------------------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = env_bool("CORS_ALLOW_ALL_ORIGINS", True)
CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000",
)

# ---------------------------------------------------------------------------
# Media / files (resumes, JD uploads)
# ---------------------------------------------------------------------------
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
MAX_RESUME_SIZE_BYTES = int(os.getenv("MAX_RESUME_SIZE_BYTES", str(5 * 1024 * 1024)))
MAX_JD_SIZE_BYTES = int(os.getenv("MAX_JD_SIZE_BYTES", str(5 * 1024 * 1024)))

# ---------------------------------------------------------------------------
# Django-Q (background worker: embeddings and import cleanup)
# ---------------------------------------------------------------------------
Q_CLUSTER = {
    "name": "job_portal",
    "workers": 1,
    "recycle": 100,
    "timeout": 300,
    "retry": 360,
    "compress": True,
    "save_limit": 100,
    "queue_limit": 100,
    "label": "Django Q",
    "orm": "default",
}

# ---------------------------------------------------------------------------
# Gemini AI
# ---------------------------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_PARSER_MODEL = os.getenv("GEMINI_PARSER_MODEL", "gemini-3.6-flash")
EMBEDDING_TIMEOUT_MS = int(os.getenv("EMBEDDING_TIMEOUT_MS", "10000"))

# ---------------------------------------------------------------------------
# i18n / timezone
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "vi"
TIME_ZONE = os.getenv("TIME_ZONE", "Asia/Ho_Chi_Minh")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
