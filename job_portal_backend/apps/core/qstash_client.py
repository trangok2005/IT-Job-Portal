"""Shared QStash client and task publisher."""
import os

from qstash import QStash, Receiver


def _env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).lower() in {"1", "true", "yes", "on"}


QSTASH_DEV = _env_bool("QSTASH_DEV")
BACKEND_PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "").rstrip("/")
QSTASH_URL = os.getenv("QSTASH_URL", "http://127.0.0.1:8080").rstrip("/")

# The Python SDK has no devMode constructor option. These are the documented
# QStash CLI default-user credentials, selected for both publishing and verify.
_DEV_TOKEN = "eyJVc2VySUQiOiJkZWZhdWx0VXNlciIsIlBhc3N3b3JkIjoiZGVmYXVsdFBhc3N3b3JkIn0="
_DEV_CURRENT_SIGNING_KEY = "sig_7kYjw48mhY7kAjqNGcy6cr29RJ6r"
_DEV_NEXT_SIGNING_KEY = "sig_5ZB6DVzB1wjE8S6rZ7eenA8Pdnhs"

QSTASH_TOKEN = os.getenv("QSTASH_TOKEN") or (_DEV_TOKEN if QSTASH_DEV else "")
QSTASH_CURRENT_SIGNING_KEY = os.getenv("QSTASH_CURRENT_SIGNING_KEY") or (
    _DEV_CURRENT_SIGNING_KEY if QSTASH_DEV else ""
)
QSTASH_NEXT_SIGNING_KEY = os.getenv("QSTASH_NEXT_SIGNING_KEY") or (
    _DEV_NEXT_SIGNING_KEY if QSTASH_DEV else ""
)

client = QStash(
    QSTASH_TOKEN,
    base_url=QSTASH_URL if QSTASH_DEV else None,
)
receiver = Receiver(
    current_signing_key=QSTASH_CURRENT_SIGNING_KEY,
    next_signing_key=QSTASH_NEXT_SIGNING_KEY,
)


def dispatcher_url() -> str:
    if not BACKEND_PUBLIC_URL:
        raise RuntimeError("BACKEND_PUBLIC_URL chưa được cấu hình.")
    return f"{BACKEND_PUBLIC_URL}/api/internal/tasks/"


def publish_task(
    task_name: str,
    payload: dict,
    delay: int | None = None,
    retries: int | None = 5,
    deduplication_id: str | None = None,
):
    """Publish one registered task to the shared dispatcher endpoint."""
    options = {
        "url": dispatcher_url(),
        "body": {"task": task_name, "payload": payload},
        "delay": delay,
    }
    if retries is not None:
        options["retries"] = retries
    if deduplication_id is not None:
        options["deduplication_id"] = deduplication_id
    return client.message.publish_json(
        **options,
    )
