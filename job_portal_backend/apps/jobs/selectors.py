"""jobs selectors — read-only query logic (no writes, no business mutation)."""
from django.db.models import Case, Count, ExpressionWrapper, F, FloatField, Q, Value, When
from django.utils import timezone
from pgvector.django import CosineDistance

from apps.candidates.models import CandidateProfile
from apps.companies.models import Company
from integrations.gemini.embeddings import (
    current_candidate_embedding_signature,
    current_job_embedding_signature,
)
from apps.jobs.models import JobPost


def is_public_job(job: JobPost) -> bool:
    """Kiểm tra một tin có đang hiển thị hợp lệ cho public hay không."""
    return bool(
        job.is_active
        and job.status == JobPost.Status.ACTIVE
        and job.company.status == Company.Status.APPROVED
        and (job.expires_at is None or job.expires_at > timezone.now())
    )


def get_active_jobs():
    """Chỉ trả tin ACTIVE, chưa hết hạn và thuộc công ty APPROVED."""
    return (
        JobPost.objects.filter(
            status=JobPost.Status.ACTIVE,
            company__status=Company.Status.APPROVED,
            is_active=True,
        )
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()))
        .select_related("company")
        .prefetch_related("job_skills__skill")
        .order_by("-created_at", "-pk")
    )


def filter_active_jobs(
    job_type=None,
    location=None,
    experience_level=None,
    salary_min=None,
):
    """Apply public eligibility and UC-03 hard filters before keyword search."""
    qs = get_active_jobs()
    if job_type:
        qs = qs.filter(job_type=job_type)
    if location:
        qs = qs.filter(location__icontains=location)
    if experience_level:
        qs = qs.filter(experience_level=experience_level)
    if salary_min is not None:
        qs = qs.filter(Q(salary_max__gte=salary_min) | Q(salary_negotiable=True))
    return qs


def rank_jobs_by_query_embedding(queryset, query_embedding):
    """Rank only current vectors by cosine similarity as specified by UC-03."""
    distance = CosineDistance("embedding", query_embedding)
    return (
        queryset.filter(
            embedding__isnull=False,
            embedding_version=F("content_version"),
            embedding_signature=current_job_embedding_signature(),
        )
        .annotate(_semantic_distance=distance)
        .annotate(
            match_score=ExpressionWrapper(
                (Value(1.0) - F("_semantic_distance")) * Value(100.0),
                output_field=FloatField(),
            )
        )
        .order_by("_semantic_distance", "-created_at", "-pk")
    )


def fallback_keyword_search(queryset, keyword):
    """UC-03 E2 lexical fallback over the already hard-filtered job set."""
    return queryset.filter(
        Q(title__icontains=keyword)
        | Q(description__icontains=keyword)
        | Q(requirements__icontains=keyword)
        | Q(benefits__icontains=keyword)
        | Q(company__name__icontains=keyword)
        | Q(job_skills__skill__name__icontains=keyword)
    ).distinct().order_by("-created_at", "-pk")


def get_employer_jobs(user):
    """Tin tuyển dụng thuộc employer (đăng hoặc qua công ty của họ)."""
    return JobPost.objects.filter(
        Q(created_by=user) | Q(company__owner=user),
        is_active=True,
    ).annotate(
        application_count=Count("applications", distinct=True),
    ).select_related("company").prefetch_related("job_skills__skill").order_by("-created_at")


def get_job_detail_queryset(user):
    """Public chỉ thấy tin mở; owner/admin vẫn xem được trạng thái nội bộ."""
    public_filter = (
        Q(status=JobPost.Status.ACTIVE)
        & Q(company__status=Company.Status.APPROVED)
        & (Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()))
    )
    qs = JobPost.objects.filter(is_active=True)
    if user and user.is_authenticated:
        if user.is_admin_role:
            pass
        elif user.is_employer:
            qs = qs.filter(
                public_filter | Q(created_by=user) | Q(company__owner=user)
            )
        else:
            qs = qs.filter(public_filter)
    else:
        qs = qs.filter(public_filter)
    return qs.select_related("company").prefetch_related("job_skills__skill")


def get_manageable_jobs(user):
    """Giới hạn object quản trị theo owner; admin được truy cập toàn bộ."""
    qs = JobPost.objects.filter(is_active=True)
    if not user.is_admin_role:
        qs = qs.filter(Q(created_by=user) | Q(company__owner=user))
    return qs.select_related("company").prefetch_related("job_skills__skill")


def get_recommended_jobs(profile: CandidateProfile):
    """Rank eligible jobs by cosine score, leaving unavailable scores null."""
    queryset = get_active_jobs()
    if profile.embedding is None or profile.embedding_is_stale:
        return queryset.annotate(
            match_score=Value(None, output_field=FloatField())
        ).order_by("-created_at", "-pk")
    cosine_score = ExpressionWrapper(
        (Value(1.0) - CosineDistance("embedding", profile.embedding)) * Value(100.0),
        output_field=FloatField(),
    )
    return queryset.annotate(
        match_score=Case(
            When(
                embedding__isnull=False,
                embedding_version=F("content_version"),
                embedding_signature=current_job_embedding_signature(),
                then=cosine_score,
            ),
            default=Value(None),
            output_field=FloatField(),
        )
    ).order_by(
        F("match_score").desc(nulls_last=True), "-created_at", "-pk"
    )


def get_recommended_candidates(job: JobPost):
    """Rank active public candidate profiles without loading private fields."""
    queryset = CandidateProfile.objects.filter(
        is_active=True,
        is_public=True,
        user__is_active=True,
    ).prefetch_related("candidate_skills__skill")
    if job.embedding is None or job.embedding_is_stale:
        return queryset.annotate(
            match_score=Value(None, output_field=FloatField())
        ).order_by("-updated_at", "-pk")
    cosine_score = ExpressionWrapper(
        (Value(1.0) - CosineDistance("embedding", job.embedding)) * Value(100.0),
        output_field=FloatField(),
    )
    return queryset.annotate(
        match_score=Case(
            When(
                embedding__isnull=False,
                embedding_version=F("profile_version"),
                embedding_signature=current_candidate_embedding_signature(),
                then=cosine_score,
            ),
            default=Value(None),
            output_field=FloatField(),
        )
    ).order_by(
        F("match_score").desc(nulls_last=True), "-updated_at", "-pk"
    )
