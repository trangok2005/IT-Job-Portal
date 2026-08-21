"""
ai_analysis/models.py
UC-04: "Match Score đã tính sẵn khi ứng viên nộp hồ sơ, lưu vào AI_Analysis"
(khác với Match Score "tạm thời" tính lúc tìm kiếm ở UC-03, KHÔNG lưu bảng
này — xem candidates/models.py và jobs/models.py, embedding chỉ dùng để
query trực tiếp bằng pgvector operator <=> lúc tìm kiếm).
"""
from django.db import models

from apps.core.models import BaseModel
from apps.applications.models import JobApplication
from apps.skills.models import MatchingWeightConfig


class AIAnalysis(BaseModel):
    application = models.OneToOneField(
        JobApplication, on_delete=models.CASCADE, related_name="ai_analysis",
    )

    # Điểm tổng hợp cuối cùng (0-100), hiển thị cho NTD ở UC-04.
    match_score = models.DecimalField(max_digits=5, decimal_places=2)

    # Các thành phần điểm con, phục vụ giải thích ("Vì sao điểm này?") và
    # debug khi kết quả AI bị nghi ngờ sai.
    semantic_similarity_score = models.DecimalField(max_digits=5, decimal_places=2)
    skill_overlap_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    experience_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    education_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    matched_skills = models.JSONField(default=list, blank=True, help_text="Danh sách skill trùng khớp giữa CV và JD.")
    missing_skills = models.JSONField(default=list, blank=True, help_text="Skill JD yêu cầu nhưng CV không có.")

    # Truy vết cấu hình trọng số & phiên bản embedding tại thời điểm tính,
    # để kết quả cũ vẫn giải thích được dù Admin sau này đổi trọng số.
    weight_config = models.ForeignKey(
        MatchingWeightConfig, on_delete=models.SET_NULL, null=True, related_name="analyses",
    )
    embedding_model_version = models.CharField(max_length=100, blank=True)
    candidate_embedding_version = models.PositiveIntegerField(default=0)
    job_embedding_version = models.PositiveIntegerField(default=0)

    computed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ai_analyses"
        verbose_name_plural = "AI analyses"
        indexes = [models.Index(fields=["match_score"])]

    def __str__(self):
        return f"{self.application_id}: {self.match_score}"

    @property
    def inputs_are_stale(self):
        """Cho biết candidate/job đã đổi sau lần tính điểm gần nhất hay chưa."""
        return bool(
            self.candidate_embedding_version
            != self.application.candidate.profile_version
            or self.job_embedding_version != self.application.job.content_version
        )
