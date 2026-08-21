"""Role permissions for account administration."""
from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    """Allow only authenticated users with the ADMIN business role."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_admin_role
        )
