from apps.companies.models import Company


def get_company_for_employer(user):
    return Company.objects.select_related("owner", "reviewed_by").filter(owner=user).first()


def get_all_companies(status=None):
    qs = Company.objects.select_related("owner", "reviewed_by").order_by("-created_at")
    if status:
        qs = qs.filter(status=status)
    return qs
