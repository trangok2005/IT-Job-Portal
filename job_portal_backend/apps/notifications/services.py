from django.db import transaction

from apps.applications.models import ApplicationStatusHistory
from integrations.qstash.publisher import publish_task


def enqueue_application_status_email(history: ApplicationStatusHistory) -> None:

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
