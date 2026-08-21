from django.contrib import admin

from apps.accounts.models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "username", "role", "is_active", "auth_provider", "created_at")
    list_filter = ("role", "is_active", "auth_provider")
    search_fields = ("email", "username")
