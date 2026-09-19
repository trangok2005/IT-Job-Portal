import logging
from datetime import datetime, timedelta

from django.conf import settings
from django.db.models import F, Q
from django.utils import timezone

from apps.candidates.models import CandidateProfile, ResumeImport
from apps.core.embedding_text_builders import build_candidate_text
from integrations.gemini.embeddings import (
    current_candidate_embedding_signature,
    embed_document,
)
from integrations.gemini.resume_parser import parse_resume_document


logger = logging.getLogger(__name__)

# Giới hạn broker retry để không cạn quota Gemini khi dịch vụ lỗi dài.
MAX_PARSE_ATTEMPTS = 3


def _retryable_imports(record_id: str, now: datetime):
    """Chỉ nhận bản chưa chạy, bị lỗi hoặc đã hết lease."""
    lease_expired_at = now - timedelta(seconds=settings.TASK_PROCESSING_LEASE_SECONDS)
    return ResumeImport.objects.filter(pk=record_id).filter(
        Q(
            parse_status__in=[
                ResumeImport.ParseStatus.PENDING,
                ResumeImport.ParseStatus.FAILED,
            ]
        )
        | Q(
            parse_status=ResumeImport.ParseStatus.PROCESSING,
            updated_at__lte=lease_expired_at,
        )
    )


def _claim_parse_attempt(record_id: str) -> datetime | None:
    """Claim bằng một UPDATE để hai worker không cùng nhận việc."""
    now = timezone.now()
    claimed = _retryable_imports(record_id, now).filter(
        parse_attempts__lt=MAX_PARSE_ATTEMPTS,
    ).update(
        parse_status=ResumeImport.ParseStatus.PROCESSING,
        parse_attempts=F("parse_attempts") + 1,
        parse_error_message="",
        updated_at=now,
    )
    return now if claimed else None


def _handle_unclaimed_import(record_id: str) -> dict:
    resume_import = ResumeImport.objects.filter(pk=record_id).first()
    if resume_import is None:
        return {}
    if resume_import.parse_status in (
        ResumeImport.ParseStatus.SUCCESS,
        ResumeImport.ParseStatus.CONSUMED,
    ):
        return resume_import.parsed_data or {}
    if resume_import.parse_attempts >= MAX_PARSE_ATTEMPTS:
        now = timezone.now()
        _retryable_imports(record_id, now).filter(
            parse_attempts__gte=MAX_PARSE_ATTEMPTS,
        ).update(
            parse_status=ResumeImport.ParseStatus.FAILED,
            parse_error_message=f"Đã vượt quá {MAX_PARSE_ATTEMPTS} lần thử phân tích CV.",
            updated_at=now,
        )
        return {}
    if resume_import.parse_status == ResumeImport.ParseStatus.PROCESSING:
        raise RuntimeError("Resume import is already being processed.")
    return {}


def parse_resume_import(resume_import_id: str) -> dict:
    resume_import = ResumeImport.objects.filter(pk=resume_import_id).first()
    if resume_import is None:
        logger.warning(
            "ResumeImport %s disappeared before parsing (cleanup/cancel)",
            resume_import_id,
        )
        return {}
    if resume_import.parse_status in [
        ResumeImport.ParseStatus.SUCCESS,
        ResumeImport.ParseStatus.CONSUMED,
    ]:
        return resume_import.parsed_data or {}

    claim_token = _claim_parse_attempt(resume_import_id)
    if claim_token is None:
        return _handle_unclaimed_import(resume_import_id)

    # updated_at giữ quyền ghi của lượt này, kể cả khi worker khác đã retry.
    owned_attempt = ResumeImport.objects.filter(
        pk=resume_import_id,
        parse_status=ResumeImport.ParseStatus.PROCESSING,
        updated_at=claim_token,
    )
    resume_import = owned_attempt.first()
    if resume_import is None:
        return {}

    try:
        with resume_import.file.open("rb") as source:
            file_data = source.read()
        result = parse_resume_document(
            filename=resume_import.original_filename,
            mime_type=None,
            file_data=file_data,
        )
        parsed_data = result.validated_data
        owned_attempt.update(
            parsed_data=parsed_data,
            parse_status=ResumeImport.ParseStatus.SUCCESS,
            parse_error_message="",
            updated_at=timezone.now(),
        )
        return parsed_data
    except Exception as exc:
        if not ResumeImport.objects.filter(pk=resume_import_id).exists():
            return {}
        logger.exception(
            "Resume import %s failed (%s)", resume_import_id, type(exc).__name__
        )
        owned_attempt.update(
            parse_status=ResumeImport.ParseStatus.FAILED,
            parse_error_message=(
                "Không thể đọc thông tin từ file CV. "
                f"Mã lỗi: {type(exc).__name__}."
            ),
            updated_at=timezone.now(),
        )
        raise


def generate_candidate_embedding(profile_id: str, profile_version: int) -> bool:
    """Bỏ kết quả nếu profile version đã đổi trong lúc chạy."""
    profile = (
        CandidateProfile.objects.filter(pk=profile_id)
        .prefetch_related(
            "educations",
            "experiences",
            "candidate_skills__skill",
        )
        .first()
    )
    if profile is None or profile.profile_version != profile_version:
        return False

    content = build_candidate_text(profile)
    if not content:
        return False

    values = embed_document(content)

    updated = CandidateProfile.objects.filter(
        pk=profile_id,
        profile_version=profile_version,
    ).update(
        embedding=values,
        embedding_version=profile_version,
        embedding_signature=current_candidate_embedding_signature(),
        embedding_updated_at=timezone.now(),
    )
    return bool(updated)


def cleanup_expired_resume_imports() -> int:
    """Xóa cả bản PENDING quá hạn; worker chịu được record vừa bị xóa."""
    from apps.candidates import services

    expired = ResumeImport.objects.filter(expires_at__lte=timezone.now())
    count = 0
    for resume_import in expired.iterator():
        services.delete_resume_import(resume_import)
        count += 1
    return count
