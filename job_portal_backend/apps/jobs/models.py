from django.conf import settings
from django.db import models
from pgvector.django import VectorField, HnswIndex

from apps.core.models import TimeStampedModel, UUIDModel
from apps.candidates.models import DegreeLevel
from integrations.gemini.embeddings import (
    EMBEDDING_DIMENSIONS,
    current_job_embedding_signature,
)
from apps.companies.models import Company
from apps.skills.models import Skill


class JobPost(UUIDModel, TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Nháp"
        ACTIVE = "ACTIVE", "Đang tuyển"
        CLOSED = "CLOSED", "Đã đóng"
        EXPIRED = "EXPIRED", "Hết hạn"

    class JobType(models.TextChoices):
        FULL_TIME = "FULL_TIME", "Toàn thời gian"
        PART_TIME = "PART_TIME", "Bán thời gian"
        CONTRACT = "CONTRACT", "Hợp đồng / Freelance"

    class WorkplaceType(models.TextChoices):
        ONSITE = "ONSITE", "Tại văn phòng"
        HYBRID = "HYBRID", "Linh hoạt (Hybrid)"
        REMOTE = "REMOTE", "Từ xa (Remote)"

    class ExperienceLevel(models.TextChoices):
        ENTRY = "ENTRY", "Mới đi làm (Intern / Fresher)"
        JUNIOR = "JUNIOR", "Junior (1 - 2 năm)"
        MID_SENIOR = "MID_SENIOR", "Middle - Senior (3+ năm)"
        LEAD = "LEAD", "Trưởng nhóm / Quản lý"

    class Location(models.TextChoices):
        HO_CHI_MINH = "Hồ Chí Minh", "Hồ Chí Minh"
        HANOI = "Hà Nội", "Hà Nội"
        DA_NANG = "Đà Nẵng", "Đà Nẵng"

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="job_posts")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="created_job_posts", limit_choices_to={"role": "EMPLOYER"},
    )

    title = models.CharField(max_length=255)
    description = models.TextField()
    requirements = models.TextField(blank=True)
    benefits = models.TextField(blank=True)

    location = models.CharField(max_length=20, choices=Location.choices, blank=True)
    workplace_type = models.CharField(
        max_length=20,
        choices=WorkplaceType.choices,
        default=WorkplaceType.ONSITE,
    )
    job_type = models.CharField(max_length=20, choices=JobType.choices, default=JobType.FULL_TIME)
    experience_level = models.CharField(max_length=20, choices=ExperienceLevel.choices, blank=True)
    required_education_level = models.CharField(
        max_length=20,
        choices=DegreeLevel.choices,
        null=True,
        blank=True,
    )
    salary_min = models.PositiveIntegerField(null=True, blank=True)
    salary_max = models.PositiveIntegerField(null=True, blank=True)
    salary_negotiable = models.BooleanField(default=False)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    published_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    required_skills = models.ManyToManyField(Skill, through="JobSkill", related_name="job_posts")

    content_version = models.PositiveIntegerField(default=1)
    embedding = VectorField(dimensions=EMBEDDING_DIMENSIONS, null=True, blank=True)
    embedding_version = models.PositiveIntegerField(default=0)
    embedding_updated_at = models.DateTimeField(null=True, blank=True)
    embedding_signature = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "job_posts"
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["job_type"]),
            models.Index(fields=["workplace_type"], name="job_workplace_idx"),
            models.Index(fields=["experience_level"], name="job_experience_idx"),
            models.Index(fields=["location"], name="job_location_idx"),
            models.Index(fields=["salary_max"], name="job_salary_max_idx"),
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
        return (
            self.embedding is None
            or self.embedding_version != self.content_version
            or self.embedding_signature != current_job_embedding_signature()
        )


class JDImport(UUIDModel, TimeStampedModel):
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
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    # Giới hạn retry để bảo vệ quota Gemini.
    parse_attempts = models.PositiveSmallIntegerField(default=0)
    parsed_data = models.JSONField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = "jd_imports"
        indexes = [
            models.Index(
                fields=["created_by", "status"],
                name="jd_imports_created_7f3574_idx",
            )
        ]


class JobSkill(UUIDModel, TimeStampedModel):
    job = models.ForeignKey(JobPost, on_delete=models.CASCADE, related_name="job_skills")
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="job_links")
    is_required = models.BooleanField(default=True, help_text="False = 'nice to have'")

    class Meta:
        db_table = "job_skills"
        constraints = [
            models.UniqueConstraint(fields=["job", "skill"], name="uniq_job_skill"),
        ]

    def __str__(self):
        return f"{self.job.title} - {self.skill.name}"
