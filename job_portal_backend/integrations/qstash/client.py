"""Các QStash SDK client được khởi tạo lazy từ Django settings."""
from functools import lru_cache

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class QStashConfigurationError(ImproperlyConfigured):
    """QStash chưa được cấu hình cho thao tác được yêu cầu."""


# Thông tin xác thực được công bố cho người dùng mặc định của QStash CLI server cục bộ.
_DEV_TOKEN = "eyJVc2VySUQiOiJkZWZhdWx0VXNlciIsIlBhc3N3b3JkIjoiZGVmYXVsdFBhc3N3b3JkIn0="
_DEV_CURRENT_SIGNING_KEY = "sig_7kYjw48mhY7kAjqNGcy6cr29RJ6r"
_DEV_NEXT_SIGNING_KEY = "sig_5ZB6DVzB1wjE8S6rZ7eenA8Pdnhs"


def _configured_value(name: str, development_default: str = "") -> str:
    value = str(getattr(settings, name, "") or "").strip()
    if value:
        return value
    if settings.QSTASH_DEV:
        return development_default
    raise QStashConfigurationError(f"{name} chưa được cấu hình.")


@lru_cache(maxsize=1)
def get_qstash_client():
    """Trả về một publishing client cho mỗi Django process."""
    from qstash import QStash

    token = _configured_value("QSTASH_TOKEN", _DEV_TOKEN)
    return QStash(
        token,
        base_url=settings.QSTASH_URL if settings.QSTASH_DEV else None,
    )


@lru_cache(maxsize=1)
def get_qstash_receiver():
    """Trả về một receiver xác minh signature và hỗ trợ signing-key rotation."""
    from qstash import Receiver

    current_key = _configured_value(
        "QSTASH_CURRENT_SIGNING_KEY", _DEV_CURRENT_SIGNING_KEY
    )
    next_key = _configured_value("QSTASH_NEXT_SIGNING_KEY", _DEV_NEXT_SIGNING_KEY)
    return Receiver(
        current_signing_key=current_key,
        next_signing_key=next_key,
    )
