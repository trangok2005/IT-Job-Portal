"""Role-based permissions shared across backend apps."""
from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    message = "Chỉ admin mới được thực hiện thao tác này."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_admin_role)


class IsCandidate(BasePermission):
    message = "Chỉ ứng viên mới được thực hiện thao tác này."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_candidate)


class IsEmployer(BasePermission):
    message = "Chỉ nhà tuyển dụng mới được thực hiện thao tác này."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_employer)


class IsEmployerOrAdmin(BasePermission):
    message = "Chỉ nhà tuyển dụng hoặc admin được thực hiện thao tác này."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.is_employer or user.is_admin_role)
        )


class HasBusinessRole(BasePermission):
    """Allow authenticated users with one of the supported business roles."""

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.is_candidate or user.is_employer or user.is_admin_role)
        )
