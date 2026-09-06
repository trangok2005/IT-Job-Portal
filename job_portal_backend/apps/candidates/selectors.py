"""Các selector chỉ đọc dữ liệu candidate, không thay đổi nghiệp vụ."""
from apps.candidates.models import CandidateProfile


def get_my_profile(user):
    """Lấy hồ sơ candidate cùng dữ liệu con để hiển thị trang hồ sơ."""
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
