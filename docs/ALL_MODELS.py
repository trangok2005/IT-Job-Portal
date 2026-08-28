"""
ALL_MODELS.py — Tổng hợp toàn bộ Model trong IT-Job-Portal
===============================================
Tổng: 21 class (18 bảng concrete + 3 abstract base)
Dùng để vẽ ERD + UML Class Diagram.

Cấu trúc file:
  A. Abstract Base Classes (apps/core/models.py)
  B. accounts  — User
  C. companies — Company
  D. skills    — SkillCategory, Skill, SkillAlias, CandidateSkill, MatchingWeightConfig
  E. candidates — CandidateProfile, Education, Experience, ResumeImport, Resume
  F. jobs      — JobPost, JDImport, JobSkill
  G. applications — JobApplication, ApplicationStatusHistory
  H. ai_analysis — AIAnalysis
"""

# ============================================================
# A. ABSTRACT BASE CLASSES  (apps/core/models.py)
# ============================================================

import uuid
from django.db import models


class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class BaseModel(UUIDModel, TimeStampedModel):
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True


# ============================================================
# B. ACCOUNTS  (apps/accounts/models.py)
# ============================================================

from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """
    Bang: users
    Email la login identifier; Google OAuth (sub claim).
    """

    class Role(models.TextChoices):
        CANDIDATE = "CANDIDATE", "Ung vien"
        EMPLOYER  = "EMPLOYER",  "Nha tuyen dung"
        ADMIN     = "ADMIN",     "Admin"

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email       = models.EmailField(unique=True)
    role        = models.CharField(max_length=20, choices=Role.choices, default=Role.CANDIDATE)

    # Google OAuth
    google_sub  = models.CharField(max_length=255, unique=True, null=True, blank=True)
    auth_provider = models.CharField(
        max_length=20,
        choices=[("PASSWORD", "Password"), ("GOOGLE", "Google OAuth")],
        default="PASSWORD",
    )

    # is_active tai su dung tu AbstractUser ("Ung vien da xoa / khoa tai khoan")
    phone         = models.CharField(max_length=20, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    USERNAME_FIELD  = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        db_table = "users"
        indexes = [
            models.Index(fields=["role"]),
            models.Index(fields=["email"]),
        ]


# ============================================================
# C. COMPANIES  (apps/companies/models.py)
# ============================================================


class Company(UUIDModel, TimeStampedModel):
    """
    Bang: companies
    1 employer = 1 company (UniqueConstraint owner).
    """

    class Status(models.TextChoices):
        PENDING  = "PENDING",  "Cho duyet"
        APPROVED = "APPROVED", "Da duyet"
        REJECTED = "REJECTED", "Tu choi"
        LOCKED   = "LOCKED",   "Bi khoa"

    owner   = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE,
        related_name="owned_companies",
        limit_choices_to={"role": "EMPLOYER"},
    )
    name           = models.CharField(max_length=255)
    tax_code       = models.CharField(max_length=50, unique=True, null=True, blank=True)
    description    = models.TextField(blank=True)
    website        = models.URLField(blank=True)
    address        = models.CharField(max_length=500, blank=True)
    company_size   = models.CharField(max_length=50, blank=True)
    industry       = models.CharField(max_length=150, blank=True)
    status         = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    # Admin approval trail
    reviewed_by    = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reviewed_companies",
        limit_choices_to={"role": "ADMIN"},
    )
    reviewed_at      = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    class Meta:
        db_table = "companies"
        indexes = [models.Index(fields=["status"])]
        constraints = [
            models.UniqueConstraint(fields=["owner"], name="unique_company_owner"),
        ]


# ============================================================
# D. SKILLS  (apps/skills/models.py)
# ============================================================


class SkillCategory(UUIDModel):
    """
    Bang: skill_categories
    18 category (programming, frontend, backend, database, devops, ...)
    """
    name = models.CharField(max_length=150, unique=True)

    class Meta:
        db_table = "skill_categories"


