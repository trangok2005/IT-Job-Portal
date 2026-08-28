from django.contrib import admin

from apps.applications.models import ApplicationStatusHistory, JobApplication


class ApplicationStatusHistoryInline(admin.TabularInline):
    model = ApplicationStatusHistory
    extra = 0
    readonly_fields = ("from_status", "to_status", "changed_by", "note", "created_at")
    can_delete = False


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ("candidate", "job", "status", "updated_at")
    list_filter = ("status",)
    search_fields = ("candidate__full_name", "job__title")
    inlines = [ApplicationStatusHistoryInline]
    readonly_fields = (
        "status",
        "profile_snapshot",
        "job_snapshot",
        "matching_weight_snapshot",
        "candidate_embedding_snapshot",
        "job_embedding_snapshot",
        "snapshot_created_at",
    )

    def has_add_permission(self, request):
        """Applications must be created through the business service."""
        return False

    def has_delete_permission(self, request, obj=None):
        """The charter has no use case for deleting an application."""
        return False
