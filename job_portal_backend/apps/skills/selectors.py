"""skills selectors — read-only queries (no writes / no business mutation)."""
from django.db.models import Count, Q

from apps.jobs.models import JobPost
from apps.skills.models import MatchingWeightConfig, Skill, SkillCategory


def get_skills_for_review(status=None):
    """Toàn bộ skill (admin dùng để duyệt lô), mới nhất trước."""
    qs = Skill.objects.select_related("category", "merged_into").order_by("-created_at")
    if status:
        qs = qs.filter(status=status)
    return qs


def get_public_skills():
    """Chỉ skill APPROVED + is_active — dùng cho form chọn skill, tìm kiếm."""
    return (
        Skill.objects.filter(status=Skill.Status.APPROVED, is_active=True)
        .select_related("category")
        .order_by("name")
    )


def get_hot_skills(limit=6):
    """Top kỹ năng xuất hiện nhiều nhất trong các tin ACTIVE (JobSkill).
    Dùng cho chip 'Đang tìm nhiều' ở trang index."""
    return (
        Skill.objects.filter(status=Skill.Status.APPROVED, is_active=True)
        .annotate(
            job_count=Count(
                "job_links",
                filter=Q(job_links__job__status=JobPost.Status.ACTIVE),
            )
        )
        .filter(job_count__gt=0)
        .order_by("-job_count", "name")[:limit]
    )


def get_skill_categories():
    return SkillCategory.objects.annotate(skill_count=Count("skills")).order_by("name")


def get_active_weight_config():
    config = MatchingWeightConfig.objects.filter(is_active=True).first()
    if config is None:
        # Mặc định lấy config đầu tiên nếu admin chưa kích hoạt config nào.
        config = MatchingWeightConfig.objects.first()
    return config