import logging
from datetime import datetime, timedelta

from django.conf import settings
from django.db.models import F, Q
from django.utils import timezone

from apps.core.embedding_text_builders import build_job_text
from apps.jobs import services
from apps.jobs.models import JDImport, JobPost
from integrations.gemini.embeddings import (
    current_job_embedding_signature,
    embed_document,
)
from integrations.gemini.jd_parser import parse_job_description


logger = logging.getLogger(__name__)

# Giới hạn broker retry để không cạn quota Gemini khi dịch vụ lỗi dài.
MAX_PARSE_ATTEMPTS = 3


def _retryable_imports(import_id: str, now: datetime):
    """Chỉ nhận bản chưa chạy, bị lỗi hoặc đã hết lease."""
    lease_expired_at = now - timedelta(seconds=settings.TASK_PROCESSING_LEASE_SECONDS)
    return JDImport.objects.filter(pk=import_id).filter(
        Q(status__in=[JDImport.Status.PENDING, JDImport.Status.FAILED])
        | Q(status=JDImport.Status.PROCESSING, updated_at__lte=lease_expired_at)
    )


def _claim_parse_attempt(import_id: str) -> datetime | None:
    """Claim bằng một UPDATE để hai worker không cùng nhận việc."""
    now = timezone.now()
    claimed = _retryable_imports(import_id, now).filter(
        parse_attempts__lt=MAX_PARSE_ATTEMPTS,
    ).update(
        status=JDImport.Status.PROCESSING,
        parse_attempts=F("parse_attempts") + 1,
        error_message="",
        updated_at=now,
    )
    return now if claimed else None


def _handle_unclaimed_import(import_id: str) -> bool:
    jd_import = JDImport.objects.filter(pk=import_id).first()
    if jd_import is None:
        return False
    if jd_import.parse_attempts >= MAX_PARSE_ATTEMPTS:
        now = timezone.now()
        _retryable_imports(import_id, now).filter(
            parse_attempts__gte=MAX_PARSE_ATTEMPTS,
        ).update(
            status=JDImport.Status.FAILED,
            error_message=f"Đã vượt quá {MAX_PARSE_ATTEMPTS} lần thử phân tích JD.",
            updated_at=now,
        )
        return False
    if jd_import.status == JDImport.Status.PROCESSING:
        raise RuntimeError("JD import is already being processed.")
    return False


def parse_jd_import(import_id: str) -> bool:
    jd_import = JDImport.objects.filter(pk=import_id).first()
    if jd_import is None or jd_import.status in (
        JDImport.Status.SUCCESS,
        JDImport.Status.CONSUMED,
    ):
        return False

    claim_token = _claim_parse_attempt(import_id)
    if claim_token is None:
        return _handle_unclaimed_import(import_id)

    # updated_at giữ quyền ghi của lượt này, kể cả khi worker khác đã retry.
    owned_attempt = JDImport.objects.filter(
        pk=import_id,
        status=JDImport.Status.PROCESSING,
        updated_at=claim_token,
    )
    jd_import = owned_attempt.first()
    if jd_import is None:
        return False

    try:
        with jd_import.file.open("rb") as source:
            file_data = source.read()
        result = parse_job_description(
            filename=jd_import.original_filename,
            mime_type=None,
            file_data=file_data,
        )
        return services.mark_jd_import_parsed(
            import_id, claim_token, result.validated_data
        )
    except Exception as exc:
        if not JDImport.objects.filter(pk=import_id).exists():
            return False
        logger.exception("JD import %s failed", import_id)
        owned_attempt.update(
            status=JDImport.Status.FAILED,
            error_message=(
                "Không thể đọc thông tin từ file JD. "
                f"Mã lỗi: {type(exc).__name__}."
            ),
            updated_at=timezone.now(),
        )
        raise


def cleanup_expired_jd_imports() -> int:
    expired = JDImport.objects.filter(expires_at__lte=timezone.now())
    count = 0
    for jd_import in expired.iterator():
        services.delete_jd_import(jd_import)
        count += 1
    return count


def generate_job_embedding(
    job_id: str,
    content_version: int,
    allow_closed: bool = False,
) -> bool:
    """Bỏ task cũ; tin đã đóng chỉ được xử lý khi chấm hồ sơ."""
    allowed_statuses = [JobPost.Status.ACTIVE]
    if allow_closed:
        allowed_statuses.extend([JobPost.Status.CLOSED, JobPost.Status.EXPIRED])
    job = (
        JobPost.objects.filter(pk=job_id, status__in=allowed_statuses)
        .prefetch_related("job_skills__skill")
        .first()
    )
    if job is None or job.content_version != content_version:
        return False

    values = embed_document(build_job_text(job))

    updated = JobPost.objects.filter(
        pk=job_id,
        status__in=allowed_statuses,
        content_version=content_version,
    ).update(
        embedding=values,
        embedding_version=content_version,
        embedding_signature=current_job_embedding_signature(),
        embedding_updated_at=timezone.now(),
    )
    return bool(updated)


def expire_jobs() -> int:
    return services.expire_jobs()