class Skill(BaseModel):
    """
    Bang: skills
    Skill chuan hoa trong taxonomy (416 skill).
    Status: PENDING -> APPROVED / REJECTED / MERGED.
    merged_into: FK self — gop skill trung (giu audit trail).
    """
    MAX_NAME_LEN = 150

    class Status(models.TextChoices):
        PENDING  = "PENDING",  "Cho duyet"
        APPROVED = "APPROVED", "Da duyet"
        REJECTED = "REJECTED", "Tu choi"
        MERGED   = "MERGED",   "Da gop vao skill khac"

    class Source(models.TextChoices):
        CV_PARSING   = "CV_PARSING",   "AI phat hien khi doc CV"
        JD_PARSING   = "JD_PARSING",   "AI phat hien khi doc JD"
        ADMIN_MANUAL = "ADMIN_MANUAL", "Admin tao tay"

    name     = models.CharField(max_length=150, unique=True)
    slug     = models.SlugField(max_length=170, unique=True)
    category = models.ForeignKey(
        SkillCategory, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="skills",
    )
    is_active = models.BooleanField(default=True)
    status    = models.CharField(max_length=20, choices=Status.choices, default=Status.APPROVED)
    source    = models.CharField(max_length=20, choices=Source.choices, default=Source.ADMIN_MANUAL)

    # Merge trail (self-referencing)
    merged_into = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="merged_from",
    )

    # Audit trail
    reviewed_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reviewed_skills",
        limit_choices_to={"role": "ADMIN"},
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "skills"
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["status"]),
        ]


class SkillAlias(UUIDModel):
    """
    Bang: skill_aliases
    Alias raw text -> Skill chuan hoa (e.g. 'ReactJS' -> 'React').
    normalized_text: lower-cased + accent-stripped, dung de fuzzy-match.
    """
    skill          = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="aliases")
    alias_text     = models.CharField(max_length=150, unique=True)
    normalized_text = models.CharField(max_length=150, unique=True)

    class Meta:
        db_table = "skill_aliases"


class MatchingWeightConfig(BaseModel):
    """
    Bang: matching_weight_configs
    Chi 1 config is_active=True tai 1 thoi diem.
    Weights tong = 1.0 (validate o serializer/service layer).
    """
    name      = models.CharField(max_length=150)
    is_active = models.BooleanField(default=False)

    weight_semantic_similarity = models.DecimalField(max_digits=4, decimal_places=3, default=0.600)
    weight_skill_overlap       = models.DecimalField(max_digits=4, decimal_places=3, default=0.250)
    weight_experience_match    = models.DecimalField(max_digits=4, decimal_places=3, default=0.100)
    weight_education_match     = models.DecimalField(max_digits=4, decimal_places=3, default=0.050)

    updated_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True,
        related_name="updated_weight_configs",
        limit_choices_to={"role": "ADMIN"},
    )

    class Meta:
        db_table = "matching_weight_configs"


class CandidateSkill(UUIDModel, TimeStampedModel):
    """
    Bang: candidate_skills
    Bang trung gian CandidateProfile <-> Skill.
    co the do AI trich xuat tu CV hoac ung vien tu them/sua.
    """
    class Level(models.TextChoices):
        BASIC       = "BASIC",       "Co ban"
        INTERMEDIATE = "INTERMEDIATE", "Trung binh"
        ADVANCED    = "ADVANCED",    "Nang cao"
        EXPERT      = "EXPERT",      "Chuyen gia"

    class Source(models.TextChoices):
        AI_EXTRACTED = "AI_EXTRACTED", "AI trich xuat tu CV"
        MANUAL       = "MANUAL",       "Ung vien tu them"

    candidate             = models.ForeignKey("candidates.CandidateProfile", on_delete=models.CASCADE, related_name="candidate_skills")
    skill                 = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="candidate_links")
    level                 = models.CharField(max_length=20, choices=Level.choices, blank=True)
    years_of_experience   = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    source                = models.CharField(max_length=20, choices=Source.choices, default=Source.MANUAL)

    class Meta:
        db_table = "candidate_skills"
        constraints = [
            models.UniqueConstraint(fields=["candidate", "skill"], name="uniq_candidate_skill"),
        ]


