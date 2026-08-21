"""Gemini-backed JD extraction used by UC-02 before a draft is created."""
import json
import io
import mimetypes
import zipfile
import xml.etree.ElementTree as ET

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from apps.skills.models import Skill
from apps.skills.services import resolve_extracted_skill
from apps.skills.utils import normalize_alias


JD_PARSE_PROMPT = """
Phân tích Job Description sau và trả về đúng một JSON object, không markdown.
Các key: title, description, requirements, benefits, location, job_type,
experience_level, salary_min, salary_max, salary_negotiable, expires_at, skills.
job_type chỉ là FULL_TIME, PART_TIME, INTERNSHIP, CONTRACT hoặc REMOTE.
experience_level chỉ là INTERN, FRESHER, JUNIOR, MIDDLE, SENIOR, LEAD hoặc chuỗi rỗng.
salary_min/salary_max là số nguyên VND hoặc null. expires_at dùng ISO 8601 hoặc null.
skills là mảng tên kỹ năng. Không suy diễn dữ liệu không có trong JD; field văn bản
dùng chuỗi rỗng, danh sách dùng mảng rỗng và giá trị không xác định dùng null.
""".strip()


def _get_client():
    if not settings.GEMINI_API_KEY:
        raise ImproperlyConfigured("GEMINI_API_KEY chưa được cấu hình.")
    from google import genai

    return genai.Client(api_key=settings.GEMINI_API_KEY)


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
        "title", "description", "requirements", "benefits", "location",
        "experience_level",
    ):
        if normalized.get(field) is None:
            normalized[field] = ""
    if normalized.get("job_type") is None:
        normalized["job_type"] = "FULL_TIME"
    if normalized.get("salary_negotiable") is None:
        normalized["salary_negotiable"] = False
    seen = set()
    skills = []
    for value in normalized.get("skills") or []:
        if not isinstance(value, str) or not value.strip():
            continue
        key = normalize_alias(value)
        if key not in seen:
            seen.add(key)
            skills.append(value.strip())
    normalized["skills"] = skills
    return normalized


def _extract_docx_text(file_data: bytes) -> str:
    """Extract paragraph/table text from DOCX without executing embedded content."""
    with zipfile.ZipFile(io.BytesIO(file_data)) as archive:
        document = ET.fromstring(archive.read("word/document.xml"))
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs = []
    for paragraph in document.findall(".//w:p", namespace):
        text = "".join(
            node.text or "" for node in paragraph.findall(".//w:t", namespace)
        ).strip()
        if text:
            paragraphs.append(text)
    if not paragraphs:
        raise ValueError("File DOCX không có nội dung văn bản.")
    return "\n".join(paragraphs)


def _resolve_approved_skills(names: list[str]) -> tuple[list[str], list[str]]:
    matched = []
    unmatched = []
    seen_ids = set()
    for name in names:
        skill = resolve_extracted_skill(name, Skill.Source.JD_PARSING)
        if skill and skill.status == Skill.Status.APPROVED and skill.is_active:
            if skill.pk not in seen_ids:
                seen_ids.add(skill.pk)
                matched.append(str(skill.pk))
        else:
            unmatched.append(name)
    return matched, unmatched


def parse_job_description(file) -> tuple[dict, dict]:
    """Return raw Gemini JSON and validated form-ready data."""
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
    matched, unmatched = _resolve_approved_skills(parsed.get("skills", []))
    parsed["required_skills"] = matched
    parsed["unmatched_skills"] = unmatched
    return raw_data, parsed
