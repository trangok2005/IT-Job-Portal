"""candidates selectors — read-only query logic (no writes, no business mutation)."""
from apps.candidates.models import CandidateProfile


def get_my_profile(user):
    """Hồ sơ của ứng viên (kèm toàn bộ các mục con để render trang profile)."""
    return (
        CandidateProfile.objects.filter(user=user)
        .select_related("user")
        .prefetch_related(
            "educations",
            "experiences",
            "candidate_skills__skill",
            "resumes",
        )
        .first()
    )


def get_resumes(profile):
    return profile.resumes.order_by("-is_primary", "-created_at")