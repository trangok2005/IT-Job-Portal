"""Pure dashboard business calculations; this app performs no writes."""


def calculate_profile_completion(profile, has_primary_resume: bool) -> int:
    """Calculate completion from four key fields and a primary CV."""
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
