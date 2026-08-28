"""Django-Q task tính match score từ snapshot bất biến của application."""
import math
from datetime import date
from decimal import Decimal

from apps.ai_analysis import services
from apps.ai_analysis.models import AIAnalysis
from apps.applications.models import JobApplication
from apps.core.matching import (
    experience_score,
    recognized_degree_level,
    required_degree_level,
    total_experience_years,
)
from apps.skills.models import MatchingWeightConfig
from integrations.gemini.embeddings import EMBEDDING_MODEL, embed_document


def _cosine_similarity(left, right) -> float:
    """Tính cosine similarity thuần Python và xử lý vector zero an toàn."""
    dot_product = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot_product / (left_norm * right_norm)


def _candidate_embedding(application: JobApplication):
    if application.candidate_embedding_snapshot is not None:
        return application.candidate_embedding_snapshot

    snapshot = application.profile_snapshot
    profile = application.candidate
    if (
        profile.embedding is not None
        and profile.embedding_version == snapshot["profile_version"]
        and profile.embedding_signature == snapshot["embedding_signature"]
    ):
        vector = list(profile.embedding)
    else:
        vector = embed_document(snapshot["embedding_text"])

    JobApplication.objects.filter(
        pk=application.pk,
        candidate_embedding_snapshot__isnull=True,
    ).update(candidate_embedding_snapshot=vector)
    application.refresh_from_db(fields=["candidate_embedding_snapshot"])
    return application.candidate_embedding_snapshot


def _job_embedding(application: JobApplication):
    if application.job_embedding_snapshot is not None:
        return application.job_embedding_snapshot

    snapshot = application.job_snapshot
    job = application.job
    if (
        job.embedding is not None
        and job.embedding_version == snapshot["content_version"]
        and job.embedding_signature == snapshot["embedding_signature"]
    ):
        vector = list(job.embedding)
    else:
        vector = embed_document(snapshot["embedding_text"])

    JobApplication.objects.filter(
        pk=application.pk,
        job_embedding_snapshot__isnull=True,
    ).update(job_embedding_snapshot=vector)
    application.refresh_from_db(fields=["job_embedding_snapshot"])
    return application.job_embedding_snapshot


def compute_application_match_score(application_id: str) -> bool:
    """Tạo duy nhất một kết quả từ input đã chụp lúc ứng tuyển."""
    if AIAnalysis.objects.filter(application_id=application_id).exists():
        return True

    application = (
        JobApplication.objects.select_related("candidate", "job")
        .get(pk=application_id)
    )
    if not all(
        (
            application.profile_snapshot,
            application.job_snapshot,
            application.matching_weight_snapshot,
            application.snapshot_created_at,
        )
    ):
        # Legacy applications predate immutable scoring snapshots and cannot be
        # reconstructed truthfully from the candidate's current profile.
        return False

    candidate_embedding = _candidate_embedding(application)
    job_embedding = _job_embedding(application)
    if candidate_embedding is None or job_embedding is None:
        raise RuntimeError("Embedding snapshot chưa sẵn sàng để tính điểm.")

    similarity = max(
        0.0,
        min(1.0, _cosine_similarity(candidate_embedding, job_embedding)),
    )
    semantic_score = round(similarity * 100, 2)

    profile_snapshot = application.profile_snapshot
    job_snapshot = application.job_snapshot
    candidate_skill_ids = {item["id"] for item in profile_snapshot["skills"]}
    job_skills = job_snapshot["skills"]
    matched_skills = [
        item["name"] for item in job_skills if item["id"] in candidate_skill_ids
    ]
    missing_skills = [
        item["name"]
        for item in job_skills
        if item["is_required"] and item["id"] not in candidate_skill_ids
    ]
    skill_overlap = (
        round(len(matched_skills) / len(job_skills) * 100, 2)
        if job_skills
        else 100.0
    )

    intervals = [
        (
            date.fromisoformat(item["start_date"]) if item["start_date"] else None,
            date.fromisoformat(item["end_date"]) if item["end_date"] else None,
            item["is_current"],
        )
        for item in profile_snapshot["experiences"]
    ]
    snapshot_date = application.snapshot_created_at.date()
    total_years = total_experience_years(intervals, snapshot_date)
    exp_score = round(
        experience_score(total_years, job_snapshot["experience_level"]),
        2,
    )

    required_level = required_degree_level(job_snapshot["requirements"])
    if not required_level:
        edu_score = 100.0
    else:
        highest_degree = max(
            (
                recognized_degree_level(item["degree"])
                for item in profile_snapshot["educations"]
            ),
            default=0,
        )
        edu_score = 100.0 if highest_degree >= required_level else 0.0

    weight_snapshot = application.matching_weight_snapshot
    semantic_weight = Decimal(weight_snapshot["semantic"])
    skill_weight = Decimal(weight_snapshot["skill"])
    experience_weight = Decimal(weight_snapshot["experience"])
    education_weight = Decimal(weight_snapshot["education"])
    score = Decimal(
        str(
            round(
                float(semantic_weight) * semantic_score
                + float(skill_weight) * skill_overlap
                + float(experience_weight) * exp_score
                + float(education_weight) * edu_score,
                2,
            )
        )
    )

    weight_config = None
    if weight_snapshot["config_id"]:
        weight_config = MatchingWeightConfig.objects.filter(
            pk=weight_snapshot["config_id"],
        ).first()
    services.save_match_analysis(
        application=application,
        match_score=score,
        semantic_similarity_score=semantic_score,
        skill_overlap_score=skill_overlap,
        experience_score=exp_score,
        education_score=edu_score,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        weight_config=weight_config,
        embedding_model_version=EMBEDDING_MODEL,
        candidate_embedding_version=profile_snapshot["profile_version"],
        job_embedding_version=job_snapshot["content_version"],
    )
    return True