# ============================================================
# E. CANDIDATES  (apps/candidates/models.py)
# ============================================================

from pgvector.django import VectorField, HnswIndex

EMBEDDING_DIMENSIONS = 1536


class CandidateProfile(BaseModel):
    """
    Bang: candidate_profiles
    Embedding vector (pgvector) dung cho semantic search (UC-03)
    va match score (UC-04 / ai_analysis).
    """

    class Gender(models.TextChoices):
        MALE   = "MALE",   "Nam"
        FEMALE = "FEMALE", "Nu"
        OTHER  = "OTHER",  "Khac"

    user    = models.OneToOneField(
        "accounts.User", on_delete=models.CASCADE,
        related_name="candidate_profile",
        limit_choices_to={"role": "CANDIDATE"},
    )
    full_name  = models.CharField(max_length=255)
    phone      = models.CharField(max_length=20, blank=True)
    dob        = models.DateField(null=True, blank=True)
    gender     = models.CharField(max_length=10, choices=Gender.choices, blank=True)
    address    = models.CharField(max_length=500, blank=True)
    avatar_url = models.URLField(blank=True)
    headline   = models.CharField(max_length=255, blank=True)
    summary    = models.TextField(blank=True)
    desired_position   = models.CharField(max_length=255, blank=True)
    desired_salary_min = models.PositiveIntegerField(null=True, blank=True)
    is_public          = models.BooleanField(default=True)

    # Versioning + embedding
    profile_version      = models.PositiveIntegerField(default=1)
    embedding            = VectorField(dimensions=EMBEDDING_DIMENSIONS, null=True, blank=True)
    embedding_version    = models.PositiveIntegerField(default=0)
    embedding_updated_at = models.DateTimeField(null=True, blank=True)
    embedding_signature  = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "candidate_profiles"
        indexes = [
            HnswIndex(
                name="candidate_embedding_hnsw",
                fields=["embedding"],
                m=16, ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ]


class Education(UUIDModel, TimeStampedModel):
    """
    Bang: candidate_educations
    co the duoc AI trich xuat tu CV (AI_EXTRACTED) hoac nhap tay (MANUAL).
    """
    candidate    = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name="educations")
    school_name  = models.CharField(max_length=255)
    major        = models.CharField(max_length=255, blank=True)
    degree       = models.CharField(max_length=150, blank=True)
    start_date   = models.DateField(null=True, blank=True)
    end_date     = models.DateField(null=True, blank=True)
    description  = models.TextField(blank=True)
    source       = models.CharField(
        max_length=20,
        choices=[("AI_EXTRACTED", "AI trich xuat"), ("MANUAL", "Nhap tay")],
        default="MANUAL",
    )

    class Meta:
        db_table = "candidate_educations"
        ordering = ["-end_date"]


class Experience(UUIDModel, TimeStampedModel):
    """
    Bang: candidate_experiences
    """
    candidate    = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name="experiences")
    company_name = models.CharField(max_length=255)
    position     = models.CharField(max_length=255)
    start_date   = models.DateField(null=True, blank=True)
    end_date     = models.DateField(null=True, blank=True)
    is_current   = models.BooleanField(default=False)
    description  = models.TextField(blank=True)
    source       = models.CharField(
        max_length=20,
        choices=[("AI_EXTRACTED", "AI trich xuat"), ("MANUAL", "Nhap tay")],
        default="MANUAL",
    )

    class Meta:
        db_table = "candidate_experiences"
        ordering = ["-end_date"]


