"""jobs selectors — read-only query logic (no writes, no business mutation)."""
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db.models import Case, Count, Exists, ExpressionWrapper, F, FloatField, OuterRef, Q, Value, When
from django.db.models.functions import Greatest, Least, Round
from django.utils import timezone
from pgvector.django import CosineDistance

from apps.candidates.models import CandidateProfile
from apps.companies.models import Company
from apps.core.matching import (
    experience_score,
    recognized_degree_level,
    required_degree_level,
    total_experience_years,
)
from integrations.gemini.embeddings import (
    current_candidate_embedding_signature,
    current_job_embedding_signature,
)
from apps.jobs.models import JobPost, JobSkill
from apps.skills.selectors import get_active_matching_weights


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
    workplace_type=None,
    job_type=None,
    location=None,
    experience_level=None,
    salary_min=None,
):
    """Apply public eligibility and UC-03 hard filters before keyword search."""
    qs = get_active_jobs()
    if workplace_type:
        qs = qs.filter(workplace_type=workplace_type)
    if job_type:
        qs = qs.filter(job_type=job_type)
    if location:
        qs = qs.filter(location=location)
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
    """PostgreSQL FTS fallback over the already hard-filtered job set."""
    query = SearchQuery(keyword, config="simple", search_type="websearch")
    vector = (
        SearchVector("title", config="simple", weight="A")
        + SearchVector("description", config="simple", weight="B")
        + SearchVector("requirements", config="simple", weight="B")
        + SearchVector("benefits", config="simple", weight="C")
        + SearchVector("company__name", config="simple", weight="C")
    )
    matching_skill = (
        JobSkill.objects.filter(job_id=OuterRef("pk"))
        .annotate(_skill_search=SearchVector("skill__name", config="simple"))
        .filter(_skill_search=query)
    )
    return (
        queryset.annotate(
            _search_vector=vector,
            _search_rank=SearchRank(vector, query),
            _skill_match=Exists(matching_skill),
        )
        .filter(Q(_search_vector=query) | Q(_skill_match=True))
        .order_by("-_search_rank", "-created_at", "-pk")
    )


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


def _score_case(scores, default=0.0):
    return Case(
        *(When(pk=pk, then=Value(score)) for pk, score in scores.items()),
        default=Value(default),
        output_field=FloatField(),
    )


def _weighted_recommendations(queryset, semantic_score, semantic_available):
    weights = get_active_matching_weights()
    weighted_score = (
        F("semantic_score") * Value(float(weights.semantic))
        + F("skill_score") * Value(float(weights.skill))
        + F("experience_score") * Value(float(weights.experience))
        + F("education_score") * Value(float(weights.education))
    )
    return queryset.annotate(
        semantic_score=Case(
            When(semantic_available, then=semantic_score),
            default=Value(None),
            output_field=FloatField(),
        )
    ).annotate(
        match_score=Case(
            When(
                semantic_score__isnull=False,
                then=Round(Least(Value(100.0), Greatest(Value(0.0), weighted_score)), 2),
            ),
            default=Value(None),
            output_field=FloatField(),
        )
    )


def get_recommended_jobs(profile: CandidateProfile):
    """Rank all eligible jobs by the active four-component configuration."""
    queryset = get_active_jobs()
    if profile.embedding is None or profile.embedding_is_stale:
        return queryset.annotate(
            match_score=Value(None, output_field=FloatField())
        ).order_by("-created_at", "-pk")

    intervals = profile.experiences.values_list("start_date", "end_date", "is_current")
    total_years = total_experience_years(intervals, timezone.localdate())
    highest_degree = max(
        (recognized_degree_level(value) for value in profile.educations.values_list("degree", flat=True)),
        default=0,
    )
    education_scores = {}
    experience_scores = {}
    for job_id, requirements, level in queryset.values_list("pk", "requirements", "experience_level"):
        required_degree = required_degree_level(requirements)
        education_scores[job_id] = 100.0 if not required_degree or highest_degree >= required_degree else 0.0
        experience_scores[job_id] = experience_score(total_years, level)

    profile_skill_ids = profile.candidate_skills.values("skill_id")
    queryset = queryset.annotate(
        _job_skill_count=Count("job_skills", distinct=True),
        _matched_skill_count=Count(
            "job_skills",
            filter=Q(job_skills__skill_id__in=profile_skill_ids),
            distinct=True,
        ),
    ).annotate(
        skill_score=Case(
            When(_job_skill_count=0, then=Value(100.0)),
            default=F("_matched_skill_count") * Value(100.0) / F("_job_skill_count"),
            output_field=FloatField(),
        ),
        experience_score=_score_case(experience_scores),
        education_score=_score_case(education_scores),
    )
    semantic_score = Least(
        Value(100.0),
        Greatest(
            Value(0.0),
            ExpressionWrapper(
                (Value(1.0) - CosineDistance("embedding", profile.embedding)) * Value(100.0),
                output_field=FloatField(),
            ),
        ),
    )
    queryset = _weighted_recommendations(
        queryset,
        semantic_score,
        Q(
            embedding__isnull=False,
            embedding_version=F("content_version"),
            embedding_signature=current_job_embedding_signature(),
        ),
    )
    return queryset.order_by(
        F("match_score").desc(nulls_last=True), "-created_at", "-pk"
    )


def get_recommended_candidates(job: JobPost):
    """Rank active public candidate profiles by pure cosine similarity.

    Trọng số MatchingWeightConfig chỉ áp dụng cho chiều candidate -> jobs
    và điểm chấm hồ sơ ứng tuyển (AIAnalysis); gợi ý ứng viên cho NTD
    giữ nguyên semantic thuần.
    """
    queryset = CandidateProfile.objects.filter(
        is_active=True,
        is_public=True,
        user__is_active=True,
    )
    if job.embedding is None or job.embedding_is_stale:
        return queryset.annotate(
            match_score=Value(None, output_field=FloatField())
        ).order_by("-updated_at", "-pk")

    semantic_available = Q(
        embedding__isnull=False,
        embedding_version=F("profile_version"),
        embedding_signature=current_candidate_embedding_signature(),
    )
    semantic_score = Least(
        Value(100.0),
        Greatest(
            Value(0.0),
            ExpressionWrapper(
                (Value(1.0) - CosineDistance("embedding", job.embedding)) * Value(100.0),
                output_field=FloatField(),
            ),
        ),
    )
    queryset = queryset.annotate(
        match_score=Case(
            When(semantic_available, then=Round(semantic_score, 2)),
            default=Value(None),
            output_field=FloatField(),
        )
    ).prefetch_related("candidate_skills__skill")
    return queryset.order_by(
        F("match_score").desc(nulls_last=True), "-updated_at", "-pk"
    )
