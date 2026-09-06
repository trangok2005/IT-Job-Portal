from django.contrib import admin

from apps.applications.models import ApplicationStatusHistory, JobApplication


class ApplicationStatusHistoryInline(admin.TabularInline):
    model = ApplicationStatusHistory
    extra = 0
    readonly_fields = (
        "from_status",
        "to_status",
        "changed_by",
        "note",
        "candidate_message",
        "notification_status",
        "notification_attempts",
        "notification_error",
        "notification_sent_at",
        "created_at",
    )
    can_delete = False


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ("candidate", "job", "status", "match_status", "updated_at")
    list_filter = ("status", "match_status")
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
        "match_status",
        "match_error",
        "match_attempts",
    )

    def has_add_permission(self, request):
        """Chỉ cho phép tạo hồ sơ ứng tuyển qua service nghiệp vụ."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Không cho phép xóa hồ sơ ứng tuyển theo đặc tả nghiệp vụ."""
        return False
