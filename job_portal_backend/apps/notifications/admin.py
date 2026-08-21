from django.contrib import admin

from apps.notifications.models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "recipient", "notif_type", "channel", "status", "is_read", "sent_at")
    list_filter = ("notif_type", "channel", "status", "is_read")
    search_fields = ("recipient__email", "title")
    readonly_fields = [
        field.name for field in Notification._meta.fields if field.name != "id"
    ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
