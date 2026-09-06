from .base import *  # noqa: F401,F403

DEBUG = False
SECRET_KEY = "test-only-secret-key-at-least-32-bytes-long"
GEMINI_API_KEY = ""
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
# Test không được phụ thuộc Redis thật (throttle history dùng locmem riêng).
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}
