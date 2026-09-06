"""Private Cloudflare R2 URL generation with a local-storage fallback."""
from datetime import timedelta

from django.conf import settings
from django.utils import timezone


def create_private_file_url(file_field) -> dict:
    """Return a short-lived R2 URL, or a normal URL for local storage."""
    ttl_seconds = settings.PRIVATE_FILE_URL_TTL_SECONDS
    storage = file_field.storage
    options = {"expire": ttl_seconds} if getattr(storage, "querystring_auth", False) else {}
    return {
        "url": storage.url(file_field.name, **options),
        "expires_at": timezone.now() + timedelta(seconds=ttl_seconds),
    }