class ResumeImport(UUIDModel, TimeStampedModel):
    """
    Bang: resume_imports
    Luong tam: upload CV -> AI parse -> preview -> user confirm (UC-01).
    Tu het han sau 24h neu khong duoc consume.
    """
    class ParseStatus(models.TextChoices):
        PENDING  = "PENDING",  "Dang xu ly"
        SUCCESS  = "SUCCESS",  "Thanh cong"
        FAILED   = "FAILED",   "That bai"
        CONSUMED = "CONSUMED", "Da dung de cap nhat ho so"

    candidate           = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name="resume_imports")
    file                = models.FileField(upload_to="resume_imports/%Y/%m/")
    original_filename   = models.CharField(max_length=255)
    file_size_bytes     = models.PositiveIntegerField(null=True, blank=True)
    parse_status        = models.CharField(max_length=20, choices=ParseStatus.choices, default=ParseStatus.PENDING)
    parse_attempts      = models.PositiveSmallIntegerField(default=0)   # max 3
    parsed_data         = models.JSONField(null=True, blank=True)
    parse_error_message = models.TextField(blank=True)
    expires_at          = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "resume_imports"
        ordering = ["-created_at"]


class Resume(UUIDModel, TimeStampedModel):
    """
    Bang: resumes
    CV chinh thuc da user xac nhan (is_primary=True).
    """
    class ParseStatus(models.TextChoices):
        PENDING = "PENDING", "Dang xu ly"
        SUCCESS = "SUCCESS", "Thanh cong"
        FAILED  = "FAILED",  "That bai"
        SKIPPED = "SKIPPED", "Bo qua"

    candidate           = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name="resumes")
    file                = models.FileField(upload_to="resumes/%Y/%m/")
    original_filename   = models.CharField(max_length=255)
    file_size_bytes     = models.PositiveIntegerField(null=True, blank=True)
    parse_status        = models.CharField(max_length=20, choices=ParseStatus.choices, default=ParseStatus.PENDING)
    parsed_data         = models.JSONField(null=True, blank=True)
    is_primary          = models.BooleanField(default=True)

    class Meta:
        db_table = "resumes"
        constraints = [
            models.UniqueConstraint(
                fields=["candidate"],
                condition=models.Q(is_primary=True),
                name="unique_primary_resume_per_candidate",
            ),
        ]


# ============================================================
# F. JOBS  (apps/jobs/models.py)
# ============================================================


class JobPost(BaseModel):
    """
    Bang: job_posts
    Embedding vector tu JD dung cho semantic search / matching.
    Status: DRAFT -> ACTIVE -> CLOSED / EXPIRED (khong reversible).
    Hard-filter fields (location, workplace_type, job_type,
    experience_level, salary_min/max, salary_negotiable).
    """
    class Status(models.TextChoices):
        DRAFT   = "DRAFT",   "Nhap"
        ACTIVE  = "ACTIVE",  "Dang tuyen"
        CLOSED  = "CLOSED",  "Da dong"
        EXPIRED = "EXPIRED", "Het han"

    class JobType(models.TextChoices):
        FULL_TIME  = "FULL_TIME",  "Toan thoi gian"
        PART_TIME  = "PART_TIME",  "Ban thoi gian"
        CONTRACT   = "CONTRACT",   "Hop dong / Freelance"

    class WorkplaceType(models.TextChoices):
        ONSITE = "ONSITE", "Tai van phong"
        HYBRID = "HYBRID", "Linh hoat (Hybrid)"
        REMOTE = "REMOTE", "Tu xa (Remote)"

    class ExperienceLevel(models.TextChoices):
        ENTRY      = "ENTRY",      "Moi di lam (Intern / Fresher)"
        JUNIOR     = "JUNIOR",     "Junior (1 - 2 nam)"
        MID_SENIOR = "MID_SENIOR", "Middle - Senior (3+ nam)"
        LEAD       = "LEAD",       "Truong nhom / Quan ly"

    class Location(models.TextChoices):
        HO_CHI_MINH = "Hồ Chí Minh", "Hồ Chí Minh"
        HANOI       = "Hà Nội",      "Hà Nội"
        DA_NANG     = "Đà Nẵng",     "Đà Nẵng"

    company   = models.ForeignKey("companies.Company", on_delete=models.CASCADE, related_name="job_posts")
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True,
        related_name="created_job_posts",
        limit_choices_to={"role": "EMPLOYER"},
    )

    title           = models.CharField(max_length=255)
    description     = models.TextField()
    requirements    = models.TextField(blank=True)
    benefits        = models.TextField(blank=True)
    location        = models.CharField(max_length=20, choices=Location.choices, blank=True)
    workplace_type  = models.CharField(max_length=20, choices=WorkplaceType.choices, default=WorkplaceType.ONSITE)
    job_type        = models.CharField(max_length=20, choices=JobType.choices, default=JobType.FULL_TIME)
    experience_level = models.CharField(max_length=20, choices=ExperienceLevel.choices, blank=True)
    salary_min      = models.PositiveIntegerField(null=True, blank=True)
    salary_max      = models.PositiveIntegerField(null=True, blank=True)
    salary_negotiable = models.BooleanField(default=False)

    status       = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    published_at = models.DateTimeField(null=True, blank=True)
    expires_at   = models.DateTimeField(null=True, blank=True)

    required_skills = models.ManyToManyField("skills.Skill", through="JobSkill", related_name="job_posts")

    # Embedding
    content_version     = models.PositiveIntegerField(default=1)
    embedding           = VectorField(dimensions=EMBEDDING_DIMENSIONS, null=True, blank=True)
    embedding_version   = models.PositiveIntegerField(default=0)
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
                m=16, ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ]


