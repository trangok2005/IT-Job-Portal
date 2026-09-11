"""Các thao tác ghi và quy tắc nghiệp vụ đăng tin tuyển dụng của UC-02."""
from datetime import timedelta
from pathlib import Path

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.companies.models import Company
from apps.jobs.models import JDImport, JobPost, JobSkill
from apps.skills.services import resolve_savable_skill
from apps.skills.utils import normalize_alias
from integrations.qstash.publisher import publish_task


def build_jd_parse_result(parsed_data: dict) -> dict:
    """Phân giải tên skill đã trích xuất và tạo cấu trúc preview JD hiện có."""
    from apps.jobs.serializers import JobDescriptionParseResultSerializer

    parsed = dict(parsed_data)
    required_flags = parsed.pop("_skill_required_flags", {})
    matched = []
    matched_indexes = {}
    unmatched = []
    for name in parsed.get("skills", []):
        try:
            skill = resolve_savable_skill(name)
        except ValueError:
            unmatched.append(name)
            continue

        is_required = required_flags.get(normalize_alias(name), True)
        matched_index = matched_indexes.get(skill.pk)
        if matched_index is None:
            matched_indexes[skill.pk] = len(matched)
            matched.append(
                {
                    "id": str(skill.pk),
                    "name": skill.name,
                    "status": skill.status,
                    "is_required": is_required,
                }
            )
        else:
            matched[matched_index]["is_required"] = (
                matched[matched_index]["is_required"] or is_required
            )

    parsed["required_skills"] = [item["id"] for item in matched]
    parsed["resolved_skills"] = matched
    parsed["unmatched_skills"] = unmatched
    return dict(JobDescriptionParseResultSerializer(parsed).data)


def _enqueue_embedding(job: JobPost) -> None:
    """Đưa embedding đúng content version vào hàng đợi sau khi commit."""

    def enqueue():
        publish_task(
            "generate_job_embedding",
            {"job_id": str(job.pk), "content_version": job.content_version},
        )

    transaction.on_commit(enqueue)


def _enqueue_jd_parse(jd_import: JDImport) -> None:
    def enqueue():
        try:
            publish_task("parse_jd_import", {"import_id": str(jd_import.pk)})
        except Exception:
            JDImport.objects.filter(
                pk=jd_import.pk, status=JDImport.Status.PENDING
            ).update(
                status=JDImport.Status.FAILED,
                error_message="Không thể đưa JD vào hàng đợi xử lý.",
                updated_at=timezone.now(),
            )

    transaction.on_commit(enqueue)


@transaction.atomic
def create_jd_import(user, company: Company, file) -> JDImport:
    if not user.is_employer or company.owner_id != user.pk:
        raise ValueError("Bạn không có quyền import JD cho công ty này.")
    if company.status != Company.Status.APPROVED:
        raise ValueError("Công ty chưa được duyệt, không thể import JD.")
    jd_import = JDImport.objects.create(
        company=company,
        created_by=user,
        file=file,
        original_filename=Path(file.name).name,
        status=JDImport.Status.PENDING,
        expires_at=timezone.now() + timedelta(hours=24),
    )
    _enqueue_jd_parse(jd_import)
    return jd_import


@transaction.atomic
def cancel_jd_import(jd_import: JDImport) -> None:
    locked = JDImport.objects.select_for_update().get(pk=jd_import.pk)
    if locked.status == JDImport.Status.CONSUMED:
        raise ValueError("JD import đã được dùng để tạo tin.")
    storage = locked.file.storage
    stored_name = locked.file.name
    locked.delete()
    if stored_name:
        transaction.on_commit(lambda: storage.delete(stored_name))


def enqueue_job_embedding_robust(job: JobPost) -> None:
    """Cố đưa task vào hàng đợi khi đọc gợi ý nhưng không làm API thất bại."""
    try:
        publish_task(
            "generate_job_embedding",
            {"job_id": str(job.pk), "content_version": job.content_version},
        )
    except Exception:
        return


def enqueue_candidate_embedding_robust(profile) -> None:
    """Cố đưa embedding candidate bị thiếu hoặc cũ vào hàng đợi."""
    try:
        publish_task(
            "generate_candidate_embedding",
            {
                "profile_id": str(profile.pk),
                "profile_version": profile.profile_version,
            },
        )
    except Exception:
        return


def _bump_content_version(job: JobPost) -> None:
    """Tăng version nguyên tử; chỉ tin ACTIVE mới cần sinh embedding ngay."""
    JobPost.objects.filter(pk=job.pk).update(
        content_version=F("content_version") + 1,
        updated_at=timezone.now(),
    )
    job.refresh_from_db(fields=["content_version", "updated_at"])
    if job.status == JobPost.Status.ACTIVE:
        _enqueue_embedding(job)


