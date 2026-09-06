"""Read-only queries cho danh sách và chi tiết hồ sơ ứng tuyển."""
from django.db.models import F, Q

from apps.applications.models import JobApplication


def _base_queryset():
    """Nạp sẵn dữ liệu cần cho serializer để tránh truy vấn N+1."""
    return (
        JobApplication.objects.all()
        .select_related(
            "job__company",
            "candidate__user",
            "resume",
            "match_result",
        )
        .prefetch_related(
            "status_history__changed_by",
            "candidate__candidate_skills__skill",
        )
    )


def get_applications_for_user(
    user,
    job_id=None,
    status=None,
    ordering="-created_at",
):
    """Candidate thấy hồ sơ mình; employer thấy hồ sơ của các tin mình quản lý."""
    qs = _base_queryset()
    if user.is_admin_role:
        pass
    elif user.is_candidate:
        qs = qs.filter(candidate__user=user)
    elif user.is_employer:
        qs = qs.filter(Q(job__created_by=user) | Q(job__company__owner=user))
    else:
        return qs.none()
    if job_id:
        qs = qs.filter(job_id=job_id)
    if status:
        qs = qs.filter(status=status)
    qs = qs.distinct()
    if ordering == "match_score":
        return qs.order_by(F("match_result__match_score").asc(nulls_last=True))
    if ordering == "-match_score":
        return qs.order_by(F("match_result__match_score").desc(nulls_last=True))
    return qs.order_by(ordering)


def get_application_detail_queryset(user):
    """Giới hạn retrieve theo cùng phạm vi quyền với danh sách."""
    return get_applications_for_user(user)
