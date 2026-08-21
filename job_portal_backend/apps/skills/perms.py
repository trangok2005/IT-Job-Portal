"""skills permissions."""
from rest_framework import permissions


class IsAdminRole(permissions.BasePermission):
    """Chỉ tài khoản role ADMIN mới quản trị skill / tiêu chí phù hợp."""

    message = "Chỉ Admin mới được thực hiện thao tác này."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_admin_role
        )