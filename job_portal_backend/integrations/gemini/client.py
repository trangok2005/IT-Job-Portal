"""Client lazy dùng chung cho các tích hợp Gemini."""
from functools import lru_cache

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class GeminiConfigurationError(ImproperlyConfigured):
    """Gemini chưa được cấu hình cho thao tác được yêu cầu."""


class GeminiRequestError(Exception):
    """Request Gemini thất bại trước khi trả về response có thể sử dụng."""


@lru_cache(maxsize=1)
def get_gemini_client():
    """Trả về một Gemini client được khởi tạo lazy cho mỗi process."""
    if not settings.GEMINI_API_KEY:
        raise GeminiConfigurationError("GEMINI_API_KEY chưa được cấu hình.")

    from google import genai
    from google.genai import types

    return genai.Client(
        api_key=settings.GEMINI_API_KEY,
        http_options=types.HttpOptions(timeout=settings.GEMINI_TIMEOUT_MS),
    )
