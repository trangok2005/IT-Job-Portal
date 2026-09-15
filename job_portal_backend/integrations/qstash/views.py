import json
import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from qstash.errors import SignatureError

from apps.core.background_tasks.dispatcher import (
    InvalidTaskPayloadError,
    UnknownTaskError,
    dispatch_task,
)
from integrations.qstash.client import get_qstash_receiver
from integrations.qstash.publisher import dispatcher_url


logger = logging.getLogger(__name__)
QSTASH_DO_NOT_RETRY_STATUS = 489


@csrf_exempt
@require_POST
def task_dispatcher(request):
    """Xác minh callback; lỗi tạm thời trả 5xx để QStash retry."""
    raw_body = request.body
    signature = request.headers.get("Upstash-Signature", "")
    try:
        body_text = raw_body.decode("utf-8")
        get_qstash_receiver().verify(
            signature=signature,
            body=body_text,
            url=dispatcher_url(),
        )
    except (SignatureError, UnicodeDecodeError):
        logger.warning("Rejected QStash task request with an invalid signature")
        return JsonResponse({"error": "Invalid QStash signature."}, status=401)

    try:
        message = json.loads(body_text)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse(
            {"error": "Invalid JSON body."}, status=QSTASH_DO_NOT_RETRY_STATUS
        )

    task_name = message.get("task") if isinstance(message, dict) else None
    payload = message.get("payload") if isinstance(message, dict) else None
    try:
        dispatch_task(task_name, payload)
    except UnknownTaskError as exc:
        return JsonResponse({"error": str(exc)}, status=QSTASH_DO_NOT_RETRY_STATUS)
    except InvalidTaskPayloadError as exc:
        return JsonResponse({"error": str(exc)}, status=QSTASH_DO_NOT_RETRY_STATUS)
    except Exception:
        logger.exception("QStash task %s failed", task_name)
        return JsonResponse({"error": "Task execution failed."}, status=500)
    return JsonResponse({"success": True})
