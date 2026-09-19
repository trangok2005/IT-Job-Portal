import html
import re
import unicodedata
from collections.abc import Iterable


_SCRIPT_STYLE_RE = re.compile(
    r"<(script|style)\b[^>]*>.*?</\1>",
    re.IGNORECASE | re.DOTALL,
)
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")
_EMAIL_RE = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+")
_PHONE_RE = re.compile(r"(?:\+?84|0)[\s.-]?\d{2,3}[\s.-]?\d{3}[\s.-]?\d{3,4}")
_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)


def clean_text_field(raw: str | None) -> str:
    """Loại markup và thông tin định danh khỏi input embedding."""
    if not raw:
        return ""
    text = unicodedata.normalize("NFKC", str(raw))
    text = html.unescape(text)
    text = _SCRIPT_STYLE_RE.sub(" ", text)
    text = _HTML_TAG_RE.sub(" ", text)
    text = _EMAIL_RE.sub(" ", text)
    text = _PHONE_RE.sub(" ", text)
    text = _URL_RE.sub(" ", text)
    text = _UUID_RE.sub(" ", text)
    return _WHITESPACE_RE.sub(" ", text).strip()


def clean_and_limit_text(raw: str | None, max_chars: int) -> str:
    cleaned = clean_text_field(raw)
    if len(cleaned) <= max_chars:
        return cleaned
    clipped = cleaned[:max_chars].rsplit(" ", 1)[0]
    return clipped or cleaned[:max_chars]


def build_labeled_text(fields: Iterable[tuple[str, str | None]]) -> str:
    lines = []
    for label, value in fields:
        cleaned = clean_text_field(value)
        if cleaned:
            lines.append(f"{label}: {cleaned}")
    return "\n".join(lines)


def build_skills_line(skill_names: Iterable[str]) -> str:
    cleaned = (clean_text_field(skill) for skill in skill_names)
    return ", ".join(dict.fromkeys(skill for skill in cleaned if skill))
