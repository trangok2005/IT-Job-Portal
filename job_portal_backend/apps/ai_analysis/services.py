"""Write operations for persisted application match results."""
from django.db import transaction
from decimal import Decimal

from apps.ai_analysis.models import ApplicationMatchResult
from apps.applications.models import JobApplication


@transaction.atomic
def save_match_result(
    application,
    match_score,
    semantic_similarity_score,
    skill_overlap_score,
    experience_score,
    education_score,
    matched_skills,
    missing_skills,
    embedding_model_version,
    status=ApplicationMatchResult.Status.COMPLETED,
    criteria_applicability=None,
    original_weights=None,
    normalized_weights=None,
    missing_information=None,
    rule_version="matching-v2.2.4",
    embedding_metadata=None,
) -> ApplicationMatchResult:
    """Create once; retries return the successful immutable result unchanged."""
    application = (
        JobApplication.objects.select_for_update()
        .select_related("candidate", "job")
        .get(pk=application.pk)
    )
    existing = ApplicationMatchResult.objects.filter(application=application).first()
    if existing is not None:
        return existing
    return ApplicationMatchResult.objects.create(
        application=application,
        match_score=match_score,
        status=status,
        semantic_similarity_score=(
            None if semantic_similarity_score is None else Decimal(str(semantic_similarity_score))
        ),
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
        embedding_model_version=embedding_model_version,
        criteria_applicability=criteria_applicability or {},
        original_weights=original_weights or {},
        normalized_weights=normalized_weights or {},
        missing_information=missing_information or {},
        rule_version=rule_version,
        embedding_metadata=embedding_metadata or {},
    )
