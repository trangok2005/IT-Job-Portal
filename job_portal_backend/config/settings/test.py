from .base import *

DEBUG = False
SECRET_KEY = "test-only-secret-key-at-least-32-bytes-long"
GEMINI_API_KEY = ""
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}
