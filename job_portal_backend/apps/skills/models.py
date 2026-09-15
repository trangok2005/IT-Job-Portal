from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import BaseModel, TimeStampedModel, UUIDModel


class SkillCategory(UUIDModel):
    name = models.CharField(max_length=150, unique=True)

    class Meta:
        db_table = "skill_categories"

    def __str__(self):
        return self.name


class Skill(BaseModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Chờ duyệt"
        APPROVED = "APPROVED", "Đã duyệt"
        REJECTED = "REJECTED", "Từ chối"
        MERGED = "MERGED", "Đã gộp vào skill khác"

    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=170, unique=True)
    category = models.ForeignKey(
        SkillCategory, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="skills",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Admin tạm ẩn 1 skill đã APPROVED (khác với status, dùng khi cần deprecate).",
    )

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.APPROVED)
    # Giữ skill đã gộp để audit; xóa sẽ cascade các liên kết.
    merged_into = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="merged_from",
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reviewed_skills", limit_choices_to={"role": "ADMIN"},
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "skills"
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return self.name

    @property
    def is_approved(self):
        return self.status == self.Status.APPROVED

    @property
    def effective_skill(self):
        """Theo chuỗi merge nếu một FK cũ chưa được rewrite."""
        node = self
        seen = {node.pk}
        while node.status == self.Status.MERGED and node.merged_into_id:
            node = node.merged_into
            if node is None or node.pk in seen:
                break
            seen.add(node.pk)
        return node


class SkillAlias(UUIDModel):
    """Ánh xạ tên nhập hoặc trích xuất về skill canonical."""

    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="aliases")
    alias_text = models.CharField(max_length=150, unique=True)
    normalized_text = models.CharField(
        max_length=150, unique=True,
        help_text="lower-cased / accent-stripped version, dùng để fuzzy-match (rapidfuzz) trước khi coi là skill mới hoàn toàn.",
    )

    class Meta:
        db_table = "skill_aliases"

    def __str__(self):
        return f"{self.alias_text} -> {self.skill.name}"


class MatchingWeightConfig(BaseModel):

    name = models.CharField(max_length=150)
    is_active = models.BooleanField(default=False)

    weight_semantic_similarity = models.DecimalField(max_digits=4, decimal_places=3, default=0.350)
    weight_skill_overlap = models.DecimalField(max_digits=4, decimal_places=3, default=0.400)
    weight_experience_match = models.DecimalField(max_digits=4, decimal_places=3, default=0.200)
    weight_education_match = models.DecimalField(max_digits=4, decimal_places=3, default=0.050)
    required_skill_multiplier = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        default=2,
        validators=[MinValueValidator(1)],
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="updated_weight_configs",
        limit_choices_to={"role": "ADMIN"},
    )

    class Meta:
        db_table = "matching_weight_configs"
        constraints = [
            models.UniqueConstraint(
                fields=["is_active"],
                condition=models.Q(is_active=True),
                name="unique_active_matching_weight_config",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(weight_semantic_similarity__gte=0)
                    & models.Q(weight_skill_overlap__gte=0)
                    & models.Q(weight_experience_match__gte=0)
                    & models.Q(weight_education_match__gte=0)
                    & models.Q(weight_semantic_similarity__lte=1)
                    & models.Q(weight_skill_overlap__lte=1)
                    & models.Q(weight_experience_match__lte=1)
                    & models.Q(weight_education_match__lte=1)
                ),
                name="matching_weights_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(required_skill_multiplier__gte=1),
                name="required_skill_multiplier_gte_one",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({'active' if self.is_active else 'inactive'})"


class CandidateSkill(UUIDModel, TimeStampedModel):
    candidate = models.ForeignKey(
        "candidates.CandidateProfile", on_delete=models.CASCADE, related_name="candidate_skills",
    )
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="candidate_links")
    years_of_experience = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        db_table = "candidate_skills"
        constraints = [
            models.UniqueConstraint(fields=["candidate", "skill"], name="uniq_candidate_skill"),
        ]

    def __str__(self):
        return f"{self.candidate_id} - {self.skill.name}"
