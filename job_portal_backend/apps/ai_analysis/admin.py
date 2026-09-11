from django.contrib import admin

from apps.ai_analysis.models import ApplicationMatchResult


@admin.register(ApplicationMatchResult)
class ApplicationMatchResultAdmin(admin.ModelAdmin):
    list_display = (
        "application",
        "match_score",
        "status",
        "rule_version",
        "embedding_model_version",
        "created_at",
    )
    search_fields = ("application__candidate__full_name", "application__job__title")
    # Kết quả đối sánh là bất biến sau khi snapshot hồ sơ được chấm điểm.
    readonly_fields = [
        f.name for f in ApplicationMatchResult._meta.fields if f.name not in ("id",)
    ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
