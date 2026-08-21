"""Write operations cho notification in-app và email."""
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.notifications.models import Notification


def _enqueue_email(notification: Notification) -> None:
    """Enqueue email sau commit; lỗi queue được ghi FAILED thay vì phá nghiệp vụ gốc."""

    def enqueue():
        try:
            from django_q.tasks import async_task

            async_task(
                "apps.notifications.tasks.send_notification_email",
                str(notification.pk),
            )
        except Exception as exc:
            failed = mark_email_failed(
                notification.pk,
                f"Không enqueue được email: {exc}",
            )
            try:
                from apps.notifications.tasks import schedule_email_retry

                schedule_email_retry(failed)
            except Exception as schedule_exc:
                update_email_error(
                    notification.pk,
                    f"{failed.error_message}; không lập lịch retry được: {schedule_exc}",
                )

    transaction.on_commit(enqueue, robust=True)


def _create_notification_pair(
    recipient,
    application,
    notif_type,
    title,
    message,
) -> tuple[Notification, Notification]:
    """Tạo đồng thời bản in-app đã sẵn sàng và bản email chờ worker gửi."""
    payload = {
        "application_id": str(application.pk),
        "job_id": str(application.job_id),
        "status": application.status,
    }
    in_app = Notification.objects.create(
        recipient=recipient,
        application=application,
        notif_type=notif_type,
        channel=Notification.Channel.IN_APP,
        status=Notification.Status.SENT,
        title=title,
        message=message,
        payload=payload,
        sent_at=timezone.now(),
    )
    email = Notification.objects.create(
        recipient=recipient,
        application=application,
        notif_type=notif_type,
        channel=Notification.Channel.EMAIL,
        status=Notification.Status.PENDING,
        title=title,
        message=message,
        payload=payload,
    )
    _enqueue_email(email)
    return in_app, email


def notify_application_received(application):
    """Thông báo employer khi candidate vừa nộp hồ sơ vào một job."""
    return _create_notification_pair(
        recipient=application.job.company.owner,
        application=application,
        notif_type=Notification.NotifType.APPLICATION_RECEIVED,
        title="Có hồ sơ ứng tuyển mới",
        message=(
            f"{application.candidate.full_name} đã ứng tuyển vào "
            f"{application.job.title}."
        ),
    )


def notify_application_status_changed(application):
    """Thông báo candidate sau khi employer chuyển trạng thái ứng tuyển."""
    return _create_notification_pair(
        recipient=application.candidate.user,
        application=application,
        notif_type=Notification.NotifType.APPLICATION_STATUS_CHANGED,
        title="Trạng thái ứng tuyển đã thay đổi",
        message=(
            f"Hồ sơ ứng tuyển {application.job.title} đã chuyển sang "
            f"{application.get_status_display()}."
        ),
    )


@transaction.atomic
def claim_email_notification(notification_id):
    """Khóa một email cho worker; trả None nếu đã gửi/đang gửi/hết retry."""
    notification = (
        Notification.objects.select_for_update()
        .select_related("recipient")
        .get(pk=notification_id)
    )
    if notification.channel != Notification.Channel.EMAIL:
        return None
    if notification.status in {
        Notification.Status.SENT,
        Notification.Status.PROCESSING,
    }:
        return None
    if notification.retry_count >= settings.NOTIFICATION_MAX_RETRIES:
        return None
    notification.status = Notification.Status.PROCESSING
    notification.save(update_fields=["status", "updated_at"])
    return notification


def mark_email_sent(notification_id) -> None:
    """Đánh dấu email gửi thành công và xóa lỗi cũ nếu đây là lần retry."""
    Notification.objects.filter(pk=notification_id).update(
        status=Notification.Status.SENT,
        sent_at=timezone.now(),
        error_message="",
        updated_at=timezone.now(),
    )


def mark_email_failed(notification_id, error_message: str) -> Notification:
    """Ghi lỗi email độc lập với transaction thay đổi application."""
    notification = Notification.objects.get(pk=notification_id)
    notification.status = Notification.Status.FAILED
    notification.retry_count += 1
    notification.error_message = error_message[:2000]
    notification.save(
        update_fields=["status", "retry_count", "error_message", "updated_at"]
    )
    return notification


def update_email_error(notification_id, error_message: str) -> None:
    """Bổ sung chi tiết lỗi hạ tầng mà không tăng số lần gửi email."""
    Notification.objects.filter(pk=notification_id).update(
        error_message=error_message[:2000],
        updated_at=timezone.now(),
    )


def mark_notification_read(notification: Notification, user) -> Notification:
    """Chỉ recipient được đánh dấu notification in-app của mình là đã đọc."""
    if notification.recipient_id != user.pk:
        raise ValueError("Bạn không có quyền cập nhật thông báo này.")
    if notification.channel != Notification.Channel.IN_APP:
        raise ValueError("Chỉ thông báo in-app có trạng thái đã đọc.")
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=["is_read", "updated_at"])
    return notification
