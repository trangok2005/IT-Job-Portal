import math
from datetime import date
from decimal import Decimal

from django.db import models
from django.utils import timezone

from apps.ai_analysis import services
from apps.ai_analysis.models import ApplicationMatchResult
from apps.applications.models import JobApplication
from apps.core.matching import (
    MatchingWeights,
    aggregate_match_score,
    education_score,
    experience_score,
    recognized_degree_level,
    required_degree_level,
    semantic_similarity,
    skill_match_score,
    total_experience_years,
)
from apps.candidates.models import DEGREE_LEVEL_RANK
from integrations.gemini.embeddings import (
    EMBEDDING_DIMENSIONS,
    EMBEDDING_CONTENT_VERSION,
    EMBEDDING_MODEL,
    TaskType,
    current_candidate_embedding_signature,
    current_job_embedding_signature,
    embed_document,
)


def _cosine_similarity(left, right) -> float:
    if len(left) != EMBEDDING_DIMENSIONS or len(right) != EMBEDDING_DIMENSIONS:
        raise ValueError("Embedding snapshot sai số chiều.")
    if any(not math.isfinite(value) for value in (*left, *right)):
        raise ValueError("Embedding snapshot chứa giá trị không hữu hạn.")
    dot_product = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        raise ValueError("Embedding snapshot không được là zero vector.")
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
        if snapshot["embedding_signature"] != current_candidate_embedding_signature():
            raise RuntimeError(
                "Không thể sinh lại vector hồ sơ bằng phiên bản embedding khác snapshot."
            )
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
        if snapshot["embedding_signature"] != current_job_embedding_signature():
            raise RuntimeError(
                "Không thể sinh lại vector tin bằng phiên bản embedding khác snapshot."
            )
        vector = embed_document(snapshot["embedding_text"])

    JobApplication.objects.filter(
        pk=application.pk,
        job_embedding_snapshot__isnull=True,
    ).update(job_embedding_snapshot=vector)
    application.refresh_from_db(fields=["job_embedding_snapshot"])
    return application.job_embedding_snapshot


def _save_legacy_snapshot_result(application, similarity) -> None:
    """Giữ cách tính cũ cho snapshot tạo trước v2."""
    profile_snapshot = application.profile_snapshot
    job_snapshot = application.job_snapshot
    candidate_skill_ids = {item["id"] for item in profile_snapshot["skills"]}
    job_skills = job_snapshot["skills"]
    matched_skills = [
        item["name"] for item in job_skills if item["id"] in candidate_skill_ids
    ]
    missing_skills = [
        item["name"] for item in job_skills
        if item["is_required"] and item["id"] not in candidate_skill_ids
    ]
    skill_score = len(matched_skills) / len(job_skills) * 100 if job_skills else 100
    intervals = [
        (
            date.fromisoformat(item["start_date"]) if item["start_date"] else None,
            date.fromisoformat(item["end_date"]) if item["end_date"] else None,
            item["is_current"],
        )
        for item in profile_snapshot["experiences"]
    ]
    snapshot_date = timezone.localdate(application.snapshot_created_at)
    legacy_days = 0
    for start_date, end_date, is_current in intervals:
        effective_end = snapshot_date if is_current else end_date
        if start_date is not None and effective_end is not None and effective_end >= start_date:
            legacy_days += (effective_end - start_date).days
    exp_score = experience_score(
        legacy_days / 365.25,
        job_snapshot["experience_level"],
    ) * 100
    required_level = required_degree_level(job_snapshot.get("requirements", ""))
    highest_level = max(
        (recognized_degree_level(item.get("degree", "")) for item in profile_snapshot["educations"]),
        default=0,
    )
    edu_score = 100 if not required_level or highest_level >= required_level else 0
    weight_snapshot = application.matching_weight_snapshot
    score = sum(
        Decimal(weight_snapshot[name]) * Decimal(str(value))
        for name, value in (
            ("semantic", similarity * 100),
            ("skill", skill_score),
            ("experience", exp_score),
            ("education", edu_score),
        )
    ).quantize(Decimal("0.01"))
    services.save_match_result(
        application=application,
        match_score=score,
        semantic_similarity_score=similarity * 100,
        skill_overlap_score=skill_score,
        experience_score=exp_score,
        education_score=edu_score,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        embedding_model_version=EMBEDDING_MODEL,
        rule_version="legacy-v1",
    )
    JobApplication.objects.filter(pk=application.pk).update(
        match_status=JobApplication.MatchStatus.COMPLETED,
        match_error="",
    )


