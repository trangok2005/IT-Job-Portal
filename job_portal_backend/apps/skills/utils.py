"""skills/utils.py — hàm chuẩn hoá tái dùng (slug duy nhất, alias normalized)."""
import re
import unicodedata

from django.utils.text import slugify


def strip_accents(text: str) -> str:
    text = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn")


def normalize_alias(text: str) -> str:
    """Lowercase + bỏ dấu + gom khoảng trắng → SkillAlias.normalized_text
    dùng để fuzzy-match (rapidfuzz) trước khi coi là skill mới hoàn toàn."""
    return re.sub(r"\s+", " ", strip_accents(text).strip().casefold())


def make_unique_slug(base: str, exclude_pk=None) -> str:
    """slugify(name) và thêm hậu tố nếu trùng (vd 'C#' và 'C++' đều -> 'c')."""
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