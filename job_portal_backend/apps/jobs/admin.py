from django.contrib import admin

from apps.jobs.models import JobPost, JobSkill


class JobSkillInline(admin.TabularInline):
    model = JobSkill
    extra = 1


@admin.register(JobPost)
class JobPostAdmin(admin.ModelAdmin):
    list_display = (
        "title", "company", "status", "workplace_type", "job_type",
        "experience_level", "required_education_level", "location", "published_at",
    )
    list_filter = (
        "status", "workplace_type", "job_type", "experience_level",
        "required_education_level", "location",
    )
    search_fields = ("title", "company__name")
    inlines = [JobSkillInline]
    exclude = ("embedding",)
