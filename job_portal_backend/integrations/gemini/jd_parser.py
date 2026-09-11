"""Phân tích và kiểm tra JD bằng Gemini."""
from django.conf import settings

from apps.jobs.models import JobPost
from apps.jobs.serializers import JobDescriptionParsedDataSerializer
from apps.skills.utils import normalize_alias
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


JD_PARSE_PROMPT = """
Phân tích Job Description sau và trả về đúng một JSON object, không markdown.
Các key: title, description, requirements, benefits, location, job_type,
    workplace_type, experience_level, required_education_level, salary_min, salary_max, salary_negotiable,
    expires_at, skills.
    location chỉ là Hồ Chí Minh, Hà Nội, Đà Nẵng hoặc chuỗi rỗng.
    workplace_type chỉ là ONSITE, HYBRID hoặc REMOTE.
    job_type chỉ là FULL_TIME, PART_TIME hoặc CONTRACT.
    experience_level chỉ là ENTRY, JUNIOR, MID_SENIOR, LEAD hoặc chuỗi rỗng.
    required_education_level chỉ là NONE, ASSOCIATE, BACHELOR, MASTER, PHD
    hoặc null khi JD không khai rõ; không suy diễn từ chức danh hay tên trường.
    Thực tập/Fresher thuộc ENTRY; Remote là workplace_type, không phải job_type.
salary_min/salary_max là số nguyên VND hoặc null. expires_at dùng ISO 8601 hoặc null.
skills là mảng object {"name": tên kỹ năng, "is_required": true/false}; true
chỉ khi JD nêu bắt buộc, false cho kỹ năng ưu tiên/nice-to-have. Không suy diễn dữ liệu không có trong JD; field văn bản
dùng chuỗi rỗng, danh sách dùng mảng rỗng và giá trị không xác định dùng null.
""".strip()

JD_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "title": {"type": "STRING"},
        "description": {"type": "STRING"},
        "requirements": {"type": "STRING"},
        "benefits": {"type": "STRING"},
        "location": {"type": "STRING"},
        "job_type": {"type": "STRING", "nullable": True},
        "workplace_type": {"type": "STRING", "nullable": True},
        "experience_level": {"type": "STRING"},
        "required_education_level": {"type": "STRING", "nullable": True},
        "salary_min": {"type": "INTEGER", "nullable": True},
        "salary_max": {"type": "INTEGER", "nullable": True},
        "salary_negotiable": {"type": "BOOLEAN"},
        "expires_at": {"type": "STRING", "nullable": True},
        "skills": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "name": {"type": "STRING"},
                    "is_required": {"type": "BOOLEAN"},
                },
            },
        },
    },
}


def _normalize_required_flag(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().lower() in {"true", "false"}:
        return value.strip().lower() == "true"
    return False


def normalize_jd_data(data: dict) -> dict:
    """Chuẩn hóa các trường JD mà không thay đổi giá trị mặc định hiện có của form."""
    normalized = dict(data)
    for field in (
        "title",
        "description",
        "requirements",
        "benefits",
        "experience_level",
    ):
        if normalized.get(field) is None:
            normalized[field] = ""
    if normalized.get("job_type") is None:
        normalized["job_type"] = "FULL_TIME"
    if normalized.get("workplace_type") is None:
        normalized["workplace_type"] = "ONSITE"

    raw_location = normalize_alias(str(normalized.get("location") or "")).replace(
        "đ", "d"
    )
    if any(
        value in raw_location
        for value in ("ho chi minh", "hcm", "sai gon", "saigon")
    ):
        normalized["location"] = JobPost.Location.HO_CHI_MINH
    elif any(value in raw_location for value in ("ha noi", "hanoi")):
        normalized["location"] = JobPost.Location.HANOI
    elif "da nang" in raw_location:
        normalized["location"] = JobPost.Location.DA_NANG
    else:
        normalized["location"] = ""
    if normalized.get("salary_negotiable") is None:
        normalized["salary_negotiable"] = False

    skill_flags = {}
    skill_names = {}
    for value in normalized.get("skills") or []:
        if isinstance(value, dict):
            name = value.get("name")
            is_required = _normalize_required_flag(value.get("is_required"))
        else:
            name = value
            is_required = True
        if not isinstance(name, str) or not name.strip():
            continue
        key = normalize_alias(name)
        skill_names.setdefault(key, name.strip())
        skill_flags[key] = skill_flags.get(key, False) or is_required
    normalized["skills"] = list(skill_names.values())
    normalized["_skill_required_flags"] = skill_flags
    return normalized


def parse_job_description(
    *, filename: str, mime_type: str | None, file_data: bytes
) -> ParsedDocumentResult:
    """Phân tích JD và trả về dữ liệu thô cùng dữ liệu form đã được serializer kiểm tra."""
    from google.genai import types

    document_content = prepare_document_input(filename, mime_type, file_data)
    try:
        response = get_gemini_client().models.generate_content(
            model=settings.GEMINI_PARSER_MODEL,
            contents=[JD_PARSE_PROMPT, document_content],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=JD_RESPONSE_SCHEMA,
            ),
        )
    except GeminiConfigurationError:
        raise
    except Exception as exc:
        raise GeminiRequestError("Không thể gọi Gemini để phân tích JD.") from exc

    raw_data = parse_json_object_response(response)
    normalized = normalize_jd_data(raw_data)
    serializer = JobDescriptionParsedDataSerializer(data=normalized)
    serializer.is_valid(raise_exception=True)
    parsed = dict(serializer.validated_data)
    parsed["_skill_required_flags"] = normalized.get("_skill_required_flags", {})
    return ParsedDocumentResult(raw_data=raw_data, validated_data=parsed)
