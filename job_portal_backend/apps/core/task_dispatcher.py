"""Authenticated dispatcher endpoint for all QStash tasks."""
import json
import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from qstash.errors import SignatureError

from apps.core.qstash_client import receiver
from apps.core.task_registry import TASK_REGISTRY


logger = logging.getLogger(__name__)
QSTASH_DO_NOT_RETRY_STATUS = 489


@csrf_exempt
@require_POST
def task_dispatcher(request):
    raw_body = request.body
    signature = request.headers.get("Upstash-Signature", "")
    try:
        receiver.verify(signature=signature, body=raw_body.decode("utf-8"))
    except (SignatureError, UnicodeDecodeError):
        logger.warning("Rejected QStash task request with an invalid signature")
        return JsonResponse({"error": "Invalid QStash signature."}, status=401)

    try:
        message = json.loads(raw_body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse(
            {"error": "Invalid JSON body."}, status=QSTASH_DO_NOT_RETRY_STATUS
        )

    task_name = message.get("task") if isinstance(message, dict) else None
    payload = message.get("payload") if isinstance(message, dict) else None
    task = TASK_REGISTRY.get(task_name)
    if task is None:
        return JsonResponse({"error": "Unknown task."}, status=QSTASH_DO_NOT_RETRY_STATUS)
    if not isinstance(payload, dict):
        return JsonResponse(
            {"error": "Task payload must be an object."},
            status=QSTASH_DO_NOT_RETRY_STATUS,
        )

    try:
        task(**payload)
    except Exception:
        logger.exception("QStash task %s failed", task_name)
        return JsonResponse({"error": "Task execution failed."}, status=500)

    return JsonResponse({"success": True})
