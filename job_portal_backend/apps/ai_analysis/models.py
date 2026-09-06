"""Persisted weighted match results captured for job applications."""
from django.db import models

from apps.core.models import UUIDModel
from apps.applications.models import JobApplication


class ApplicationMatchResult(UUIDModel):
    class Status(models.TextChoices):
        COMPLETED = "COMPLETED", "Đã tính điểm"
        INSUFFICIENT = "INSUFFICIENT", "Chưa đủ điều kiện tính điểm"

    application = models.OneToOneField(
        JobApplication, on_delete=models.CASCADE, related_name="match_result",
    )

    # Điểm tổng hợp cuối cùng (0-100) theo trọng số MatchingWeightConfig
    # đang kích hoạt tại thời điểm tính, hiển thị cho NTD ở UC-04.
    match_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.COMPLETED)

    # Các thành phần điểm con phục vụ giải thích ("Vì sao điểm này?").
    semantic_similarity_score = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    skill_overlap_score = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    experience_score = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    education_score = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)

    matched_skills = models.JSONField(default=list, blank=True, help_text="Danh sách skill trùng khớp giữa CV và JD.")
    missing_skills = models.JSONField(default=list, blank=True, help_text="Skill JD yêu cầu nhưng CV không có.")
    criteria_applicability = models.JSONField(default=dict, blank=True)
    original_weights = models.JSONField(default=dict, blank=True)
    normalized_weights = models.JSONField(default=dict, blank=True)
    missing_information = models.JSONField(default=dict, blank=True)
    rule_version = models.CharField(max_length=50, default="matching-v2.2.4")
    embedding_metadata = models.JSONField(default=dict, blank=True)

    # Snapshot trên application giữ cấu hình trọng số và phiên bản input.
    embedding_model_version = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "application_match_results"
        indexes = [models.Index(fields=["match_score"], name="app_match_score_idx")]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(match_score__isnull=True)
                    | (models.Q(match_score__gte=0) & models.Q(match_score__lte=100))
                ),
                name="application_match_score_range",
            ),
            *[
                models.CheckConstraint(
                    condition=(
                        ~models.Q(rule_version="matching-v2.2.4")
                        | models.Q(**{f"{field}__isnull": True})
                        | (
                            models.Q(**{f"{field}__gte": 0})
                            & models.Q(**{f"{field}__lte": 1})
                        )
                    ),
                    name=f"v224_{field}_range",
                )
                for field in (
                    "semantic_similarity_score",
                    "skill_overlap_score",
                    "experience_score",
                    "education_score",
                )
            ],
        ]

    def __str__(self):
        return f"{self.application_id}: {self.match_score}"
