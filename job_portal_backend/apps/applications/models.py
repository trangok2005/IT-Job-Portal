"""
applications/models.py
UC "Ứng tuyển" (candidate) + UC-04 "Xử lý ứng tuyển" (employer).
Trạng thái tuân theo state machine trong Charter:
    applied -> shortlisted -> interviewed -> hired
    applied -> rejected | shortlisted -> rejected | interviewed -> rejected
hired/rejected là trạng thái cuối (terminal), không cho chuyển tiếp
(UC-04 exception E3 "Trạng thái không hợp lệ").
"""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import BaseModel
from apps.candidates.models import CandidateProfile, Resume
from apps.jobs.models import JobPost


class JobApplication(BaseModel):
    class Status(models.TextChoices):
        APPLIED = "APPLIED", "Đã ứng tuyển"
        SHORTLISTED = "SHORTLISTED", "Đã chọn lọc"
        INTERVIEWED = "INTERVIEWED", "Đã phỏng vấn"
        REJECTED = "REJECTED", "Từ chối"
        HIRED = "HIRED", "Tuyển dụng"

    # Bảng chuyển trạng thái hợp lệ, dùng để validate ở service layer trước
    # khi save() (UC-04 E3: "Trạng thái không hợp lệ -> báo lỗi, giữ nguyên").
    VALID_TRANSITIONS = {
        Status.APPLIED: {Status.SHORTLISTED, Status.REJECTED},
        Status.SHORTLISTED: {Status.INTERVIEWED, Status.REJECTED},
        Status.INTERVIEWED: {Status.HIRED, Status.REJECTED},
        Status.HIRED: set(),       # terminal
        Status.REJECTED: set(),    # terminal
    }

    job = models.ForeignKey(JobPost, on_delete=models.CASCADE, related_name="applications")
    candidate = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name="applications")
    # Snapshot CV dùng để ứng tuyển tại thời điểm nộp — nếu ứng viên sửa/xóa
    # CV sau đó, hồ sơ ứng tuyển này vẫn tham chiếu đúng bản đã nộp.
    resume = models.ForeignKey(
        Resume,
        on_delete=models.RESTRICT,
        null=True,
        related_name="applications",
    )

    cover_letter = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.APPLIED)
    status_updated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "job_applications"
        constraints = [
            # Ngăn ứng viên nộp trùng vào cùng 1 tin (đáp ứng ràng buộc ngầm
            # trong UC "Ứng tuyển").
            models.UniqueConstraint(fields=["job", "candidate"], name="uniq_job_candidate_application"),
        ]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["job", "status"]),
        ]

    def __str__(self):
        return f"{self.candidate.full_name} -> {self.job.title} [{self.status}]"

    def can_transition_to(self, new_status: str, from_status: str | None = None) -> bool:
        """Kiểm tra transition từ trạng thái chỉ định hoặc trạng thái hiện tại."""
        source_status = from_status or self.status
        return new_status in self.VALID_TRANSITIONS.get(source_status, set())

    def clean(self):
        # Bảo vệ ở tầng model, ngoài validate ở serializer/service.
        if self.pk:
            old_status = JobApplication.objects.get(pk=self.pk).status
            if old_status != self.status and not self.can_transition_to(
                self.status,
                from_status=old_status,
            ):
                raise ValidationError(
                    f"Không thể chuyển trạng thái từ '{old_status}' sang '{self.status}'."
                )


class ApplicationStatusHistory(BaseModel):
    """Audit trail cho mỗi lần đổi trạng thái — phục vụ UC "Theo dõi trạng
    thái ứng tuyển" (ứng viên xem lịch sử) và truy vết cho Admin/NTD.
    """

    application = models.ForeignKey(JobApplication, on_delete=models.CASCADE, related_name="status_history")
    from_status = models.CharField(max_length=20, choices=JobApplication.Status.choices, blank=True)
    to_status = models.CharField(max_length=20, choices=JobApplication.Status.choices)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="application_status_changes",
    )
    note = models.TextField(blank=True)

    class Meta:
        db_table = "application_status_history"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.application_id}: {self.from_status} -> {self.to_status}"
