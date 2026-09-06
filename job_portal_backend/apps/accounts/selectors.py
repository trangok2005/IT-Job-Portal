"""Các truy vấn chỉ đọc về tài khoản."""
from django.db.models import Q

from apps.accounts.models import User


def get_users(role=None, is_active=None, search=None):
    """Trả danh sách user cho admin sau khi áp dụng bộ lọc hợp lệ."""
    queryset = User.objects.all().order_by("-created_at")
    if role:
        queryset = queryset.filter(role=role)
    if is_active is not None:
        queryset = queryset.filter(is_active=is_active)
    if search:
        queryset = queryset.filter(
            Q(email__icontains=search)
            | Q(username__icontains=search)
            | Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
        )
    return queryset


def get_manageable_user(user_id):
    """Trả user là đối tượng của thao tác quản trị tài khoản."""
    return User.objects.filter(pk=user_id).first()
