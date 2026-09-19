from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from pgvector.django import VectorField

from apps.core.models import TimeStampedModel, UUIDModel
from apps.candidates.models import CandidateProfile, Resume
from apps.jobs.models import JobPost
from integrations.gemini.embeddings import EMBEDDING_DIMENSIONS


class JobApplication(UUIDModel, TimeStampedModel):
    class MatchStatus(models.TextChoices):
        PENDING = "PENDING", "Đang chờ tính điểm"
        PROCESSING = "PROCESSING", "Đang tính điểm"
        COMPLETED = "COMPLETED", "Đã tính điểm"
        FAILED = "FAILED", "Tính điểm thất bại"
        INSUFFICIENT = "INSUFFICIENT", "Chưa đủ điều kiện tính điểm"

    class Status(models.TextChoices):
        APPLIED = "APPLIED", "Chờ xem xét"
        SHORTLISTED = "SHORTLISTED", "Đã qua vòng xem xét"
        INTERVIEWED = "INTERVIEWED", "Phỏng vấn"
        REJECTED = "REJECTED", "Từ chối"
        HIRED = "HIRED", "Đã tuyển dụng"

    VALID_TRANSITIONS = {
        Status.APPLIED: {Status.SHORTLISTED, Status.REJECTED},
        Status.SHORTLISTED: {Status.INTERVIEWED, Status.REJECTED},
        Status.INTERVIEWED: {Status.HIRED, Status.REJECTED},
        Status.HIRED: set(),
        Status.REJECTED: set(),
    }

    job = models.ForeignKey(JobPost, on_delete=models.CASCADE, related_name="applications")
    candidate = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name="applications")
    # RESTRICT giữ CV đã nộp khi ứng viên đổi CV chính.
    resume = models.ForeignKey(
        Resume,
        on_delete=models.RESTRICT,
        null=True,
        related_name="applications",
    )

    cover_letter = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.APPLIED)

    # Lưu đầu vào chấm điểm cùng transaction; queue chỉ mang ID.
    profile_snapshot = models.JSONField(null=True, blank=True, editable=False)
    job_snapshot = models.JSONField(null=True, blank=True, editable=False)
    matching_weight_snapshot = models.JSONField(null=True, blank=True, editable=False)
    candidate_embedding_snapshot = VectorField(
        dimensions=EMBEDDING_DIMENSIONS, null=True, blank=True, editable=False,
    )
    job_embedding_snapshot = VectorField(
        dimensions=EMBEDDING_DIMENSIONS, null=True, blank=True, editable=False,
    )
    snapshot_created_at = models.DateTimeField(null=True, blank=True, editable=False)
    match_status = models.CharField(
        max_length=20,
        choices=MatchStatus.choices,
        default=MatchStatus.PENDING,
    )
    match_error = models.TextField(blank=True)
    match_attempts = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "job_applications"
        constraints = [
            models.UniqueConstraint(fields=["job", "candidate"], name="uniq_job_candidate_application"),
        ]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["job", "status"]),
        ]

    def __str__(self):
        return f"{self.candidate.full_name} -> {self.job.title} [{self.status}]"

    def can_transition_to(self, new_status: str, from_status: str | None = None) -> bool:
        source_status = from_status or self.status
        return new_status in self.VALID_TRANSITIONS.get(source_status, set())

    def clean(self):
        # Giữ ràng buộc chuyển trạng thái khi caller bỏ qua service.
        if self.pk:
            old_status = JobApplication.objects.get(pk=self.pk).status
            if old_status != self.status and not self.can_transition_to(
                self.status,
                from_status=old_status,
            ):
                raise ValidationError(
                    f"Không thể chuyển trạng thái từ '{old_status}' sang '{self.status}'."
                )


class ApplicationStatusHistory(UUIDModel):
    application = models.ForeignKey(JobApplication, on_delete=models.CASCADE, related_name="status_history")
    from_status = models.CharField(max_length=20, choices=JobApplication.Status.choices, blank=True)
    to_status = models.CharField(max_length=20, choices=JobApplication.Status.choices)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="application_status_changes",
    )
    note = models.TextField(blank=True, help_text="Ghi chú nội bộ, không hiển thị cho ứng viên.")
    candidate_message = models.TextField(blank=True)

    class NotificationStatus(models.TextChoices):
        NOT_REQUESTED = "NOT_REQUESTED", "Không yêu cầu"
        PENDING = "PENDING", "Đang chờ gửi"
        SENT = "SENT", "Đã gửi"
        FAILED = "FAILED", "Gửi thất bại"

    notification_status = models.CharField(
        max_length=20,
        choices=NotificationStatus.choices,
        default=NotificationStatus.NOT_REQUESTED,
    )
    notification_attempts = models.PositiveSmallIntegerField(default=0)
    notification_error = models.TextField(blank=True)
    notification_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "application_status_history"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.application_id}: {self.from_status} -> {self.to_status}"
