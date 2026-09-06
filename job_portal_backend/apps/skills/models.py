"""
skills/models.py
UC diagram: Admin "Quản trị Skill và tiêu chí phù hợp".
Solves Charter problem #6: "Skill trong CV và tin tuyển dụng có thể được
biểu diễn bằng nhiều cách khác nhau" -> Skill (canonical) + SkillAlias
(raw strings extracted by AI, normalized to a canonical Skill).

Note: CandidateSkill (bảng nối candidate <-> skill) được định nghĩa ở CUỐI
file này thay vì trong candidates/models.py để tránh circular import
(candidates cần import Skill, nhưng Skill không cần biết về Candidate).
Django tự phát hiện model theo module "<app>/models.py" nên phải để ở đây,
KHÔNG để ở file rời (vd skills/candidate_skill.py) nếu không tự import nó
trong models.py hoặc khai báo lại default_app_config.
"""
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
    """Canonical / normalized skill node in the taxonomy."""

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

    # --- Non-blocking taxonomy: skill lạ được tạo NGAY ở trạng thái PENDING,
    # không chặn luồng lưu hồ sơ/JD. Admin duyệt sau theo lô. ---
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.APPROVED)
    # --- Gộp trùng: khi Admin thấy 2 skill thực ra là 1 (VD "ReactJS" và
    # "React"), KHÔNG xoá skill này (sẽ cascade-xoá luôn mọi
    # CandidateSkill/JobSkill đã trỏ vào nó, làm mất dữ liệu đã hiển thị
    # trên hồ sơ). Thay vào đó set MERGED + merged_into, và service layer
    # sẽ viết lại (rewrite) toàn bộ CandidateSkill/JobSkill đang trỏ vào
    # đây sang merged_into thay vì giữ nguyên chain để tránh phải resolve
    # merge nhiều tầng lúc query.
    merged_into = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="merged_from",
    )

    # --- Audit trail duyệt, cùng pattern với Company.reviewed_by ---
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
        """Nếu skill này đã bị gộp, trả về skill đích cuối cùng (phòng khi
        service layer bỏ sót bước rewrite FK lúc merge)."""
        node = self
        seen = {node.pk}
        while node.status == self.Status.MERGED and node.merged_into_id:
            node = node.merged_into
            if node is None or node.pk in seen:
                break
            seen.add(node.pk)
        return node


class SkillAlias(UUIDModel):
    """Raw strings (as typed by users or extracted by Gemini) that map to a
    canonical Skill, e.g. 'ReactJS', 'React.js', 'react' -> Skill('React').
    This is the core of the Skill Normalization step in the AI pipeline.
    """

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
    """Admin "Quản trị tiêu chí và trọng số tính mức độ phù hợp".
    Only one config should be is_active=True at a time; Business Rule
    Ranking step reads the active config when combining semantic similarity
    with rule-based signals.
    """

    name = models.CharField(max_length=150)
    is_active = models.BooleanField(default=False)

    # Weights should sum to 1.0 (validated at the serializer/service layer).
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
    """Normalized skill selected for a candidate profile."""

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
