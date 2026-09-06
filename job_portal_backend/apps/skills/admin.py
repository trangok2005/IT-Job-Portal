from django.contrib import admin
from django.db import transaction

from apps.skills.models import CandidateSkill, MatchingWeightConfig, Skill, SkillAlias, SkillCategory


class SkillAliasInline(admin.TabularInline):
    model = SkillAlias
    extra = 1


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    inlines = [SkillAliasInline]


@admin.register(SkillCategory)
class SkillCategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(MatchingWeightConfig)
class MatchingWeightConfigAdmin(admin.ModelAdmin):
    list_display = (
        "name", "is_active",
        "weight_semantic_similarity", "weight_skill_overlap",
        "weight_experience_match", "weight_education_match",
        "required_skill_multiplier",
        "updated_by",
    )
    list_filter = ("is_active",)

    @transaction.atomic
    def save_model(self, request, obj, form, change):
        configs = list(
            MatchingWeightConfig.objects.select_for_update().order_by("pk")
        )
        obj.updated_by = request.user
        if obj.is_active:
            # Chỉ 1 config được active tại một thời điểm.
            for other in configs:
                if other.pk != obj.pk and other.is_active:
                    other.is_active = False
                    other.save(update_fields=["is_active", "updated_at"])
        super().save_model(request, obj, form, change)


@admin.register(CandidateSkill)
class CandidateSkillAdmin(admin.ModelAdmin):
    list_display = ("candidate", "skill", "years_of_experience")
    search_fields = ("candidate__full_name", "skill__name")
