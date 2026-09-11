"""Phân tích và kiểm tra CV ứng viên bằng Gemini."""
import logging

from django.conf import settings

from apps.candidates.serializers import ResumeParsedDataSerializer
from integrations.gemini.client import (
    GeminiConfigurationError,
    GeminiRequestError,
    get_gemini_client,
)
from integrations.gemini.document_input import prepare_document_input
from integrations.gemini.structured_output import (
    ParsedDocumentResult,
    parse_json_object_response,
)


logger = logging.getLogger(__name__)

RESUME_PARSE_PROMPT = """
Phân tích CV sau và trả về đúng một JSON object. Không thêm markdown.
Các key cần có: full_name, phone, headline, summary, educations, experiences,
skills. educations là mảng object gồm school_name, major, degree, degree_level,
is_completed, start_date, end_date, description; degree_level chỉ là NONE,
ASSOCIATE, BACHELOR, MASTER, PHD hoặc null. experiences là mảng object gồm company_name, position,
start_date, end_date, is_current, description. Ngày dùng YYYY-MM-DD hoặc null.
skills là mảng string. Không suy diễn thông tin không có trong CV; field văn bản
dùng chuỗi rỗng, ngày dùng null và danh sách dùng mảng rỗng khi thiếu dữ liệu.
""".strip()

RESUME_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "full_name": {"type": "STRING"},
        "phone": {"type": "STRING"},
        "headline": {"type": "STRING"},
        "summary": {"type": "STRING"},
        "educations": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "school_name": {"type": "STRING"},
                    "major": {"type": "STRING"},
                    "degree": {"type": "STRING"},
                    "degree_level": {"type": "STRING", "nullable": True},
                    "is_completed": {"type": "BOOLEAN"},
                    "start_date": {"type": "STRING", "nullable": True},
                    "end_date": {"type": "STRING", "nullable": True},
                    "description": {"type": "STRING"},
                },
            },
        },
        "experiences": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "company_name": {"type": "STRING"},
                    "position": {"type": "STRING"},
                    "start_date": {"type": "STRING", "nullable": True},
                    "end_date": {"type": "STRING", "nullable": True},
                    "is_current": {"type": "BOOLEAN"},
                    "description": {"type": "STRING"},
                },
            },
        },
        "skills": {"type": "ARRAY", "items": {"type": "STRING"}},
    },
}


def _normalize_boolean(value, *, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().lower() in {"true", "false"}:
        return value.strip().lower() == "true"
    raise ValueError("Giá trị boolean do Gemini trả về không hợp lệ.")


def normalize_resume_data(data: dict) -> dict:
    """Chuẩn hóa các trường CV đã trích xuất trước khi serializer kiểm tra."""
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
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                logger.warning("Bỏ qua %s[%s]: không phải object", collection, index)
                continue
            if collection == "educations" and not item.get("school_name"):
                logger.warning("Bỏ qua educations[%s]: thiếu school_name", index)
                continue
            if collection == "experiences" and not (
                item.get("company_name") and item.get("position")
            ):
                logger.warning(
                    "Bỏ qua experiences[%s]: thiếu company_name hoặc position", index
                )
                continue

            clean_item = dict(item)
            for field in text_fields:
                if clean_item.get(field) is None or field not in clean_item:
                    clean_item[field] = ""
            if collection == "experiences":
                clean_item["is_current"] = _normalize_boolean(
                    clean_item.get("is_current")
                )
            else:
                clean_item["is_completed"] = _normalize_boolean(
                    clean_item.get("is_completed")
                )
                # Học vấn do AI trích xuất phải được ứng viên xác nhận.
                clean_item["is_verified"] = False
            normalized[collection].append(clean_item)

    normalized["skills"] = [
        skill.strip()
        for skill in (normalized.get("skills") or [])
        if isinstance(skill, str) and skill.strip()
    ]
    return normalized


def parse_resume_document(
    *, filename: str, mime_type: str | None, file_data: bytes
) -> ParsedDocumentResult:
    """Phân tích CV và trả về dữ liệu thô cùng dữ liệu đã được serializer kiểm tra."""
    from google.genai import types

    document_content = prepare_document_input(filename, mime_type, file_data)
    try:
        response = get_gemini_client().models.generate_content(
            model=settings.GEMINI_PARSER_MODEL,
            contents=[RESUME_PARSE_PROMPT, document_content],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=RESUME_RESPONSE_SCHEMA,
            ),
        )
    except GeminiConfigurationError:
        raise
    except Exception as exc:
        raise GeminiRequestError("Không thể gọi Gemini để phân tích CV.") from exc

    raw_data = parse_json_object_response(response)
    serializer = ResumeParsedDataSerializer(data=normalize_resume_data(raw_data))
    serializer.is_valid(raise_exception=True)
    validated_data = dict(ResumeParsedDataSerializer(serializer.validated_data).data)
    return ParsedDocumentResult(raw_data=raw_data, validated_data=validated_data)
