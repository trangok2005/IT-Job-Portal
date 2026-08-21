"""Django-Q tasks cho embedding và hết hạn tin tuyển dụng."""
import logging

from django.utils import timezone

from integrations.gemini.embeddings import (
    current_job_embedding_signature,
    embed_document,
)
from apps.core.embedding_text_builders import build_job_text
from apps.jobs.models import JDImport, JobPost


logger = logging.getLogger(__name__)


def parse_jd_import(import_id: str) -> bool:
    claimed = JDImport.objects.filter(
        pk=import_id, status=JDImport.Status.PENDING
    ).update(status=JDImport.Status.PROCESSING, error_message="")
    if not claimed:
        return False
    jd_import = JDImport.objects.get(pk=import_id)
    try:
        from apps.jobs.jd_parser import parse_job_description
        from apps.jobs.serializers import JobDescriptionParseResultSerializer

        with jd_import.file.open("rb") as source:
            source.name = jd_import.original_filename
            raw_data, parsed = parse_job_description(source)
        serialized = JobDescriptionParseResultSerializer(parsed).data
        JDImport.objects.filter(
            pk=import_id, status=JDImport.Status.PROCESSING
        ).update(
            status=JDImport.Status.SUCCESS,
            raw_extracted_json=raw_data,
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
        return False


def cleanup_expired_jd_imports() -> int:
    expired = list(JDImport.objects.filter(expires_at__lte=timezone.now()))
    for jd_import in expired:
        if jd_import.status != JDImport.Status.CONSUMED and jd_import.file.name:
            jd_import.file.storage.delete(jd_import.file.name)
        jd_import.delete()
    return len(expired)


def generate_job_embedding(
    job_id: str,
    content_version: int,
    allow_closed: bool = False,
) -> bool:
    """Sinh embedding, chống task stale; cho phép tin đã đóng khi chấm hồ sơ."""
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
    """Task định kỳ gọi service để chuyển các tin quá hạn sang EXPIRED."""
    from apps.jobs.services import expire_jobs as expire_jobs_service

    return expire_jobs_service()