def _compute_application_match_score(application_id: str) -> bool:
    if ApplicationMatchResult.objects.filter(application_id=application_id).exists():
        result = ApplicationMatchResult.objects.get(application_id=application_id)
        JobApplication.objects.filter(pk=application_id).update(
            match_status=(
                JobApplication.MatchStatus.COMPLETED
                if result.status == ApplicationMatchResult.Status.COMPLETED
                else JobApplication.MatchStatus.INSUFFICIENT
            ),
            match_error="",
        )
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
        # Dữ liệu hiện tại không thể tái tạo điểm của hồ sơ có trước snapshot.
        JobApplication.objects.filter(pk=application_id).update(
            match_status=JobApplication.MatchStatus.INSUFFICIENT,
            match_error="Đơn lịch sử không có snapshot tính điểm.",
        )
        return False

    candidate_embedding = _candidate_embedding(application)
    job_embedding = _job_embedding(application)
    if candidate_embedding is None or job_embedding is None:
        raise RuntimeError("Embedding snapshot chưa sẵn sàng để tính điểm.")

    cosine_similarity = max(
        -1.0,
        min(1.0, _cosine_similarity(candidate_embedding, job_embedding)),
    )
    semantic_score = semantic_similarity(1.0 - cosine_similarity)
    similarity = semantic_score

    profile_snapshot = application.profile_snapshot
    job_snapshot = application.job_snapshot
    if "rule_version" not in application.matching_weight_snapshot:
        _save_legacy_snapshot_result(application, similarity)
        return True
    candidate_skill_ids = {item["id"] for item in profile_snapshot["skills"]}
    job_skills = job_snapshot["skills"]
    multiplier = application.matching_weight_snapshot["required_skill_multiplier"]
    skill_score, skill_details = skill_match_score(
        candidate_skill_ids,
        job_skills,
        multiplier,
    )
    all_job_skills = {**skill_details.get("preferred", {}), **skill_details.get("required", {})}
    matched_skills = sorted({
        item["name"] for skill_id, item in all_job_skills.items()
        if skill_id in candidate_skill_ids
    })
    missing_skills = [
        item["name"] for skill_id, item in skill_details.get("required", {}).items()
        if skill_id not in candidate_skill_ids
    ]

    intervals = [
        (
            date.fromisoformat(item["start_date"]) if item["start_date"] else None,
            date.fromisoformat(item["end_date"]) if item["end_date"] else None,
            item["is_current"],
        )
        for item in profile_snapshot["experiences"]
    ]
    snapshot_date = timezone.localdate(application.snapshot_created_at)
    total_years = total_experience_years(intervals, snapshot_date)
    has_valid_experience = any(
        start_date is not None
        and (snapshot_date if is_current else end_date) is not None
        and (snapshot_date if is_current else end_date) >= start_date
        for start_date, end_date, is_current in intervals
    )
    experience_level = job_snapshot["experience_level"]
    exp_score = experience_score(total_years, experience_level) if experience_level else None

    verified_levels = [
        item["degree_level"]
        for item in profile_snapshot["educations"]
        if item.get("is_completed")
        and item.get("is_verified")
        and item.get("degree_level") in DEGREE_LEVEL_RANK
    ]
    highest_degree = max(verified_levels, key=DEGREE_LEVEL_RANK.get) if verified_levels else None
    required_level = job_snapshot.get("required_education_level")
    edu_score = education_score(highest_degree, required_level)

    weight_snapshot = application.matching_weight_snapshot
    weights = MatchingWeights(
        semantic=Decimal(weight_snapshot["semantic"]),
        skill=Decimal(weight_snapshot["skill"]),
        experience=Decimal(weight_snapshot["experience"]),
        education=Decimal(weight_snapshot["education"]),
        required_skill_multiplier=Decimal(multiplier),
    )
    components = {
        "semantic": semantic_score,
        "skill": skill_score,
        "experience": exp_score,
        "education": edu_score,
    }
    score, normalized_weights = aggregate_match_score(components, weights)
    applicability = {name: value is not None for name, value in components.items()}
    missing_information = {}
    if experience_level and not has_valid_experience:
        missing_information["experience"] = "Hồ sơ chưa có kinh nghiệm được ghi nhận; dùng 0 năm."
    if required_level and highest_degree is None:
        missing_information["education"] = "Hồ sơ chưa khai học vấn hoàn thành và đã xác nhận."
    if skill_score is None:
        missing_information["skill"] = "Tin tuyển dụng không yêu cầu kỹ năng."
    if edu_score is None:
        missing_information["education"] = "Tin tuyển dụng không yêu cầu học vấn."

    result_status = (
        ApplicationMatchResult.Status.COMPLETED
        if score is not None
        else ApplicationMatchResult.Status.INSUFFICIENT
    )

    services.save_match_result(
        application=application,
        match_score=score,
        semantic_similarity_score=semantic_score,
        skill_overlap_score=skill_score,
        experience_score=exp_score,
        education_score=edu_score,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        embedding_model_version=EMBEDDING_MODEL,
        status=result_status,
        criteria_applicability=applicability,
        original_weights={
            "semantic": str(weights.semantic),
            "skill": str(weights.skill),
            "experience": str(weights.experience),
            "education": str(weights.education),
            "required_skill_multiplier": str(weights.required_skill_multiplier),
        },
        normalized_weights={name: str(value) for name, value in normalized_weights.items()},
        missing_information=missing_information,
        rule_version=weight_snapshot.get("rule_version", "matching-v2.2.4"),
        embedding_metadata={
            "model": EMBEDDING_MODEL,
            "task_type": TaskType.DOCUMENT,
            "dimensions": EMBEDDING_DIMENSIONS,
            "content_version": EMBEDDING_CONTENT_VERSION,
            "candidate_signature": profile_snapshot["embedding_signature"],
            "job_signature": job_snapshot["embedding_signature"],
        },
    )
    JobApplication.objects.filter(pk=application.pk).update(
        match_status=(
            JobApplication.MatchStatus.COMPLETED
            if score is not None
            else JobApplication.MatchStatus.INSUFFICIENT
        ),
        match_error="",
    )
    return True


