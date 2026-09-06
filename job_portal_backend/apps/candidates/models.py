"""
candidates/models.py
UC-01 "Quản lý hồ sơ ứng viên". Covers:
  - CandidateProfile: thông tin hồ sơ + embedding vector (pgvector) dùng cho
    semantic search (UC-03) và tính Match Score (UC-04).
  - Education / Experience: dữ liệu có cấu trúc được ứng viên xác nhận.
  - ResumeImport: bản ghi tạm lưu file CV + kết quả parse từ Gemini.
    Dùng cho luồng Non-blocking UI: upload -> parse ngầm -> preview -> user confirm.
    Tự hết hạn sau 24h nếu không được consume. Không ảnh hưởng Resume chính thức.
  - Resume: file CV chính thức đã được user xác nhận (is_primary=True).

Yêu cầu cài: pip install pgvector
INSTALLED_APPS cần "pgvector" KHÔNG bắt buộc, nhưng DB phải có extension:
    CREATE EXTENSION IF NOT EXISTS vector;
(thường chạy bằng migration RunSQL, xem ai_analysis/migrations note ở README)
"""
from django.conf import settings
from django.db import models
from django.db.models import Q
from pgvector.django import VectorField, HnswIndex

from apps.core.models import TimeStampedModel, UUIDModel
from integrations.gemini.embeddings import (
    EMBEDDING_DIMENSIONS,
    current_candidate_embedding_signature,
)


class DegreeLevel(models.TextChoices):
    NONE = "NONE", "Không có bằng thuộc danh mục"
    ASSOCIATE = "ASSOCIATE", "Cao đẳng"
    BACHELOR = "BACHELOR", "Cử nhân / Kỹ sư"
    MASTER = "MASTER", "Thạc sĩ"
    PHD = "PHD", "Tiến sĩ"


DEGREE_LEVEL_RANK = {
    DegreeLevel.NONE: 0,
    DegreeLevel.ASSOCIATE: 1,
    DegreeLevel.BACHELOR: 2,
    DegreeLevel.MASTER: 3,
    DegreeLevel.PHD: 4,
}


class CandidateProfile(UUIDModel, TimeStampedModel):
    class Gender(models.TextChoices):
        MALE = "MALE", "Nam"
        FEMALE = "FEMALE", "Nữ"
        OTHER = "OTHER", "Khác"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="candidate_profile",
        limit_choices_to={"role": "CANDIDATE"},
    )

    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True)
    dob = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=Gender.choices, blank=True)
    address = models.CharField(max_length=500, blank=True)
    avatar_url = models.URLField(blank=True)
    headline = models.CharField(max_length=255, blank=True, help_text="vd: 'Backend Developer 2 năm kinh nghiệm'")
    summary = models.TextField(blank=True)
    desired_position = models.CharField(max_length=255, blank=True)
    is_public = models.BooleanField(default=True, help_text="Cho phép NTD tìm thấy qua Gợi ý ứng viên phù hợp")

    # --- Versioning: mỗi lần cập nhật hồ sơ đáng kể -> tăng version và
    # đánh dấu cần tính lại embedding (đáp ứng "profile_version" trong đặc tả).
    profile_version = models.PositiveIntegerField(default=1)

    # --- Embedding cho semantic search (UC-03) và match score (UC-04) ---
    embedding = VectorField(dimensions=EMBEDDING_DIMENSIONS, null=True, blank=True)
    embedding_version = models.PositiveIntegerField(
        default=0, help_text="profile_version tại thời điểm embedding được tính, dùng để biết embedding có 'stale' hay không.",
    )
    embedding_updated_at = models.DateTimeField(null=True, blank=True)
    embedding_signature = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "candidate_profiles"
        indexes = [
            HnswIndex(
                name="candidate_embedding_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ]

    def __str__(self):
        return self.full_name

    @property
    def embedding_is_stale(self):
        return (
            self.embedding is None
            or self.embedding_version != self.profile_version
            or self.embedding_signature != current_candidate_embedding_signature()
        )

    @property
    def is_complete(self):
        """Hồ sơ đủ điều kiện ứng tuyển khi có liên hệ và ít nhất một skill."""
        required_fields = (self.full_name, self.phone, self.desired_position)
        return bool(
            all(value and value.strip() for value in required_fields)
            and self.candidate_skills.filter(
                skill__is_active=True,
                skill__status__in=("APPROVED", "PENDING"),
            ).exists()
        )


class Education(UUIDModel, TimeStampedModel):
    candidate = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name="educations")
    school_name = models.CharField(max_length=255)
    major = models.CharField(max_length=255, blank=True)
    degree = models.CharField(max_length=150, blank=True)
    degree_level = models.CharField(
        max_length=20,
        choices=DegreeLevel.choices,
        null=True,
        blank=True,
    )
    is_completed = models.BooleanField(default=False)
    is_verified = models.BooleanField(
        default=False,
        help_text="Ứng viên đã xác nhận dữ liệu học vấn này.",
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)
    class Meta:
        db_table = "candidate_educations"
        ordering = ["-end_date"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(start_date__isnull=True)
                    | Q(end_date__isnull=True)
                    | Q(end_date__gte=models.F("start_date"))
                ),
                name="education_valid_date_range",
            ),
        ]

    def __str__(self):
        return f"{self.school_name} - {self.major}"


