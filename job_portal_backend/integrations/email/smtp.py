"""Adapter SMTP cho các task gửi thông báo."""
from django.conf import settings
from django.core.mail import send_mail


def send_text_email(*, subject: str, message: str, recipients: list[str]) -> None:
    """Gửi email văn bản thuần và báo lỗi nếu SMTP không chấp nhận."""
    sent = send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipients,
        fail_silently=False,
    )
    if sent != 1:
        raise RuntimeError("SMTP không xác nhận email đã được gửi.")
