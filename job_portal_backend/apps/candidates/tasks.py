"""Các task nền xử lý CV và embedding hồ sơ candidate."""
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

# Số lần tối đa một bản ghi được gửi Gemini parse; vượt quá sẽ FAILED vĩnh viễn
# thay vì để broker re-present vô hạn (tiêu quota khi Gemini lỗi kéo dài).
MAX_PARSE_ATTEMPTS = 3


def _claim_parse_attempt(record_id: str) -> datetime | None:
    """Nhận đúng một lượt giao để các callback đồng thời không phân tích hai lần."""
    now = timezone.now()
    lease_expired_at = now - timedelta(seconds=settings.TASK_PROCESSING_LEASE_SECONDS)
    claimed = ResumeImport.objects.filter(
        pk=record_id,
        parse_attempts__lt=MAX_PARSE_ATTEMPTS,
    ).filter(
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
    ).update(
        parse_status=ResumeImport.ParseStatus.PROCESSING,
        parse_attempts=F("parse_attempts") + 1,
        parse_error_message="",
        updated_at=now,
    )
    return now if claimed else None


def parse_resume_import(resume_import_id: str) -> dict:
    """Gửi CV lên Gemini và lưu kết quả phân tích vào ResumeImport."""
    resume_import = (
        ResumeImport.objects.select_related("candidate")
        .filter(pk=resume_import_id)
        .first()
    )
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
        resume_import = ResumeImport.objects.filter(pk=resume_import_id).first()
        if resume_import is None:
            return {}
        if resume_import.parse_status in (
            ResumeImport.ParseStatus.SUCCESS,
            ResumeImport.ParseStatus.CONSUMED,
        ):
            return resume_import.parsed_data or {}
        if (
            resume_import.parse_status == ResumeImport.ParseStatus.PROCESSING
            and resume_import.parse_attempts < MAX_PARSE_ATTEMPTS
        ):
            raise RuntimeError("Resume import is already being processed.")
        if (
            resume_import.parse_status
            in [
                ResumeImport.ParseStatus.PENDING,
                ResumeImport.ParseStatus.PROCESSING,
                ResumeImport.ParseStatus.FAILED,
            ]
            and resume_import.parse_attempts >= MAX_PARSE_ATTEMPTS
        ):
            ResumeImport.objects.filter(
                pk=resume_import_id,
                parse_attempts__gte=MAX_PARSE_ATTEMPTS,
            ).filter(
                Q(
                    parse_status__in=[
                        ResumeImport.ParseStatus.PENDING,
                        ResumeImport.ParseStatus.FAILED,
                    ]
                )
                | Q(
                    parse_status=ResumeImport.ParseStatus.PROCESSING,
                    updated_at__lte=(
                        timezone.now()
                        - timedelta(seconds=settings.TASK_PROCESSING_LEASE_SECONDS)
                    ),
                )
            ).update(
                parse_status=ResumeImport.ParseStatus.FAILED,
                parse_error_message=(
                    f"Đã vượt quá {MAX_PARSE_ATTEMPTS} lần thử phân tích CV."
                ),
                updated_at=timezone.now(),
            )
        return {}

    resume_import.refresh_from_db()

    try:
        with resume_import.file.open("rb") as source:
            file_data = source.read()
        result = parse_resume_document(
            filename=resume_import.original_filename,
            mime_type=None,
            file_data=file_data,
        )
        ResumeImport.objects.filter(
            pk=resume_import_id,
            parse_status=ResumeImport.ParseStatus.PROCESSING,
            updated_at=claim_token,
        ).update(
            parsed_data=result.validated_data,
            parse_status=ResumeImport.ParseStatus.SUCCESS,
            parse_error_message="",
            updated_at=timezone.now(),
        )
        return result.raw_data
    except Exception as exc:
        logger.exception(
            "Resume import %s failed (%s)", resume_import_id, type(exc).__name__
        )
        ResumeImport.objects.filter(
            pk=resume_import_id,
            parse_status=ResumeImport.ParseStatus.PROCESSING,
            updated_at=claim_token,
        ).update(
            parse_status=ResumeImport.ParseStatus.FAILED,
            parse_error_message=(
                "Không thể đọc thông tin từ file CV. "
                f"Mã lỗi: {type(exc).__name__}."
            ),
            updated_at=timezone.now(),
        )
        raise


def generate_candidate_embedding(profile_id: str, profile_version: int) -> bool:
    """Sinh embedding và chỉ lưu nếu hồ sơ chưa chuyển sang version mới hơn."""
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
    """Xóa ResumeImport không dùng trong 24 giờ cùng file để giải phóng lưu trữ.

    Bản PENDING quá hạn cũng bị xóa vì là task mồ côi; hàm phân tích dùng
    ``.first()`` nên không lỗi nếu bản ghi vừa bị xóa.
    """
    from apps.candidates import services

    expired = ResumeImport.objects.filter(expires_at__lt=timezone.now())
    count = 0
    for resume_import in expired.iterator():
        services.delete_resume_import(resume_import)
        count += 1
    return count