def compute_application_match_score(application_id: str) -> bool:
    """Không để lỗi chấm điểm đổi trạng thái tuyển dụng."""
    claimed = JobApplication.objects.filter(pk=application_id).update(
        match_status=JobApplication.MatchStatus.PROCESSING,
        match_error="",
        match_attempts=models.F("match_attempts") + 1,
    )
    if not claimed:
        return True
    try:
        return _compute_application_match_score(application_id)
    except Exception as exc:
        failed = JobApplication.objects.filter(
            pk=application_id,
            match_result__isnull=True,
        ).update(
            match_status=JobApplication.MatchStatus.FAILED,
            match_error=str(exc),
        )
        if not failed:
            result = ApplicationMatchResult.objects.filter(
                application_id=application_id
            ).first()
            if result is not None:
                JobApplication.objects.filter(pk=application_id).update(
                    match_status=(
                        JobApplication.MatchStatus.COMPLETED
                        if result.status == ApplicationMatchResult.Status.COMPLETED
                        else JobApplication.MatchStatus.INSUFFICIENT
                    ),
                    match_error="",
                )
                return True
        raise


def retry_incomplete_application_matches() -> int:
    from integrations.qstash.publisher import publish_task

    application_ids = list(
        JobApplication.objects.filter(
            match_status__in=(
                JobApplication.MatchStatus.PENDING,
                JobApplication.MatchStatus.FAILED,
            ),
            match_result__isnull=True,
        )
        .filter(models.Q(match_attempts__lt=5) | models.Q(match_attempts=0))
        .values_list("pk", flat=True)[:100]
    )
    published = 0
    for application_id in application_ids:
        try:
            publish_task(
                "compute_application_match_score",
                {"application_id": str(application_id)},
                deduplication_id=(
                    f"application-match-retry-{application_id}-"
                    f"{int(timezone.now().timestamp() // 300)}"
                ),
            )
            published += 1
        except Exception as exc:
            JobApplication.objects.filter(pk=application_id).update(
                match_status=JobApplication.MatchStatus.FAILED,
                match_error=f"Không thể phát hành lại tác vụ tính điểm: {exc}",
            )
    return published