class JDImport(UUIDModel, TimeStampedModel):
    """
    Bang: jd_imports
    Luong tam cho import JD tu file (giong ResumeImport o candidates).
    Tu het han sau 24h.
    """
    class Status(models.TextChoices):
        PENDING    = "PENDING",    "Dang cho"
        PROCESSING = "PROCESSING", "Dang phan tich"
        SUCCESS    = "SUCCESS",    "Hoan tat"
        FAILED     = "FAILED",     "That bai"
        CONSUMED   = "CONSUMED",   "Da tao tin"

    company       = models.ForeignKey("companies.Company", on_delete=models.CASCADE, related_name="jd_imports")
    created_by    = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="jd_imports")
    file          = models.FileField(upload_to="job_description_imports/%Y/%m/")
    original_filename = models.CharField(max_length=255)
    status        = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    parse_attempts    = models.PositiveSmallIntegerField(default=0)  # max 3
    parsed_data        = models.JSONField(null=True, blank=True)
    error_message      = models.TextField(blank=True)
    expires_at         = models.DateTimeField()

    class Meta:
        db_table = "jd_imports"
        indexes = [
            models.Index(fields=["created_by", "status"], name="jd_imports_created_7f3574_idx"),
        ]


class JobSkill(UUIDModel, TimeStampedModel):
    """
    Bang: job_skills
    Bang trung gian JobPost <-> Skill voi min_years.
    is_required: False = "nice to have".
    """
    job        = models.ForeignKey(JobPost, on_delete=models.CASCADE, related_name="job_skills")
    skill      = models.ForeignKey("skills.Skill", on_delete=models.CASCADE, related_name="job_links")
    is_required = models.BooleanField(default=True)
    min_years  = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)

    class Meta:
        db_table = "job_skills"
        constraints = [
            models.UniqueConstraint(fields=["job", "skill"], name="uniq_job_skill"),
        ]


# ============================================================
# G. APPLICATIONS  (apps/applications/models.py)
# ============================================================


