from django.contrib import admin

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
        "updated_by",
    )
    list_filter = ("is_active",)

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        if obj.is_active:
            # Chỉ 1 config được active tại một thời điểm.
            MatchingWeightConfig.objects.exclude(pk=obj.pk).update(is_active=False)
        super().save_model(request, obj, form, change)


@admin.register(CandidateSkill)
class CandidateSkillAdmin(admin.ModelAdmin):
    list_display = ("candidate", "skill", "level", "source", "years_of_experience")
    list_filter = ("source", "level")
    search_fields = ("candidate__full_name", "skill__name")
