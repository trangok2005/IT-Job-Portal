"""
notifications/models.py
UC-04 exception E4: "Gửi email thất bại -> trạng thái vẫn được lưu, chỉ
việc gửi email thất bại, lỗi được ghi log". Notification là bản ghi log đó,
đồng thời phục vụ hiển thị thông báo trong ứng dụng (in-app).
Được tạo/gửi bất đồng bộ qua Django-Q (worker đọc bảng này hoặc nhận task).
"""
from django.conf import settings
from django.db import models

from apps.core.models import BaseModel
from apps.applications.models import JobApplication


class Notification(BaseModel):
    class NotifType(models.TextChoices):
        APPLICATION_RECEIVED = "APPLICATION_RECEIVED", "Nhà tuyển dụng nhận được hồ sơ mới"
        APPLICATION_STATUS_CHANGED = "APPLICATION_STATUS_CHANGED", "Trạng thái ứng tuyển thay đổi"
        COMPANY_APPROVED = "COMPANY_APPROVED", "Hồ sơ công ty được duyệt"
        COMPANY_REJECTED = "COMPANY_REJECTED", "Hồ sơ công ty bị từ chối"
        JOB_MATCH_SUGGESTION = "JOB_MATCH_SUGGESTION", "Gợi ý việc làm phù hợp"

    class Channel(models.TextChoices):
        EMAIL = "EMAIL", "Email"
        IN_APP = "IN_APP", "Trong ứng dụng"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Chờ gửi"
        PROCESSING = "PROCESSING", "Đang gửi"
        SENT = "SENT", "Đã gửi"
        FAILED = "FAILED", "Thất bại"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications",
    )
    application = models.ForeignKey(
        JobApplication, on_delete=models.CASCADE, null=True, blank=True, related_name="notifications",
    )
    notif_type = models.CharField(max_length=40, choices=NotifType.choices)
    channel = models.CharField(max_length=20, choices=Channel.choices, default=Channel.EMAIL)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    title = models.CharField(max_length=255)
    message = models.TextField(blank=True)
    payload = models.JSONField(default=dict, blank=True, help_text="Dữ liệu cấu trúc để render template email/UI.")

    is_read = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    retry_count = models.PositiveSmallIntegerField(default=0)
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = "notifications"
        indexes = [
            models.Index(fields=["recipient", "is_read"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"[{self.status}] {self.title} -> {self.recipient_id}"
