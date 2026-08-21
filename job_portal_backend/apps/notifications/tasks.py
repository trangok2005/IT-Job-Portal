"""Django-Q task gửi email notification và lập lịch retry."""
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from apps.notifications import services


def schedule_email_retry(notification) -> None:
    """Tạo one-off schedule cho lần gửi kế tiếp nếu chưa vượt giới hạn."""
    if notification.retry_count >= settings.NOTIFICATION_MAX_RETRIES:
        return
    from django_q.models import Schedule
    from django_q.tasks import schedule

    schedule(
        "apps.notifications.tasks.send_notification_email",
        str(notification.pk),
        name=f"retry-notification-{notification.pk}-{notification.retry_count}",
        schedule_type=Schedule.ONCE,
        repeats=1,
        next_run=timezone.now()
        + timedelta(minutes=settings.NOTIFICATION_RETRY_MINUTES),
    )


def send_notification_email(notification_id: str) -> bool:
    """Gửi email, lưu SENT/FAILED và retry mà không rollback application."""
    notification = services.claim_email_notification(notification_id)
    if notification is None:
        return False
    if not notification.recipient.email:
        services.mark_email_failed(notification.pk, "Người nhận không có email.")
        return False

    try:
        sent_count = send_mail(
            subject=notification.title,
            message=notification.message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[notification.recipient.email],
            fail_silently=False,
        )
        if sent_count != 1:
            raise RuntimeError("Email backend không xác nhận email đã gửi.")
    except Exception as exc:
        failed = services.mark_email_failed(notification.pk, str(exc))
        try:
            schedule_email_retry(failed)
        except Exception as schedule_exc:
            services.update_email_error(
                notification.pk,
                f"{exc}; không lập lịch retry được: {schedule_exc}",
            )
        return False

    services.mark_email_sent(notification.pk)
    return True
