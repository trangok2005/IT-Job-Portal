"""Các hàm hỗ trợ kiểm tra response có cấu trúc từ Gemini."""
import json
from dataclasses import dataclass
from typing import Any


class StructuredOutputError(ValueError):
    """Gemini trả về response có cấu trúc rỗng hoặc không hợp lệ."""


@dataclass(frozen=True)
class ParsedDocumentResult:
    raw_data: dict
    validated_data: dict


def parse_json_object_response(response: Any) -> dict:
    """Đọc JSON object từ response Gemini, chấp nhận code fence bao ngoài."""
    if response is None:
        raise StructuredOutputError("Gemini không trả về response.")

    text = getattr(response, "text", None)
    if not isinstance(text, str) or not text.strip():
        raise StructuredOutputError("Gemini không trả về nội dung.")

    cleaned = text.strip()
    if cleaned.startswith("```"):
        first_line, separator, remainder = cleaned.partition("\n")
        if first_line.strip().lower() in {"```", "```json"}:
            cleaned = remainder if separator else ""
            if cleaned.rstrip().endswith("```"):
                cleaned = cleaned.rstrip()[:-3].rstrip()

    try:
        data = json.loads(cleaned)
    except (TypeError, json.JSONDecodeError) as exc:
        raise StructuredOutputError("Gemini trả về JSON không hợp lệ.") from exc
    if not isinstance(data, dict):
        raise StructuredOutputError("Gemini phải trả về một JSON object.")
    return data
