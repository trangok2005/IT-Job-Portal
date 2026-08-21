"""companies permissions — business rules checked here, not in views."""
from rest_framework import permissions


class IsAdminRole(permissions.BasePermission):
    message = "Chỉ admin mới thực hiện được thao tác này."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_admin_role
        )


class IsEmployer(permissions.BasePermission):
    message = "Chỉ nhà tuyển dụng mới quản lý hồ sơ công ty."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_employer
        )


class IsCompanyOwner(permissions.BasePermission):
    """Chủ hồ sơ công ty mới được gửi lại hồ sơ đó."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        return request.user.is_employer and obj.owner_id == request.user.pk
