"""Write operations cho kết quả phân tích AI của application."""
from django.db import transaction
from decimal import Decimal

from apps.ai_analysis.models import AIAnalysis
from apps.applications.models import JobApplication


@transaction.atomic
def save_match_analysis(
    application,
    match_score,
    semantic_similarity_score,
    skill_overlap_score,
    experience_score,
    education_score,
    matched_skills,
    missing_skills,
    weight_config,
    embedding_model_version,
    candidate_embedding_version,
    job_embedding_version,
) -> AIAnalysis:
    """Create once; retries return the successful immutable result unchanged."""
    application = (
        JobApplication.objects.select_for_update()
        .select_related("candidate", "job")
        .get(pk=application.pk)
    )
    existing = AIAnalysis.objects.filter(application=application).first()
    if existing is not None:
        return existing
    return AIAnalysis.objects.create(
        application=application,
        match_score=match_score,
        semantic_similarity_score=Decimal(str(semantic_similarity_score)),
        skill_overlap_score=(
            None if skill_overlap_score is None else Decimal(str(skill_overlap_score))
        ),
        experience_score=(
            None if experience_score is None else Decimal(str(experience_score))
        ),
        education_score=(
            None if education_score is None else Decimal(str(education_score))
        ),
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        weight_config=weight_config,
        embedding_model_version=embedding_model_version,
        candidate_embedding_version=candidate_embedding_version,
        job_embedding_version=job_embedding_version,
    )
