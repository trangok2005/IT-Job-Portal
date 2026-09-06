"""jobs permissions — business rules are checked here, not in views."""
from rest_framework import permissions

from apps.companies.models import Company
from apps.jobs.models import JobPost


class IsApprovedEmployer(permissions.BasePermission):
    """Chỉ employer có công ty APPROVED mới được đăng tin (precondition UC-02)."""

    message = "Cần có hồ sơ công ty được duyệt để đăng tin tuyển dụng."

    def has_permission(self, request, view):
        """Kiểm tra role và hồ sơ công ty APPROVED trước khi tạo tin."""
        if not request.user or not request.user.is_authenticated:
            return False
        if not request.user.is_employer:
            return False
        return Company.objects.filter(
            owner=request.user, status=Company.Status.APPROVED
        ).exists()


class IsJobOwnerOrAdmin(permissions.BasePermission):
    """Chủ tin hoặc admin mới được sửa, đăng hoặc đóng tin."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_employer or request.user.is_admin_role)
        )

    def has_object_permission(self, request, view, obj: JobPost):
        if request.user.is_admin_role:
            return True
        return obj.created_by_id == request.user.pk or obj.company.owner_id == request.user.pk
