"""Write operations cho kết quả phân tích AI của application."""
from django.db import transaction
from django.utils import timezone

from apps.ai_analysis.models import AIAnalysis
from apps.applications.models import JobApplication


@transaction.atomic
def save_match_analysis(
    application,
    match_score,
    skill_overlap_score,
    matched_skills,
    missing_skills,
    weight_config,
    embedding_model_version,
) -> AIAnalysis:
    """Upsert điểm và snapshot version embedding dùng trong lần tính hiện tại."""
    application = (
        JobApplication.objects.select_for_update()
        .select_related("candidate", "job")
        .get(pk=application.pk)
    )
    analysis, _ = AIAnalysis.objects.update_or_create(
        application=application,
        defaults={
            "match_score": match_score,
            "semantic_similarity_score": match_score,
            "skill_overlap_score": skill_overlap_score,
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "weight_config": weight_config,
            "embedding_model_version": embedding_model_version,
            "candidate_embedding_version": application.candidate.embedding_version,
            "job_embedding_version": application.job.embedding_version,
            "computed_at": timezone.now(),
        },
    )
    return analysis
