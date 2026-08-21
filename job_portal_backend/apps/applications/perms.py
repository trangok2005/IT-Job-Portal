"""Role permissions của API hồ sơ ứng tuyển."""
from rest_framework import permissions


class CanAccessApplications(permissions.BasePermission):
    """Chỉ ba role nghiệp vụ đã đăng nhập được truy cập applications."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (
                request.user.is_candidate
                or request.user.is_employer
                or request.user.is_admin_role
            )
        )


class IsCandidate(permissions.BasePermission):
    """Chỉ candidate được tạo hồ sơ ứng tuyển."""

    message = "Chỉ ứng viên mới được ứng tuyển."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_candidate
        )


class IsEmployerOrAdmin(permissions.BasePermission):
    """Chỉ employer hoặc admin được yêu cầu chuyển trạng thái."""

    message = "Chỉ nhà tuyển dụng hoặc admin được xử lý hồ sơ ứng tuyển."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_employer or request.user.is_admin_role)
        )
