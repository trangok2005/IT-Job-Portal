from functools import lru_cache

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class QStashConfigurationError(ImproperlyConfigured):
    pass


# Credential công khai của QStash CLI server cục bộ.
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
    from qstash import QStash

    token = _configured_value("QSTASH_TOKEN", _DEV_TOKEN)
    return QStash(
        token,
        base_url=settings.QSTASH_URL if settings.QSTASH_DEV else None,
    )


@lru_cache(maxsize=1)
def get_qstash_receiver():
    from qstash import Receiver

    current_key = _configured_value(
        "QSTASH_CURRENT_SIGNING_KEY", _DEV_CURRENT_SIGNING_KEY
    )
    next_key = _configured_value("QSTASH_NEXT_SIGNING_KEY", _DEV_NEXT_SIGNING_KEY)
    return Receiver(
        current_signing_key=current_key,
        next_signing_key=next_key,
    )
