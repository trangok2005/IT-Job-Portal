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

    # Tăng version khi nội dung đổi để không dùng lại embedding cũ.
    profile_version = models.PositiveIntegerField(default=1)

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
    """Bản tạm để xem kết quả AI mà chưa ghi đè hồ sơ."""

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
    # Giới hạn retry để bảo vệ quota Gemini.
    parse_attempts = models.PositiveSmallIntegerField(default=0)
    parsed_data = models.JSONField(
        null=True, blank=True, help_text="Dữ liệu đã validate, dùng để điền Form preview."
    )
    parse_error_message = models.TextField(blank=True)

    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "resume_imports"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.original_filename} ({self.parse_status})"


class Resume(UUIDModel, TimeStampedModel):
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