def _replace_job_skills(job: JobPost, skill_specs: list) -> None:
    """Thay danh sách skill trong cùng transaction tạo hoặc cập nhật.
    Mỗi phần tử là dict ``{skill, is_required?}`` từ serializer.
    """
    job.job_skills.all().delete()
    JobSkill.objects.bulk_create(
        JobSkill(
            job=job,
            skill=spec["skill"],
            is_required=spec.get("is_required", True),
        )
        for spec in skill_specs
    )


@transaction.atomic
def create_job(
    user,
    company: Company,
    data: dict,
    required_skills: list | None = None,
    publish_immediately: bool = False,
    jd_import_id=None,
) -> JobPost:
    """Tạo DRAFT hoặc ACTIVE theo lựa chọn xác nhận trong UC-02."""
    if not user.is_employer or company.owner_id != user.pk:
        raise ValueError("Bạn không có quyền tạo tin cho công ty này.")
    if company.status != Company.Status.APPROVED:
        raise ValueError("Công ty chưa được duyệt, không thể tạo tin.")
    expires_at = data.get("expires_at")
    if publish_immediately and expires_at is not None and expires_at <= timezone.now():
        raise ValueError("Thời hạn nhận hồ sơ phải ở tương lai.")

    jd_import = None
    if jd_import_id:
        jd_import = JDImport.objects.select_for_update().filter(
            pk=jd_import_id,
            created_by=user,
            company=company,
            status=JDImport.Status.SUCCESS,
            expires_at__gt=timezone.now(),
        ).first()
        if jd_import is None:
            raise ValueError("Kết quả trích xuất JD không hợp lệ hoặc đã hết hạn.")
    job = JobPost.objects.create(
        company=company,
        created_by=user,
        status=(JobPost.Status.ACTIVE if publish_immediately else JobPost.Status.DRAFT),
        published_at=timezone.now() if publish_immediately else None,
        **data,
    )
    if required_skills:
        _replace_job_skills(job, required_skills)
    if publish_immediately:
        _enqueue_embedding(job)
    if jd_import is not None:
        jd_import.status = JDImport.Status.CONSUMED
        jd_import.save(update_fields=["status", "updated_at"])
    return job


@transaction.atomic
def update_job(
    job: JobPost,
    data: dict,
    required_skills: list | None = None,
) -> JobPost:
    """Chỉ tin DRAFT được chỉnh sửa nội dung. ACTIVE/CLOSED/EXPIRED là
    bản ghi bất biến: tin đang tuyển giữ nguyên ngữ nghĩa của các đơn đã
    nộp, tin đóng/kết thúc là lịch sử — không ai sửa được."""
    if job.status != JobPost.Status.DRAFT:
        raise ValueError("Chỉ tin nháp mới được chỉnh sửa nội dung.")
    if not data and required_skills is None:
        return job
    for field, value in data.items():
        setattr(job, field, value)
    if data:
        job.save(update_fields=[*data.keys(), "updated_at"])
    if required_skills is not None:
        _replace_job_skills(job, required_skills)
    _bump_content_version(job)
    return job


@transaction.atomic
def publish_job(job: JobPost) -> JobPost:
    """Chỉ chuyển DRAFT sang ACTIVE khi công ty và thời hạn còn hợp lệ."""
    if job.company.status != Company.Status.APPROVED:
        raise ValueError("Công ty chưa được duyệt, không thể đăng tin.")
    if job.status == JobPost.Status.ACTIVE:
        if job.embedding_is_stale:
            _enqueue_embedding(job)
        return job
    if job.status != JobPost.Status.DRAFT:
        raise ValueError("Chỉ tin nháp mới được đăng.")
    if job.expires_at is not None and job.expires_at <= timezone.now():
        raise ValueError("Thời hạn nhận hồ sơ phải ở tương lai.")

    job.status = JobPost.Status.ACTIVE
    job.published_at = timezone.now()
    job.save(update_fields=["status", "published_at", "updated_at"])
    _enqueue_embedding(job)
    return job


@transaction.atomic
def close_job(job: JobPost) -> JobPost:
    """Đóng vĩnh viễn tin đang tuyển; không cho chuyển ngược sang ACTIVE."""
    if job.status != JobPost.Status.ACTIVE:
        raise ValueError("Chỉ có thể đóng tin đang tuyển.")
    job.status = JobPost.Status.CLOSED
    job.save(update_fields=["status", "updated_at"])
    return job


def expire_jobs() -> int:
    """Đánh dấu EXPIRED cho các tin ACTIVE đã qua hạn; dùng bởi lịch QStash."""
    return JobPost.objects.filter(
        status=JobPost.Status.ACTIVE,
        expires_at__lte=timezone.now(),
    ).update(status=JobPost.Status.EXPIRED, updated_at=timezone.now())
