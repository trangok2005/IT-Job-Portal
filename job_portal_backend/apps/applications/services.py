"""Write operations và state machine của nghiệp vụ ứng tuyển."""
from django.db import transaction
from django.utils import timezone

from apps.applications.models import ApplicationStatusHistory, JobApplication
from apps.candidates.models import CandidateProfile
from apps.jobs import selectors as job_selectors
from apps.jobs.models import JobPost

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
def apply_to_job(user, job: JobPost, cover_letter: str = "") -> JobApplication:
    """Nộp CV chính vào tin đang mở sau khi kiểm tra hồ sơ và chống nộp trùng."""
    if not user.is_candidate or not user.is_active:
        raise ValueError("Chỉ ứng viên đang hoạt động mới được ứng tuyển.")

    profile = (
        CandidateProfile.objects.select_for_update()
        .prefetch_related("resumes")
        .get(user=user)
    )
    locked_job = (
        JobPost.objects.select_for_update()
        .select_related("company")
        .get(pk=job.pk)
    )
    if not job_selectors.is_public_job(locked_job):
        raise ValueError("Tin tuyển dụng không còn nhận hồ sơ.")
    if not profile.is_complete:
        raise ValueError(
            "Hồ sơ chưa hoàn chỉnh; cần họ tên, số điện thoại, vị trí mong muốn và CV chính."
        )
    if JobApplication.objects.filter(job=locked_job, candidate=profile).exists():
        raise ValueError("Bạn đã ứng tuyển vào tin này.")

    resume = profile.resumes.filter(is_primary=True).first()
    application = JobApplication.objects.create(
        job=locked_job,
        candidate=profile,
        resume=resume,
        cover_letter=cover_letter,
        status=JobApplication.Status.APPLIED,
    )
    ApplicationStatusHistory.objects.create(
        application=application,
        from_status="",
        to_status=JobApplication.Status.APPLIED,
        changed_by=user,
        note="Ứng viên nộp hồ sơ.",
    )

    from apps.notifications.services import notify_application_received

    notify_application_received(application)
    _enqueue_match_score(application)
    return application


@transaction.atomic
def transition_application(
    application: JobApplication,
    user,
    new_status: str,
    note: str = "",
) -> JobApplication:
    """Chuyển trạng thái một chiều, ghi audit trail và thông báo cho ứng viên."""
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
    locked.status_updated_at = timezone.now()
    locked.save(update_fields=["status", "status_updated_at", "updated_at"])
    ApplicationStatusHistory.objects.create(
        application=locked,
        from_status=previous_status,
        to_status=new_status,
        changed_by=user,
        note=note,
    )
    from apps.notifications.services import notify_application_status_changed

    notify_application_status_changed(locked)

    application.status = locked.status
    application.status_updated_at = locked.status_updated_at
    if hasattr(application, "_prefetched_objects_cache"):
        application._prefetched_objects_cache.clear()
    return application
