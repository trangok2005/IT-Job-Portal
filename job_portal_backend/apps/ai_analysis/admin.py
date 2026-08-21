from django.contrib import admin

from apps.ai_analysis.models import AIAnalysis


@admin.register(AIAnalysis)
class AIAnalysisAdmin(admin.ModelAdmin):
    list_display = (
        "application",
        "match_score",
        "candidate_embedding_version",
        "job_embedding_version",
        "inputs_are_stale",
        "computed_at",
    )
    search_fields = ("application__candidate__full_name", "application__job__title")
    # Điểm số do pipeline AI tính, không chỉnh sửa tay trong admin.
    readonly_fields = [f.name for f in AIAnalysis._meta.fields if f.name not in ("id",)]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
