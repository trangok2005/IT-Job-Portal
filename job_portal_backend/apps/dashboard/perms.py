"""Dashboard permissions."""
from rest_framework import permissions


class HasDashboardRole(permissions.BasePermission):
    """Allow the three supported business roles to read their dashboard."""

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.is_candidate or user.is_employer or user.is_admin_role)
        )
