"""Django-Q tasks xử lý CV và embedding hồ sơ ứng viên."""
import json
import logging
import mimetypes

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone

from apps.candidates.models import CandidateProfile, Resume, ResumeImport
from integrations.gemini.embeddings import (
    current_candidate_embedding_signature,
    embed_document,
)
from apps.core.embedding_text_builders import build_candidate_text


logger = logging.getLogger(__name__)


RESUME_PARSE_PROMPT = """
Phân tích CV sau và trả về đúng một JSON object. Không thêm markdown.
Các key cần có: full_name, phone, headline, summary, educations, experiences,
skills. educations là mảng object gồm school_name, major, degree, start_date,
end_date, description. experiences là mảng object gồm company_name, position,
start_date, end_date, is_current, description. Ngày dùng YYYY-MM-DD hoặc null.
skills là mảng string. Không suy diễn thông tin không có trong CV; field văn bản
dùng chuỗi rỗng, ngày dùng null và danh sách dùng mảng rỗng khi thiếu dữ liệu.
""".strip()


def _get_client():
    """Khởi tạo Gemini client và báo lỗi cấu hình rõ ràng cho Django-Q."""
    if not settings.GEMINI_API_KEY:
        raise ImproperlyConfigured("GEMINI_API_KEY chưa được cấu hình.")
    from google import genai

    return genai.Client(api_key=settings.GEMINI_API_KEY)


def _parse_json_response(text: str) -> dict:
    """Loại bỏ code fence phổ biến trước khi giải mã JSON Gemini trả về."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```")
        cleaned = cleaned.removesuffix("```").strip()
    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise ValueError("Kết quả parse CV không phải JSON object.")
    return data


def _normalize_parsed_data(data: dict) -> dict:
    """Đổi null từ Gemini về giá trị hợp lệ cho các field model không-null.
    Bỏ qua entry thiếu required field (school_name / company_name + position)."""
    normalized = dict(data)
    for field in ("full_name", "phone", "headline", "summary"):
        if normalized.get(field) is None:
            normalized[field] = ""

    collections = {
        "educations": ("school_name", "major", "degree", "description"),
        "experiences": ("company_name", "position", "description"),
    }
    for collection, text_fields in collections.items():
        items = normalized.get(collection) or []
        normalized[collection] = []
        for item in items:
            if not isinstance(item, dict):
                continue

            # Skip entry thiếu field bắt buộc theo model
            if collection == "educations" and not item.get("school_name"):
                logger.warning("Bỏ qua education thiếu school_name: %s", item)
                continue
            if collection == "experiences" and not (item.get("company_name") and item.get("position")):
                logger.warning("Bỏ qua experience thiếu company_name/position: %s", item)
                continue

            clean_item = dict(item)
            for field in text_fields:
                if clean_item.get(field) is None or field not in clean_item:
                    clean_item[field] = ""
            if collection == "experiences" and clean_item.get("is_current") is None:
                clean_item["is_current"] = False
            normalized[collection].append(clean_item)

    normalized["skills"] = [
        skill.strip()
        for skill in (normalized.get("skills") or [])
        if isinstance(skill, str) and skill.strip()
    ]
    return normalized


def parse_resume(resume_id: str) -> dict:
    """Gửi CV lên Gemini, lưu JSON thô và kích hoạt tạo lại embedding."""
    from google.genai import types

    from apps.candidates import serializers, services

    resume = Resume.objects.select_related("candidate").get(pk=resume_id)
    if resume.parse_status == Resume.ParseStatus.SUCCESS:
        return resume.raw_extracted_json or {}

    try:
        with resume.file.open("rb") as source:
            file_data = source.read()
        mime_type = (
            mimetypes.guess_type(resume.original_filename)[0]
            or "application/octet-stream"
        )
        client = _get_client()
        response = client.models.generate_content(
            model=settings.GEMINI_PARSER_MODEL,
            contents=[
                RESUME_PARSE_PROMPT,
                types.Part.from_bytes(data=file_data, mime_type=mime_type),
            ],
        )
        raw_data = _parse_json_response(response.text)
        normalized_data = _normalize_parsed_data(raw_data)
        serializer = serializers.ResumeParsedDataSerializer(data=normalized_data)
        serializer.is_valid(raise_exception=True)
        preview = serializers.ResumeParsedDataSerializer(
            serializer.validated_data
        ).data
        services.mark_resume_parsed(resume, raw_data, preview)
        return raw_data
    except Exception as exc:
        services.mark_resume_parse_failed(resume, str(exc))
        raise


def parse_resume_import(resume_import_id: str) -> dict:
    """Gửi CV (ResumeImport) lên Gemini, lưu kết quả parse vào ResumeImport."""
    from google.genai import types

    from apps.candidates import serializers, services

    resume_import = ResumeImport.objects.select_related("candidate").get(pk=resume_import_id)
    if resume_import.parse_status == ResumeImport.ParseStatus.SUCCESS:
        return resume_import.raw_extracted_json or {}

    try:
        with resume_import.file.open("rb") as source:
            file_data = source.read()
        mime_type = (
            mimetypes.guess_type(resume_import.original_filename)[0]
            or "application/octet-stream"
        )
        client = _get_client()
        response = client.models.generate_content(
            model=settings.GEMINI_PARSER_MODEL,
            contents=[
                RESUME_PARSE_PROMPT,
                types.Part.from_bytes(data=file_data, mime_type=mime_type),
            ],
        )
        raw_data = _parse_json_response(response.text)
        normalized_data = _normalize_parsed_data(raw_data)
        serializer = serializers.ResumeParsedDataSerializer(data=normalized_data)
        serializer.is_valid(raise_exception=True)
        preview = serializers.ResumeParsedDataSerializer(
            serializer.validated_data
        ).data
        services.mark_resume_import_parsed(resume_import, raw_data, preview)
        return raw_data
    except Exception as exc:
        services.mark_resume_import_failed(resume_import, str(exc))
        raise


def generate_candidate_embedding(profile_id: str, profile_version: int) -> bool:
    """Sinh embedding và chỉ lưu nếu profile chưa đổi sang version mới hơn."""
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
    """Hậu điều kiện UC-01: bản ghi ResumeImport không được dùng trong 24h
    sẽ bị xóa (kèm file vật lý) để giải phóng dung lượng DB/storage."""
    from apps.candidates import services

    expired = ResumeImport.objects.filter(
        expires_at__lt=timezone.now(),
    ).exclude(parse_status=ResumeImport.ParseStatus.PENDING)
    # PENDING quá hạn cũng xóa: worker đã fail/timeout hoặc task mất.
    count = 0
    for resume_import in expired.iterator():
        services.delete_resume_import(resume_import)
        count += 1
    return count
