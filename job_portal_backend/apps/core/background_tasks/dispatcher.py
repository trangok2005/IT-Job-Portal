"""Tra cứu và thực thi background task đã đăng ký, độc lập với provider."""
import inspect
from typing import Any

from apps.core.background_tasks.registry import TASK_REGISTRY


class UnknownTaskError(ValueError):
    """Task được yêu cầu không có trong allow-list."""


class InvalidTaskPayloadError(ValueError):
    """Payload không thể áp dụng cho task đã đăng ký."""


def dispatch_task(task_name: str, payload: dict) -> Any:
    """Kiểm tra task envelope và thực thi callable đã đăng ký."""
    task = TASK_REGISTRY.get(task_name) if isinstance(task_name, str) else None
    if task is None:
        raise UnknownTaskError("Unknown task.")
    if not isinstance(payload, dict):
        raise InvalidTaskPayloadError("Task payload must be an object.")
    try:
        inspect.signature(task).bind(**payload)
    except TypeError as exc:
        raise InvalidTaskPayloadError("Task payload does not match its parameters.") from exc
    return task(**payload)
