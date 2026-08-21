"""Django-Q task tính match score cho hồ sơ ứng tuyển."""
import math
from decimal import Decimal

from apps.ai_analysis import services
from apps.applications.models import JobApplication
from apps.skills.selectors import get_active_weight_config
from integrations.gemini.embeddings import EMBEDDING_MODEL


def _cosine_similarity(left, right) -> float:
    """Tính cosine similarity thuần Python và xử lý vector zero an toàn."""
    dot_product = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot_product / (left_norm * right_norm)


def _ensure_embeddings(application: JobApplication) -> None:
    """Sinh đồng bộ embedding còn thiếu bên trong background worker hiện tại."""
    candidate = application.candidate
    job = application.job
    if candidate.embedding is None or candidate.embedding_is_stale:
        from apps.candidates.tasks import generate_candidate_embedding

        generate_candidate_embedding(str(candidate.pk), candidate.profile_version)
    if job.embedding is None or job.embedding_is_stale:
        from apps.jobs.tasks import generate_job_embedding

        generate_job_embedding(
            str(job.pk),
            job.content_version,
            allow_closed=True,
        )


def compute_application_match_score(application_id: str) -> bool:
    """Tính CosineSimilarity x 100 và lưu kết quả giải thích vào AIAnalysis."""
    application = (
        JobApplication.objects.select_related("candidate", "job")
        .prefetch_related(
            "candidate__candidate_skills",
            "job__job_skills",
        )
        .get(pk=application_id)
    )
    _ensure_embeddings(application)
    application.candidate.refresh_from_db()
    application.job.refresh_from_db()

    candidate_embedding = application.candidate.embedding
    job_embedding = application.job.embedding
    if candidate_embedding is None or job_embedding is None:
        raise RuntimeError("Embedding chưa sẵn sàng để tính match score.")

    similarity = _cosine_similarity(candidate_embedding, job_embedding)
    score = Decimal(str(round(max(0.0, min(1.0, similarity)) * 100, 2)))

    candidate_skill_ids = set(
        application.candidate.candidate_skills.values_list("skill_id", flat=True)
    )
    job_skills = list(application.job.job_skills.select_related("skill"))
    matched_skills = [
        job_skill.skill.name
        for job_skill in job_skills
        if job_skill.skill_id in candidate_skill_ids
    ]
    missing_skills = [
        job_skill.skill.name
        for job_skill in job_skills
        if job_skill.is_required and job_skill.skill_id not in candidate_skill_ids
    ]
    skill_overlap = None
    if job_skills:
        skill_overlap = Decimal(
            str(round(len(matched_skills) / len(job_skills) * 100, 2))
        )

    services.save_match_analysis(
        application=application,
        match_score=score,
        skill_overlap_score=skill_overlap,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        weight_config=get_active_weight_config(),
        embedding_model_version=EMBEDDING_MODEL,
    )
    return True
