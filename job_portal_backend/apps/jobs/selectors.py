from django.db.models import Case, Count, ExpressionWrapper, F, FloatField, Q, Value, When
from django.db.models.functions import Greatest, Least, Round
from django.utils import timezone
from pgvector.django import CosineDistance

from apps.candidates.models import CandidateProfile, DEGREE_LEVEL_RANK, DegreeLevel
from apps.companies.models import Company
from apps.core.matching import (
    education_score,
    experience_score,
    total_experience_years,
)
from integrations.gemini.embeddings import (
    current_candidate_embedding_signature,
    current_job_embedding_signature,
)
from apps.jobs.models import JobPost
from apps.skills.selectors import get_active_matching_weights


MIN_SEMANTIC_SIMILARITY = 0.67


def is_public_job(job: JobPost) -> bool:
    return bool(
        job.status == JobPost.Status.ACTIVE
        and job.company.status == Company.Status.APPROVED
        and (job.expires_at is None or job.expires_at > timezone.now())
    )


def get_active_jobs():
    return (
        JobPost.objects.filter(
            status=JobPost.Status.ACTIVE,
            company__status=Company.Status.APPROVED,
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


def jobs_with_current_embeddings(queryset):
    return queryset.filter(
        embedding__isnull=False,
        embedding_version=F("content_version"),
        embedding_signature=current_job_embedding_signature(),
    )


def _semantic_similarity(cosine_distance):
    return Greatest(
        Value(0.0),
        ExpressionWrapper(
            Value(1.0) - cosine_distance,
            output_field=FloatField(),
        ),
    )


def rank_jobs_by_query_embedding(queryset, query_embedding):
    distance = CosineDistance("embedding", query_embedding)
    return (
        jobs_with_current_embeddings(queryset)
        .annotate(_semantic_distance=distance)
        .annotate(
            semantic_score=_semantic_similarity(F("_semantic_distance")),
        )
        .filter(semantic_score__gt=MIN_SEMANTIC_SIMILARITY)
        .order_by("-semantic_score", "-created_at", "-pk")
    )


def basic_keyword_search(queryset, keyword):
    for term in keyword.split():
        queryset = queryset.filter(
            Q(title__icontains=term)
            | Q(description__icontains=term)
            | Q(requirements__icontains=term)
            | Q(benefits__icontains=term)
            | Q(company__name__icontains=term)
            | Q(job_skills__skill__name__icontains=term)
        )
    return queryset.distinct().order_by("-created_at", "-pk")


def get_employer_jobs(user):
    return JobPost.objects.filter(
        Q(created_by=user) | Q(company__owner=user),
    ).annotate(
        application_count=Count("applications", distinct=True),
    ).select_related("company").prefetch_related("job_skills__skill").order_by("-created_at")


def get_job_detail_queryset(user):
    """Chỉ owner và admin thấy trạng thái nội bộ của tin."""
    public_filter = (
        Q(status=JobPost.Status.ACTIVE)
        & Q(company__status=Company.Status.APPROVED)
        & (Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()))
    )
    qs = JobPost.objects.all()
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
    """Scope thao tác quản trị theo owner, trừ admin."""
    qs = JobPost.objects.all()
    if not user.is_admin_role:
        qs = qs.filter(Q(created_by=user) | Q(company__owner=user))
    return qs.select_related("company").prefetch_related("job_skills__skill")


def _score_case(scores, default=0.0):
    return Case(
        *(When(pk=pk, then=Value(score)) for pk, score in scores.items()),
        default=Value(default),
        output_field=FloatField(),
    )


def _weighted_recommendations(queryset, semantic_score, semantic_available, weights):
    numerator = (
        F("semantic_score") * Value(float(weights.semantic))
        + F("skill_score") * Value(float(weights.skill))
        + F("experience_score") * Value(float(weights.experience))
        + F("education_score") * Value(float(weights.education))
    )
    denominator = (
        Case(When(semantic_available, then=Value(float(weights.semantic))), default=Value(0.0))
        + Case(When(_job_skill_count__gt=0, then=Value(float(weights.skill))), default=Value(0.0))
        + Case(When(experience_level__gt="", then=Value(float(weights.experience))), default=Value(0.0))
        + Case(
            When(
                required_education_level__isnull=False,
                then=Case(
                    When(required_education_level=DegreeLevel.NONE, then=Value(0.0)),
                    default=Value(float(weights.education)),
                ),
            ),
            default=Value(0.0),
        )
    )
    return queryset.annotate(
        semantic_score=Case(
            When(semantic_available, then=semantic_score),
            default=Value(None),
            output_field=FloatField(),
        ),
        _applied_weight=ExpressionWrapper(denominator, output_field=FloatField()),
    ).annotate(
        match_score=Case(
            When(
                _applied_weight__gt=0,
                then=Round(
                    Least(Value(100.0), Greatest(Value(0.0), numerator / F("_applied_weight"))),
                    2,
                ),
            ),
            default=Value(None),
            output_field=FloatField(),
        )
    )


def get_recommended_jobs(profile: CandidateProfile):
    queryset = get_active_jobs()
    if profile.embedding is None or profile.embedding_is_stale:
        return queryset.annotate(
            match_score=Value(None, output_field=FloatField())
        ).order_by("-created_at", "-pk")
    weights = get_active_matching_weights()
    if weights is None:
        return queryset.annotate(
            match_score=Value(None, output_field=FloatField())
        ).order_by("-created_at", "-pk")

    intervals = profile.experiences.values_list("start_date", "end_date", "is_current")
    total_years = total_experience_years(intervals, timezone.localdate())
    verified_levels = profile.educations.filter(
        is_completed=True,
        is_verified=True,
        degree_level__isnull=False,
    ).values_list("degree_level", flat=True)
    highest_degree = max(verified_levels, key=DEGREE_LEVEL_RANK.get, default=None)
    education_scores = {}
    experience_scores = {}
    for job_id, required_degree, level in queryset.values_list(
        "pk", "required_education_level", "experience_level"
    ):
        edu_score = education_score(highest_degree, required_degree)
        education_scores[job_id] = 0.0 if edu_score is None else edu_score * 100.0
        experience_scores[job_id] = (
            experience_score(total_years, level) * 100.0 if level else 0.0
        )

    profile_skill_ids = profile.candidate_skills.filter(
        skill__is_active=True,
        skill__status__in=("APPROVED", "PENDING"),
    ).values("skill_id")
    valid_job_skill = Q(
        job_skills__skill__is_active=True,
        job_skills__skill__status__in=("APPROVED", "PENDING"),
    )
    queryset = queryset.annotate(
        _required_skill_count=Count(
            "job_skills",
            filter=valid_job_skill & Q(job_skills__is_required=True),
            distinct=True,
        ),
        _preferred_skill_count=Count(
            "job_skills",
            filter=valid_job_skill & Q(job_skills__is_required=False),
            distinct=True,
        ),
        _matched_required_count=Count(
            "job_skills",
            filter=valid_job_skill & Q(
                job_skills__is_required=True,
                job_skills__skill_id__in=profile_skill_ids,
            ),
            distinct=True,
        ),
        _matched_preferred_count=Count(
            "job_skills",
            filter=valid_job_skill & Q(
                job_skills__is_required=False,
                job_skills__skill_id__in=profile_skill_ids,
            ),
            distinct=True,
        ),
    ).annotate(
        _job_skill_count=F("_required_skill_count") + F("_preferred_skill_count"),
        skill_score=Case(
            When(_job_skill_count=0, then=Value(0.0)),
            default=(
                (F("_matched_required_count") * Value(float(weights.required_skill_multiplier)) + F("_matched_preferred_count"))
                * Value(100.0)
                / (F("_required_skill_count") * Value(float(weights.required_skill_multiplier)) + F("_preferred_skill_count"))
            ),
            output_field=FloatField(),
        ),
        experience_score=_score_case(experience_scores),
        education_score=_score_case(education_scores),
    )
    semantic_score = ExpressionWrapper(
        _semantic_similarity(
            CosineDistance("embedding", profile.embedding),
        ) * Value(100.0),
        output_field=FloatField(),
    )
    queryset = _weighted_recommendations(
        queryset,
        semantic_score,
        Q(
            embedding__isnull=False,
            embedding_version=F("content_version"),
            embedding_signature=current_job_embedding_signature(),
        ),
        weights,
    )
    return queryset.order_by(
        F("match_score").desc(nulls_last=True), "-created_at", "-pk"
    )


def get_recommended_candidates(job: JobPost):
    """Chiều employer-to-candidate chỉ dùng cosine, không dùng trọng số."""
    queryset = CandidateProfile.objects.filter(
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
    semantic_score = ExpressionWrapper(
        _semantic_similarity(
            CosineDistance("embedding", job.embedding),
        ) * Value(100.0),
        output_field=FloatField(),
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
