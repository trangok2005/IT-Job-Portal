"""Các thao tác ghi và state machine của nghiệp vụ ứng tuyển."""
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.applications.models import ApplicationStatusHistory, JobApplication
from apps.candidates.models import CandidateProfile
from apps.core.embedding_text_builders import build_candidate_text, build_job_text
from apps.core.matching import MatchingWeights
from integrations.qstash.publisher import publish_task
from apps.jobs import selectors as job_selectors
from apps.jobs.models import JobPost
from apps.notifications.services import enqueue_application_status_email
from apps.skills.models import MatchingWeightConfig
from integrations.gemini.embeddings import (
    EMBEDDING_CONTENT_VERSION,
    EMBEDDING_DIMENSIONS,
    EMBEDDING_MODEL,
    TaskType,
    current_candidate_embedding_signature,
    current_job_embedding_signature,
)


def _enqueue_match_score(application: JobApplication) -> None:
    """Chỉ đưa tác vụ tính điểm vào hàng đợi sau khi hồ sơ commit thành công."""

    def enqueue():
        try:
            publish_task(
                "compute_application_match_score",
                {"application_id": str(application.pk)},
                deduplication_id=f"application-match-{application.pk}",
            )
        except Exception as exc:
            JobApplication.objects.filter(pk=application.pk).update(
                match_status=JobApplication.MatchStatus.FAILED,
                match_error=f"Không thể phát hành tác vụ tính điểm: {exc}",
            )

    transaction.on_commit(enqueue)


@transaction.atomic
def apply_to_job(
    user,
    job: JobPost,
    cover_letter: str = "",
    attach_current_resume: bool = False,
) -> JobApplication:
    """Tạo hồ sơ ứng tuyển và đóng băng mọi input dùng để tính điểm AI."""
    if not user.is_candidate or not user.is_active:
        raise ValueError("Chỉ ứng viên đang hoạt động mới được ứng tuyển.")

    profile = (
        CandidateProfile.objects.select_for_update()
        .prefetch_related(
            "resumes",
            "candidate_skills__skill",
            "experiences",
            "educations",
        )
        .filter(user=user)
        .first()
    )
    if profile is None:
        raise ValueError("Ứng viên chưa có hồ sơ để ứng tuyển.")
    locked_job = (
        JobPost.objects.select_for_update()
        .select_related("company")
        .prefetch_related("job_skills__skill")
        .get(pk=job.pk)
    )
    if not job_selectors.is_public_job(locked_job):
        raise ValueError("Tin tuyển dụng không còn nhận hồ sơ.")
    if not profile.is_complete:
        raise ValueError(
            "Hồ sơ chưa hoàn chỉnh; cần họ tên, số điện thoại, vị trí mong muốn và ít nhất một kỹ năng."
        )
    if JobApplication.objects.filter(job=locked_job, candidate=profile).exists():
        raise ValueError("Bạn đã ứng tuyển vào tin này.")

    resume = None
    if attach_current_resume:
        resume = profile.resumes.filter(is_primary=True).exclude(file="").first()
        if resume is None:
            raise ValueError("Bạn chưa có CV chính để đính kèm.")
        if (
            Path(resume.original_filename).suffix.lower() not in {".pdf", ".doc", ".docx"}
            or (
                resume.file_size_bytes is not None
                and resume.file_size_bytes > settings.MAX_RESUME_SIZE_BYTES
            )
            or not resume.file.storage.exists(resume.file.name)
        ):
            raise ValueError("CV chính không còn tồn tại hoặc không hợp lệ để đính kèm.")

    candidate_skills = [
        {
            "id": str(link.skill_id),
            "name": link.skill.name,
            "status": link.skill.status,
            "is_active": link.skill.is_active,
        }
        for link in profile.candidate_skills.all()
        if link.skill.is_active and link.skill.status in ("APPROVED", "PENDING")
    ]
    experiences = [
        {
            "start_date": item.start_date.isoformat() if item.start_date else None,
            "end_date": item.end_date.isoformat() if item.end_date else None,
            "is_current": item.is_current,
        }
        for item in profile.experiences.all()
    ]
    educations = [
        {
            "degree": item.degree,
            "degree_level": item.degree_level,
            "is_completed": item.is_completed,
            "is_verified": item.is_verified,
        }
        for item in profile.educations.all()
    ]
    job_skills = [
        {
            "id": str(link.skill_id),
            "name": link.skill.name,
            "is_required": link.is_required,
            "status": link.skill.status,
            "is_active": link.skill.is_active,
        }
        for link in locked_job.job_skills.all()
        if link.skill.is_active and link.skill.status in ("APPROVED", "PENDING")
    ]

    weight_configs = list(
        MatchingWeightConfig.objects.select_for_update().order_by("pk")
    )
    weight_config = next(
        (config for config in weight_configs if config.is_active),
        None,
    )
    if weight_config is None:
        raise ValueError("Chưa có cấu hình trọng số đang hiệu lực.")
    weights = MatchingWeights(
        semantic=weight_config.weight_semantic_similarity,
        skill=weight_config.weight_skill_overlap,
        experience=weight_config.weight_experience_match,
        education=weight_config.weight_education_match,
        required_skill_multiplier=weight_config.required_skill_multiplier,
    )

    snapshot_created_at = timezone.now()
    application = JobApplication.objects.create(
        job=locked_job,
        candidate=profile,
        resume=resume,
        cover_letter=cover_letter,
        status=JobApplication.Status.APPLIED,
        profile_snapshot={
            "profile_version": profile.profile_version,
            "embedding_signature": current_candidate_embedding_signature(),
            "embedding_model": EMBEDDING_MODEL,
            "embedding_task_type": TaskType.DOCUMENT,
            "embedding_dimensions": EMBEDDING_DIMENSIONS,
            "embedding_content_version": EMBEDDING_CONTENT_VERSION,
            "embedding_text": build_candidate_text(profile),
            "skills": candidate_skills,
            "experiences": experiences,
            "educations": educations,
        },
        job_snapshot={
            "content_version": locked_job.content_version,
            "embedding_signature": current_job_embedding_signature(),
            "embedding_model": EMBEDDING_MODEL,
            "embedding_task_type": TaskType.DOCUMENT,
            "embedding_dimensions": EMBEDDING_DIMENSIONS,
            "embedding_content_version": EMBEDDING_CONTENT_VERSION,
            "embedding_text": build_job_text(locked_job),
            "skills": job_skills,
            "experience_level": locked_job.experience_level,
            "requirements": locked_job.requirements,
            "required_education_level": locked_job.required_education_level,
        },
        matching_weight_snapshot={
            "config_id": str(weight_config.pk),
            "config_name": weight_config.name,
            "semantic": str(weights.semantic),
            "skill": str(weights.skill),
            "experience": str(weights.experience),
            "education": str(weights.education),
            "required_skill_multiplier": str(weights.required_skill_multiplier),
            "rule_version": "matching-v2.2.4",
        },
        candidate_embedding_snapshot=(
            list(profile.embedding) if not profile.embedding_is_stale else None
        ),
        job_embedding_snapshot=(
            list(locked_job.embedding) if not locked_job.embedding_is_stale else None
        ),
        snapshot_created_at=snapshot_created_at,
    )
    ApplicationStatusHistory.objects.create(
        application=application,
        from_status="",
        to_status=JobApplication.Status.APPLIED,
        changed_by=user,
        note="Ứng viên nộp hồ sơ.",
    )

    _enqueue_match_score(application)
    return application


