from .base import *  # noqa: F401,F403

DEBUG = False
SECRET_KEY = "test-only-secret-key-at-least-32-bytes-long"
Q_CLUSTER["sync"] = True  # noqa: F405
GEMINI_API_KEY = ""
# Test không được phụ thuộc Redis thật (throttle history dùng locmem riêng).
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}
