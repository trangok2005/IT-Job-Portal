"""Trích xuất JD bằng Gemini cho UC-02 trước khi tạo bản nháp."""
import json
import mimetypes

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from apps.jobs.models import JobPost
from apps.skills.services import resolve_savable_skill
from apps.skills.utils import normalize_alias
from common.document_extraction import extract_docx_text as _extract_docx_text


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


def _get_client():
    if not settings.GEMINI_API_KEY:
        raise ImproperlyConfigured("GEMINI_API_KEY chưa được cấu hình.")
    from google import genai
    from google.genai import types

    return genai.Client(
        api_key=settings.GEMINI_API_KEY,
        http_options=types.HttpOptions(timeout=settings.EMBEDDING_TIMEOUT_MS),
    )


def _parse_json_response(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```")
        cleaned = cleaned.removesuffix("```").strip()
    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise ValueError("Kết quả parse JD không phải JSON object.")
    return data


def _normalize_data(data: dict) -> dict:
    normalized = dict(data)
    for field in (
        "title", "description", "requirements", "benefits", "experience_level",
    ):
        if normalized.get(field) is None:
            normalized[field] = ""
    if normalized.get("job_type") is None:
        normalized["job_type"] = "FULL_TIME"
    if normalized.get("workplace_type") is None:
        normalized["workplace_type"] = "ONSITE"
    raw_location = normalize_alias(str(normalized.get("location") or "")).replace("đ", "d")
    if any(value in raw_location for value in ("ho chi minh", "hcm", "sai gon", "saigon")):
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
            is_required = value.get("is_required") is True
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


def _resolve_approved_skills(
    names: list[str], required_flags: dict | None = None
) -> tuple[list[dict], list[str]]:
    """Phân giải tên skill bằng ``resolve_savable_skill`` dùng chung.

    Skill lạ được tạo ở trạng thái PENDING và đưa vào danh sách khớp; chỉ tên
    rỗng hoặc không hợp lệ mới được đưa vào danh sách không khớp.
    """
    matched = []
    unmatched = []
    seen_ids = set()
    for name in names:
        try:
            skill = resolve_savable_skill(name)
        except ValueError:
            unmatched.append(name)
            continue
        if skill.pk not in seen_ids:
            seen_ids.add(skill.pk)
            matched.append({
                "id": str(skill.pk),
                "name": skill.name,
                "status": skill.status,
                "is_required": (required_flags or {}).get(normalize_alias(name), True),
            })
    return matched, unmatched


def parse_job_description(file) -> tuple[dict, dict]:
    """Trả JSON thô từ Gemini và dữ liệu đã kiểm tra để điền biểu mẫu."""
    from google.genai import types

    from apps.jobs.serializers import JobDescriptionParsedDataSerializer

    file_data = file.read()
    mime_type = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
    if file.name.lower().endswith(".docx"):
        document_content = _extract_docx_text(file_data)
    else:
        document_content = types.Part.from_bytes(data=file_data, mime_type=mime_type)
    client = _get_client()
    response = client.models.generate_content(
        model=settings.GEMINI_PARSER_MODEL,
        contents=[
            JD_PARSE_PROMPT,
            document_content,
        ],
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    if not response.text:
        raise ValueError("Gemini không trả về nội dung JD.")
    raw_data = _parse_json_response(response.text)
    normalized = _normalize_data(raw_data)
    serializer = JobDescriptionParsedDataSerializer(data=normalized)
    serializer.is_valid(raise_exception=True)
    parsed = dict(serializer.validated_data)
    matched, unmatched = _resolve_approved_skills(
        parsed.get("skills", []),
        normalized.get("_skill_required_flags"),
    )
    parsed["required_skills"] = [item["id"] for item in matched]
    parsed["resolved_skills"] = matched
    parsed["unmatched_skills"] = unmatched
    return raw_data, parsed