class JobApplication(BaseModel):
    """
    Bang: job_applications
    State machine one-way, non-reversible (Project Charter):
        applied -> shortlisted -> interviewed -> hired
        applied -> rejected | shortlisted -> rejected | interviewed -> rejected
    hired/rejected = terminal.
    """
    class Status(models.TextChoices):
        APPLIED     = "APPLIED",     "Da ung tuyen"
        SHORTLISTED = "SHORTLISTED", "Da chon loc"
        INTERVIEWED = "INTERVIEWED", "Da phong van"
        REJECTED    = "REJECTED",    "Tu choi"
        HIRED       = "HIRED",       "Tuyen dung"

    VALID_TRANSITIONS = {
        Status.APPLIED:     {Status.SHORTLISTED, Status.REJECTED},
        Status.SHORTLISTED: {Status.INTERVIEWED, Status.REJECTED},
        Status.INTERVIEWED: {Status.HIRED,       Status.REJECTED},
        Status.HIRED:       set(),
        Status.REJECTED:    set(),
    }

    job       = models.ForeignKey("jobs.JobPost", on_delete=models.CASCADE, related_name="applications")
    candidate = models.ForeignKey("candidates.CandidateProfile", on_delete=models.CASCADE, related_name="applications")
    resume    = models.ForeignKey(
        "candidates.Resume", on_delete=models.RESTRICT, null=True,
        related_name="applications",
    )
    cover_letter       = models.TextField(blank=True)
    status             = models.CharField(max_length=20, choices=Status.choices, default=Status.APPLIED)

    class Meta:
        db_table = "job_applications"
        constraints = [
            models.UniqueConstraint(fields=["job", "candidate"], name="uniq_job_candidate_application"),
        ]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["job", "status"]),
        ]


class ApplicationStatusHistory(UUIDModel):
    """
    Bang: application_status_history
    Audit trail cho moi lan doi trang thai — phuc vu "Theo doi trang thai
    ung tuyen" (ung vien xem lich su) va truy vet Admin/NTD.
    """
    application = models.ForeignKey(JobApplication, on_delete=models.CASCADE, related_name="status_history")
    from_status = models.CharField(max_length=20, choices=JobApplication.Status.choices, blank=True)
    to_status   = models.CharField(max_length=20, choices=JobApplication.Status.choices)
    changed_by  = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True,
        related_name="application_status_changes",
    )
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "application_status_history"
        ordering = ["-created_at"]


# ============================================================
# H. AI_ANALYSIS  (apps/ai_analysis/models.py)
# ============================================================


class AIAnalysis(UUIDModel, TimeStampedModel):
    """
    Bang: ai_analyses
    Match Score da tinh san khi ung vien nop ho so (UC-04).
    Diem tong hop = trong so MatchingWeightConfig active x 4 thanh phan
    (semantic, skill overlap, experience, education).
    """
    application = models.OneToOneField(
        JobApplication, on_delete=models.CASCADE, related_name="ai_analysis",
    )

    match_score                  = models.DecimalField(max_digits=5, decimal_places=2)
    semantic_similarity_score    = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    skill_overlap_score          = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    experience_score             = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    education_score              = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    matched_skills = models.JSONField(default=list, blank=True)
    missing_skills = models.JSONField(default=list, blank=True)

    weight_config               = models.ForeignKey(MatchingWeightConfig, on_delete=models.SET_NULL, null=True, blank=True, related_name="analyses")
    embedding_model_version     = models.CharField(max_length=100, blank=True)
    candidate_embedding_version = models.PositiveIntegerField(default=0)
    job_embedding_version       = models.PositiveIntegerField(default=0)
    computed_at                 = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ai_analyses"
        indexes = [models.Index(fields=["match_score"])]


# ============================================================
# TONG KET
# ============================================================
#  18 bang concrete + 3 abstract base = 21 class
#
#  Bang (db_table):
#    users, companies, skill_categories, skills, skill_aliases,
#    matching_weight_configs, candidate_skills, candidate_profiles,
#    candidate_educations, candidate_experiences, resume_imports, resumes,
#    job_posts, jd_imports, job_skills, job_applications,
#    application_status_history, ai_analyses
#
#  Mối quan hệ chính:
#    User ─1:1─ CandidateProfile ─1:N─ Education, Experience, ResumeImport, Resume
#                            └─N:N─ Skill (qua CandidateSkill)
#    User ─1:1─ Company ─1:N─ JobPost ─M:N─ Skill (qua JobSkill)
#                            └─1:N─ JobApplication ─1:1─ AIAnalysis
#                                         └─1:N─ ApplicationStatusHistory
#    SkillCategory ─1:N─ Skill ─1:N─ SkillAlias
#    Skill ─N:1─ Skill (merged_into — self-referencing)
