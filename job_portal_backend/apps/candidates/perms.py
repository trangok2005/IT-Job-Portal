"""candidates permissions — business rules checked here, not in views."""
from rest_framework import permissions


class IsCandidate(permissions.BasePermission):
    """Chỉ tài khoản role CANDIDATE được thao tác hồ sơ của chính mình."""

    message = "Chỉ ứng viên mới được quản lý hồ sơ này."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_candidate
        )