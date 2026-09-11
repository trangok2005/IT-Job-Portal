"""Gửi các background-task envelope nhỏ qua QStash."""
from typing import Any

from django.conf import settings

from integrations.qstash.client import QStashConfigurationError, get_qstash_client


def dispatcher_url() -> str:
    """Trả về URL công khai được QStash ký cho task callback."""
    base_url = str(getattr(settings, "BACKEND_PUBLIC_URL", "") or "").rstrip("/")
    if not base_url:
        raise QStashConfigurationError("BACKEND_PUBLIC_URL chưa được cấu hình.")
    return f"{base_url}/api/internal/tasks/"


def publish_task(
    task_name: str,
    payload: dict,
    delay: int | None = None,
    retries: int | None = 5,
    deduplication_id: str | None = None,
) -> Any:
    """Gửi một task đã đăng ký tới callback endpoint dùng chung."""
    options = {
        "url": dispatcher_url(),
        "body": {"task": task_name, "payload": payload},
        "delay": delay,
    }
    if retries is not None:
        options["retries"] = retries
    if deduplication_id is not None:
        options["deduplication_id"] = deduplication_id
    return get_qstash_client().message.publish_json(**options)
