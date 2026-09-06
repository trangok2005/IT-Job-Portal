"""Điều phối thông báo độc lập với thay đổi trạng thái hồ sơ ứng tuyển."""
from django.db import transaction

from apps.applications.models import ApplicationStatusHistory
from apps.core.qstash_client import publish_task


def enqueue_application_status_email(history: ApplicationStatusHistory) -> None:
    """Đưa tác vụ delivery vào hàng đợi sau commit mà không ảnh hưởng trạng thái đã lưu."""

    def enqueue():
        try:
            publish_task(
                "send_application_status_email",
                {"history_id": str(history.pk)},
                retries=3,
                deduplication_id=f"application-status-{history.pk}",
            )
        except Exception as exc:
            ApplicationStatusHistory.objects.filter(pk=history.pk).update(
                notification_status=ApplicationStatusHistory.NotificationStatus.FAILED,
                notification_error=f"Không thể đưa email vào hàng đợi: {exc}"[:2000],
            )

    transaction.on_commit(enqueue)
