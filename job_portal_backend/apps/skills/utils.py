import re
import unicodedata

from django.utils.text import slugify


def strip_accents(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn")


def normalize_alias(text: str) -> str:
    """Giữ ký hiệu để C, C++ và C# không cùng một khóa."""
    return re.sub(r"\s+", " ", strip_accents(text).strip().casefold())


def make_unique_slug(base: str, exclude_pk=None) -> str:
    """Thêm hậu tố khi nhiều tên cho cùng một slug."""
    from apps.skills.models import Skill

    base_slug = slugify(base) or "skill"
    slug = base_slug
    counter = 2
    while True:
        qs = Skill.objects.filter(slug=slug)
        if exclude_pk:
            qs = qs.exclude(pk=exclude_pk)
        if not qs.exists():
            return slug
        slug = f"{base_slug}-{counter}"
        counter += 1