class Experience(UUIDModel, TimeStampedModel):
    candidate = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name="experiences")
    company_name = models.CharField(max_length=255)
    position = models.CharField(max_length=255)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    class Meta:
        db_table = "candidate_experiences"
        ordering = ["-end_date"]
        constraints = [
            models.CheckConstraint(
                condition=Q(is_current=False) | Q(end_date__isnull=True),
                name="current_experience_has_no_end",
            ),
            models.CheckConstraint(
                condition=(
                    Q(start_date__isnull=True)
                    | Q(end_date__isnull=True)
                    | Q(end_date__gte=models.F("start_date"))
                ),
                name="experience_valid_date_range",
            ),
        ]

    def __str__(self):
        return f"{self.position} @ {self.company_name}"


class ResumeImport(UUIDModel, TimeStampedModel):
    """Bản ghi tạm cho luồng upload CV -> AI parse -> preview -> user confirm (UC-01).
    Tách riêng khỏi Resume (CV chính thức) để:
    - Không ghi đè hồ sơ chính khi user chỉ preview.
    - Tự dọn dẹp sau 24h nếu user không confirm (expires_at).
    - Cho phép user thử nhiều CV khác nhau trước khi quyết định lưu.
    """

    class ParseStatus(models.TextChoices):
        PENDING = "PENDING", "Đang xử lý"
        PROCESSING = "PROCESSING", "Đang phân tích"
        SUCCESS = "SUCCESS", "Thành công"
        FAILED = "FAILED", "Thất bại"
        CONSUMED = "CONSUMED", "Đã dùng để cập nhật hồ sơ"

    candidate = models.ForeignKey(
        CandidateProfile, on_delete=models.CASCADE, related_name="resume_imports"
    )
    file = models.FileField(upload_to="resume_imports/%Y/%m/")
    original_filename = models.CharField(max_length=255)
    file_size_bytes = models.PositiveIntegerField(null=True, blank=True)

    parse_status = models.CharField(
        max_length=20, choices=ParseStatus.choices, default=ParseStatus.PENDING
    )
    # Giới hạn số lần Gemini parse lại bản ghi này (chống retry vô hạn của broker).
    parse_attempts = models.PositiveSmallIntegerField(default=0)
    parsed_data = models.JSONField(
        null=True, blank=True, help_text="Dữ liệu đã validate, dùng để điền Form preview."
    )
    parse_error_message = models.TextField(blank=True)

    # Tự động hết hạn sau 24h, dọn dẹp bởi task định kỳ hoặc khi user hủy chỉnh sửa.
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "resume_imports"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.original_filename} ({self.parse_status})"


class Resume(UUIDModel, TimeStampedModel):
    """File CV chính thức do ứng viên xác nhận từ bản xem trước."""

    candidate = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name="resumes")
    file = models.FileField(upload_to="resumes/%Y/%m/")
    original_filename = models.CharField(max_length=255)
    file_size_bytes = models.PositiveIntegerField(null=True, blank=True)

    is_primary = models.BooleanField(default=True, help_text="CV chính hiện dùng để ứng tuyển mặc định.")

    class Meta:
        db_table = "resumes"
        constraints = [
            models.UniqueConstraint(
                fields=["candidate"],
                condition=Q(is_primary=True),
                name="unique_primary_resume_per_candidate",
            ),
        ]

    def __str__(self):
        return self.original_filename
