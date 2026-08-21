"""
jobs/models.py
UC-02 "Đăng tin tuyển dụng" + UC-03 "Tìm kiếm công việc".
JobPost giữ embedding (pgvector) sinh từ JD, dùng để so khớp semantic với
CandidateProfile.embedding. JobSkill là bảng trung gian có trọng số, phục
vụ Business Rule Ranking (kết hợp semantic similarity + skill overlap).
"""
from django.conf import settings
from django.db import models
from pgvector.django import VectorField, HnswIndex

from apps.core.models import BaseModel
from integrations.gemini.embeddings import (
    EMBEDDING_DIMENSIONS,
    current_job_embedding_signature,
)
from apps.companies.models import Company
from apps.skills.models import Skill


class JobPost(BaseModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Nháp"
        ACTIVE = "ACTIVE", "Đang tuyển"
        CLOSED = "CLOSED", "Đã đóng"
        EXPIRED = "EXPIRED", "Hết hạn"

    class JobType(models.TextChoices):
        FULL_TIME = "FULL_TIME", "Toàn thời gian"
        PART_TIME = "PART_TIME", "Bán thời gian"
        INTERNSHIP = "INTERNSHIP", "Thực tập"
        CONTRACT = "CONTRACT", "Hợp đồng"
        REMOTE = "REMOTE", "Từ xa"

    class ExperienceLevel(models.TextChoices):
        INTERN = "INTERN", "Thực tập sinh"
        FRESHER = "FRESHER", "Mới tốt nghiệp"
        JUNIOR = "JUNIOR", "Junior"
        MIDDLE = "MIDDLE", "Middle"
        SENIOR = "SENIOR", "Senior"
        LEAD = "LEAD", "Lead / Manager"

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="job_posts")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="created_job_posts", limit_choices_to={"role": "EMPLOYER"},
    )

    title = models.CharField(max_length=255)
    description = models.TextField()
    requirements = models.TextField(blank=True)
    benefits = models.TextField(blank=True)

    location = models.CharField(max_length=255, blank=True)
    job_type = models.CharField(max_length=20, choices=JobType.choices, default=JobType.FULL_TIME)
    experience_level = models.CharField(max_length=20, choices=ExperienceLevel.choices, blank=True)
    salary_min = models.PositiveIntegerField(null=True, blank=True)
    salary_max = models.PositiveIntegerField(null=True, blank=True)
    salary_negotiable = models.BooleanField(default=False)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    published_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    # --- Nguồn JD gốc + kết quả AI parse (giống Resume ở candidates app) ---
    raw_jd_file = models.FileField(upload_to="job_descriptions/%Y/%m/", null=True, blank=True)
    raw_extracted_json = models.JSONField(null=True, blank=True)

    required_skills = models.ManyToManyField(Skill, through="JobSkill", related_name="job_posts")

    # --- Embedding cho semantic search / matching ---
    content_version = models.PositiveIntegerField(default=1)
    embedding = VectorField(dimensions=EMBEDDING_DIMENSIONS, null=True, blank=True)
    embedding_version = models.PositiveIntegerField(default=0)
    embedding_updated_at = models.DateTimeField(null=True, blank=True)
    embedding_signature = models.CharField(max_length=255, blank=True)

    view_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "job_posts"
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["job_type"]),
            HnswIndex(
                name="job_embedding_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ]

    def __str__(self):
        return f"{self.title} @ {self.company.name}"

    @property
    def is_open(self):
        return self.status == self.Status.ACTIVE

    @property
    def embedding_is_stale(self):
        """Cho biết embedding có còn khớp nội dung JD hiện tại hay không."""
        return (
            self.embedding is None
            or self.embedding_version != self.content_version
            or self.embedding_signature != current_job_embedding_signature()
        )


class JDImport(BaseModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Đang chờ"
        PROCESSING = "PROCESSING", "Đang phân tích"
        SUCCESS = "SUCCESS", "Hoàn tất"
        FAILED = "FAILED", "Thất bại"
        CONSUMED = "CONSUMED", "Đã tạo tin"

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="jd_imports"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="jd_imports",
    )
    file = models.FileField(upload_to="job_description_imports/%Y/%m/")
    original_filename = models.CharField(max_length=255)
    file_size_bytes = models.PositiveBigIntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    raw_extracted_json = models.JSONField(null=True, blank=True)
    parsed_data = models.JSONField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    expires_at = models.DateTimeField()
    consumed_job = models.OneToOneField(
        JobPost,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_jd_import",
    )

    class Meta:
        db_table = "jd_imports"
        indexes = [
            models.Index(
                fields=["created_by", "status"],
                name="jd_imports_created_7f3574_idx",
            )
        ]


class JobSkill(BaseModel):
    """Trọng số từng skill trong 1 tin tuyển dụng, dùng cho skill-overlap
    score ở Business Rule Ranking (kết hợp với semantic similarity)."""

    job = models.ForeignKey(JobPost, on_delete=models.CASCADE, related_name="job_skills")
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="job_links")
    is_required = models.BooleanField(default=True, help_text="False = 'nice to have'")
    weight = models.DecimalField(max_digits=3, decimal_places=2, default=1.00)
    min_years = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)

    class Meta:
        db_table = "job_skills"
        constraints = [
            models.UniqueConstraint(fields=["job", "skill"], name="uniq_job_skill"),
        ]

    def __str__(self):
        return f"{self.job.title} - {self.skill.name}"
