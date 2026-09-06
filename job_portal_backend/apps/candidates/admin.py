from django.contrib import admin

from apps.candidates.models import CandidateProfile, Education, Experience, Resume


class EducationInline(admin.TabularInline):
    model = Education
    extra = 0


class ExperienceInline(admin.TabularInline):
    model = Experience
    extra = 0


class ResumeInline(admin.TabularInline):
    model = Resume
    extra = 0
    fields = ("original_filename", "is_primary")


@admin.register(CandidateProfile)
class CandidateProfileAdmin(admin.ModelAdmin):
    list_display = ("full_name", "user", "profile_version", "embedding_is_stale", "is_public")
    search_fields = ("full_name", "user__email")
    inlines = [EducationInline, ExperienceInline, ResumeInline]
    # embedding là vector 768 chiều -> không hiển thị trực tiếp trong list/edit form
    exclude = ("embedding",)
