"""Quyền truy cập đối tượng dành riêng cho công ty."""
from rest_framework import permissions


class IsCompanyOwner(permissions.BasePermission):
    """Chủ hồ sơ công ty mới được gửi lại hồ sơ đó."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        return request.user.is_employer and obj.owner_id == request.user.pk
