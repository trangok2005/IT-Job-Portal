"""SMTP adapter used by notification delivery tasks."""
from django.conf import settings
from django.core.mail import send_mail


def send_text_email(*, subject: str, message: str, recipients: list[str]) -> None:
    """Send one plain-text email and fail if SMTP does not accept it."""
    sent = send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipients,
        fail_silently=False,
    )
    if sent != 1:
        raise RuntimeError("SMTP không xác nhận email đã được gửi.")
