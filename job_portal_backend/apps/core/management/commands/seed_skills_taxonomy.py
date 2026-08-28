"""
Seed duy nhất cho Skill Taxonomy - đọc dữ liệu từ skill_taxonomy_seed.json
nằm cùng thư mục. Chạy lại an toàn (idempotent):
- Category: get_or_create theo name.
- Skill: get_or_create theo name (slug tự sinh unique, phòng 'C#'/'C++' cùng slug).
- SkillAlias: bỏ qua alias đã tồn tại (tránh vi phạm unique alias_text /
  normalized_text).
"""
import json

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.skills.models import Skill, SkillAlias, SkillCategory
from apps.skills.utils import make_unique_slug, normalize_alias


class Command(BaseCommand):
    help = "Seed taxonomy skill tu skill_taxonomy_seed.json (idempotent)."

    def handle(self, *args, **options):
        seed_path = (
            settings.BASE_DIR / "apps" / "core" / "seed_data"
            / "skill_taxonomy_seed.json"
        )
        if not seed_path.exists():
            self.stderr.write(self.style.ERROR(f"Khong tim thay {seed_path}"))
            return

        data = json.loads(seed_path.read_text(encoding="utf-8"))

        created_cat = created_skill = created_alias = 0

        for entry in data["skills"]:
            category, cat_created = SkillCategory.objects.get_or_create(name=entry["category"])
            if cat_created:
                created_cat += 1

            skill, skill_created = Skill.objects.get_or_create(
                name=entry["name"],
                defaults={
                    "slug": make_unique_slug(entry["name"]),
                    "category": category,
                    "status": Skill.Status.APPROVED,
                    "source": Skill.Source.ADMIN_MANUAL,
                },
            )
            if skill_created:
                created_skill += 1
            elif skill.category_id != category.pk:
                skill.category = category
                skill.save(update_fields=["category", "updated_at"])

            for alias_text in entry.get("aliases") or []:
                if SkillAlias.objects.filter(alias_text=alias_text).exists():
                    continue
                normalized = normalize_alias(alias_text)
                if SkillAlias.objects.filter(normalized_text=normalized).exists():
                    continue
                SkillAlias.objects.create(
                    skill=skill, alias_text=alias_text, normalized_text=normalized,
                )
                created_alias += 1

        self.stdout.write(self.style.SUCCESS(
            f"Seed xong: +{created_cat} category, +{created_skill} skill, "
            f"+{created_alias} alias. "
            f"Tong: {SkillCategory.objects.count()} category, "
            f"{Skill.objects.count()} skill, {SkillAlias.objects.count()} alias."
        ))
