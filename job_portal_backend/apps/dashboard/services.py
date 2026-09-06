"""Tính toán nghiệp vụ thuần túy cho dashboard, không ghi dữ liệu."""


def calculate_profile_completion(profile, has_primary_resume: bool) -> int:
    """Tính độ hoàn thiện từ bốn trường chính và một CV chính."""
    completed = sum(
        bool(value and str(value).strip())
        for value in (
            profile.full_name,
            profile.phone,
            profile.headline,
            profile.desired_position,
        )
    )
    return (completed + int(has_primary_resume)) * 20
