"""Các task nền xử lý embedding và hết hạn tin tuyển dụng."""
import logging
from datetime import timedelta

from django.conf import settings
from django.db.models import F, Q
from django.utils import timezone

from integrations.gemini.embeddings import (
    current_job_embedding_signature,
    embed_document,
)
from apps.core.embedding_text_builders import build_job_text
from apps.jobs.models import JDImport, JobPost


logger = logging.getLogger(__name__)

# Số lần tối đa một JDImport được gửi Gemini parse (đồng bộ với UC-01).
MAX_PARSE_ATTEMPTS = 3


def parse_jd_import(import_id: str) -> bool:
    # Nhận lại cả FAILED để task bị re-present (crash recovery) có cơ hội thử
    # lại như UC-01; giới hạn parse_attempts vẫn là ranh giới cứng chung.
    now = timezone.now()
    lease_expired_at = now - timedelta(seconds=settings.TASK_PROCESSING_LEASE_SECONDS)
    claimed = JDImport.objects.filter(
        pk=import_id,
        parse_attempts__lt=MAX_PARSE_ATTEMPTS,
    ).filter(
        Q(status__in=[JDImport.Status.PENDING, JDImport.Status.FAILED])
        | Q(status=JDImport.Status.PROCESSING, updated_at__lte=lease_expired_at)
    ).update(
        status=JDImport.Status.PROCESSING,
        parse_attempts=F("parse_attempts") + 1,
        error_message="",
        updated_at=now,
    )
    jd_import = JDImport.objects.filter(pk=import_id).first()
    if not claimed:
        if (
            jd_import is not None
            and jd_import.status == JDImport.Status.PROCESSING
            and jd_import.parse_attempts < MAX_PARSE_ATTEMPTS
        ):
            raise RuntimeError("JD import is already being processed.")
        if jd_import is not None and jd_import.parse_attempts >= MAX_PARSE_ATTEMPTS:
            # Cạn lượt thử: chốt FAILED vĩnh viễn, không gọi Gemini nữa.
            JDImport.objects.filter(pk=import_id).update(
                status=JDImport.Status.FAILED,
                error_message=f"Đã vượt quá {MAX_PARSE_ATTEMPTS} lần thử phân tích JD.",
                updated_at=timezone.now(),
            )
        return False
    if jd_import is None:
        # Bản ghi bị hủy khi đang PROCESSING — không còn gì để parse.
        logger.warning("JD import %s disappeared before parsing", import_id)
        return False
    try:
        from apps.jobs.jd_parser import parse_job_description
        from apps.jobs.serializers import JobDescriptionParseResultSerializer

        with jd_import.file.open("rb") as source:
            source.name = jd_import.original_filename
            _, parsed = parse_job_description(source)
        serialized = JobDescriptionParseResultSerializer(parsed).data
        JDImport.objects.filter(
            pk=import_id, status=JDImport.Status.PROCESSING
        ).update(
            status=JDImport.Status.SUCCESS,
            parsed_data=serialized,
            error_message="",
            updated_at=timezone.now(),
        )
        return True
    except Exception as exc:
        logger.exception("JD import %s failed", import_id)
        JDImport.objects.filter(pk=import_id).update(
            status=JDImport.Status.FAILED,
            error_message=(
                "Không thể đọc thông tin từ file JD. "
                f"Mã lỗi: {type(exc).__name__}."
            ),
            updated_at=timezone.now(),
        )
        raise


def cleanup_expired_jd_imports() -> int:
    expired = list(JDImport.objects.filter(expires_at__lte=timezone.now()))
    for jd_import in expired:
        if jd_import.file.name:
            jd_import.file.storage.delete(jd_import.file.name)
        jd_import.delete()
    return len(expired)


def generate_job_embedding(
    job_id: str,
    content_version: int,
    allow_closed: bool = False,
) -> bool:
    """Sinh embedding, bỏ task cũ; cho phép tin đã đóng khi chấm hồ sơ."""
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
    """Task định kỳ gọi service để chuyển tin quá hạn sang EXPIRED."""
    from apps.jobs.services import expire_jobs as expire_jobs_service

    return expire_jobs_service()