@transaction.atomic
def transition_application(
    application: JobApplication,
    user,
    new_status: str,
    note: str = "",
    candidate_message: str = "",
    expected_status: str | None = None,
) -> JobApplication:
    """Chuyển trạng thái một chiều và ghi audit trail."""
    locked = (
        JobApplication.objects.select_for_update()
        .select_related("candidate__user", "job__company")
        .get(pk=application.pk)
    )
    is_owner = (
        user.is_active
        and user.is_employer
        and (
            locked.job.created_by_id == user.pk
            or locked.job.company.owner_id == user.pk
        )
    )
    if not is_owner:
        raise ValueError("Bạn không có quyền xử lý hồ sơ ứng tuyển này.")
    if expected_status is not None and locked.status != expected_status:
        raise ValueError(
            "Hồ sơ đã được người khác xử lý. Vui lòng tải lại thông tin mới."
        )
    if not locked.can_transition_to(new_status):
        raise ValueError(
            f"Không thể chuyển trạng thái từ {locked.status} sang {new_status}."
        )

    previous_status = locked.status
    locked.status = new_status
    locked.save(update_fields=["status", "updated_at"])
    history = ApplicationStatusHistory.objects.create(
        application=locked,
        from_status=previous_status,
        to_status=new_status,
        changed_by=user,
        note=note,
        candidate_message=candidate_message,
        notification_status=ApplicationStatusHistory.NotificationStatus.PENDING,
    )
    enqueue_application_status_email(history)
    application.status = locked.status
    if hasattr(application, "_prefetched_objects_cache"):
        application._prefetched_objects_cache.clear()
    return application
