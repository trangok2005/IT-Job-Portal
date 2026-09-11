"""Chuẩn bị nội dung tài liệu được hỗ trợ cho Gemini parser."""
import mimetypes
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

from common.document_extraction import extract_docx_text


class DocumentInputError(ValueError):
    """Tài liệu được cung cấp rỗng hoặc không được hỗ trợ."""


SUPPORTED_DOCUMENT_MIME_TYPES = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def prepare_document_input(
    filename: str,
    mime_type: str | None,
    file_data: bytes,
):
    """Chuyển PDF/DOC/DOCX được hỗ trợ thành nội dung request Gemini."""
    if not file_data:
        raise DocumentInputError("Tài liệu không có nội dung.")

    suffix = Path(filename).suffix.lower()
    expected_mime_type = SUPPORTED_DOCUMENT_MIME_TYPES.get(suffix)
    if expected_mime_type is None:
        raise DocumentInputError("Tài liệu chỉ hỗ trợ file PDF, DOC hoặc DOCX.")
    if suffix == ".docx":
        try:
            return extract_docx_text(file_data)
        except (KeyError, OSError, ValueError, zipfile.BadZipFile, ET.ParseError) as exc:
            raise DocumentInputError("File DOCX không hợp lệ hoặc không có nội dung.") from exc

    from google.genai import types

    resolved_mime_type = mime_type or mimetypes.guess_type(filename)[0]
    if resolved_mime_type != expected_mime_type:
        resolved_mime_type = expected_mime_type
    return types.Part.from_bytes(data=file_data, mime_type=resolved_mime_type)
