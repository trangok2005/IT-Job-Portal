from .base import *  # noqa: F401,F403

DEBUG = False
Q_CLUSTER["sync"] = True  # noqa: F405
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
GEMINI_API_KEY = ""
# Test không được phụ thuộc Redis thật (throttle history dùng locmem riêng).
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}
