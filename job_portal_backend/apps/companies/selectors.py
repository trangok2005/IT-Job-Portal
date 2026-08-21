"""companies selectors — read-only query logic (no writes, no business mutation)."""
from apps.companies.models import Company


def get_company_for_employer(user):
    """Hồ sơ công ty duy nhất mà employer đang quản lý."""
    return Company.objects.select_related("owner", "reviewed_by").filter(owner=user).first()


def get_all_companies(status=None):
    """Toàn bộ hồ sơ công ty cho admin duyệt (UC "Duyệt hồ sơ công ty đăng ký")."""
    qs = Company.objects.select_related("owner", "reviewed_by").order_by("-created_at")
    if status:
        qs = qs.filter(status=status)
    return qs
