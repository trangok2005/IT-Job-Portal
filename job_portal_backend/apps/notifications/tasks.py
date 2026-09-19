from django.db.models import F
from django.utils import timezone

from apps.applications.models import ApplicationStatusHistory, JobApplication
from integrations.email.smtp import send_text_email


def send_application_status_email(history_id: str) -> bool:
    history = (
        ApplicationStatusHistory.objects.select_related(
            "application__candidate__user",
            "application__job",
        )
        .filter(pk=history_id)
        .first()
    )
    if history is None:
        return False
    if history.notification_status == history.NotificationStatus.SENT:
        return True

    application = history.application
    status_label = JobApplication.Status(history.to_status).label
    candidate = application.candidate
    message_lines = [
        f"Xin chào {candidate.full_name},",
        "",
        f"Hồ sơ ứng tuyển vị trí {application.job.title} của bạn "
        f"đã được cập nhật sang trạng thái: {status_label}.",
    ]
    if history.candidate_message:
        message_lines.extend(["", history.candidate_message])
    message_lines.extend(["", "Trân trọng,", "IT Job Portal"])

    try:
        send_text_email(
            subject=f"[IT Job Portal] Cập nhật hồ sơ: {status_label}",
            message="\n".join(message_lines),
            recipients=[candidate.user.email],
        )
    except Exception as exc:
        ApplicationStatusHistory.objects.filter(pk=history.pk).update(
            notification_status=history.NotificationStatus.FAILED,
            notification_attempts=F("notification_attempts") + 1,
            notification_error=str(exc)[:2000],
        )
        raise

    ApplicationStatusHistory.objects.filter(pk=history.pk).update(
        notification_status=history.NotificationStatus.SENT,
        notification_attempts=F("notification_attempts") + 1,
        notification_error="",
        notification_sent_at=timezone.now(),
    )
    return True
