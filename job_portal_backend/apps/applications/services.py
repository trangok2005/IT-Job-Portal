"""Write operations và state machine của nghiệp vụ ứng tuyển."""
from django.db import transaction
from django.utils import timezone

from apps.applications.models import ApplicationStatusHistory, JobApplication
from apps.candidates.models import CandidateProfile
from apps.core.embedding_text_builders import build_candidate_text, build_job_text
from apps.core.matching import DEFAULT_MATCHING_WEIGHTS, MatchingWeights
from apps.jobs import selectors as job_selectors
from apps.jobs.models import JobPost
from apps.skills.models import MatchingWeightConfig
from integrations.gemini.embeddings import (
    current_candidate_embedding_signature,
    current_job_embedding_signature,
)


def _enqueue_match_score(application: JobApplication) -> None:
    """Chỉ enqueue tính match score sau khi hồ sơ ứng tuyển commit thành công."""

    def enqueue():
        from django_q.tasks import async_task

        async_task(
            "apps.ai_analysis.tasks.compute_application_match_score",
            str(application.pk),
        )

    transaction.on_commit(enqueue)


@transaction.atomic
def apply_to_job(
    user,
    job: JobPost,
    cover_letter: str = "",
    attach_current_resume: bool = False,
) -> JobApplication:
    """Create one application and freeze every input used by its AI score."""
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
        .get(user=user)
    )
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

    candidate_skills = [
        {
            "id": str(link.skill_id),
            "name": link.skill.name,
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
    educations = [{"degree": item.degree} for item in profile.educations.all()]
    job_skills = [
        {
            "id": str(link.skill_id),
            "name": link.skill.name,
            "is_required": link.is_required,
        }
        for link in locked_job.job_skills.all()
    ]

    weight_configs = list(
        MatchingWeightConfig.objects.select_for_update().order_by("pk")
    )
    weight_config = next(
        (config for config in weight_configs if config.is_active),
        None,
    )
    weights = DEFAULT_MATCHING_WEIGHTS
    if weight_config is not None:
        weights = MatchingWeights(
            semantic=weight_config.weight_semantic_similarity,
            skill=weight_config.weight_skill_overlap,
            experience=weight_config.weight_experience_match,
            education=weight_config.weight_education_match,
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
            "embedding_text": build_candidate_text(profile),
            "skills": candidate_skills,
            "experiences": experiences,
            "educations": educations,
        },
        job_snapshot={
            "content_version": locked_job.content_version,
            "embedding_signature": current_job_embedding_signature(),
            "embedding_text": build_job_text(locked_job),
            "skills": job_skills,
            "experience_level": locked_job.experience_level,
            "requirements": locked_job.requirements,
        },
        matching_weight_snapshot={
            "config_id": str(weight_config.pk) if weight_config else None,
            "config_name": weight_config.name if weight_config else None,
            "semantic": str(weights.semantic),
            "skill": str(weights.skill),
            "experience": str(weights.experience),
            "education": str(weights.education),
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
) -> JobApplication:
    """Chuyển trạng thái một chiều và ghi audit trail."""
    locked = (
        JobApplication.objects.select_for_update()
        .select_related("candidate__user", "job__company")
        .get(pk=application.pk)
    )
    is_owner = (
        user.is_employer
        and (
            locked.job.created_by_id == user.pk
            or locked.job.company.owner_id == user.pk
        )
    )
    if not (user.is_admin_role or is_owner):
        raise ValueError("Bạn không có quyền xử lý hồ sơ ứng tuyển này.")
    if not locked.can_transition_to(new_status):
        raise ValueError(
            f"Không thể chuyển trạng thái từ {locked.status} sang {new_status}."
        )

    previous_status = locked.status
    locked.status = new_status
    locked.save(update_fields=["status", "updated_at"])
    ApplicationStatusHistory.objects.create(
        application=locked,
        from_status=previous_status,
        to_status=new_status,
        changed_by=user,
        note=note,
    )
    application.status = locked.status
    if hasattr(application, "_prefetched_objects_cache"):
        application._prefetched_objects_cache.clear()
    return application
