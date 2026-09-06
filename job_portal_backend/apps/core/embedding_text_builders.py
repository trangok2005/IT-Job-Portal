"""Stable Candidate, Job, and Query documents for the shared embedder."""
from typing import TYPE_CHECKING

from django.db.models import F

from apps.core.text_processing import (
    build_labeled_text,
    build_skills_line,
    clean_and_limit_text,
)


if TYPE_CHECKING:
    from apps.candidates.models import CandidateProfile
    from apps.jobs.models import JobPost


def build_candidate_text(profile: "CandidateProfile") -> str:
    """Build focused CV text without personal, school, or company identity."""
    educations = []
    for education in profile.educations.order_by(
        F("end_date").desc(nulls_first=True),
        F("start_date").desc(nulls_last=True),
        "-pk",
    ):
        value = build_labeled_text(
            [("Degree", education.degree), ("Major", education.major)]
        ).replace("\n", "; ")
        if value:
            educations.append(value)

    experiences = []
    for experience in profile.experiences.order_by(
        "-is_current",
        F("end_date").desc(nulls_last=True),
        F("start_date").desc(nulls_last=True),
        "-pk",
    ):
        value = build_labeled_text(
            [
                ("Position", experience.position),
                (
                    "Description",
                    clean_and_limit_text(experience.description, 600),
                ),
            ]
        ).replace("\n", "; ")
        if value:
            experiences.append(value)

    skills = build_skills_line(
        link.skill.name
        for link in profile.candidate_skills.select_related("skill")
        # PENDING vẫn vào text vector (UC-01 bước 11): pending chỉ bị loại
        # khỏi bộ lọc SQL cứng, không chặn semantic matching.
        .filter(skill__status__in=("APPROVED", "PENDING"), skill__is_active=True)
        .order_by("skill__name", "pk")
    )
    return build_labeled_text(
        [
            ("Desired position", profile.desired_position),
            ("Headline", profile.headline),
            ("Summary", clean_and_limit_text(profile.summary, 1200)),
            ("Education", " | ".join(educations)),
            ("Experience", " | ".join(experiences)),
            ("Skills", skills),
        ]
    )


def build_job_text(job: "JobPost") -> str:
    """Build one focused JD document shared by search and CV matching."""
    skills = build_skills_line(
        link.skill.name
        for link in job.job_skills.select_related("skill")
        .filter(skill__status__in=("APPROVED", "PENDING"), skill__is_active=True)
        .order_by("skill__name", "pk")
    )
    return build_labeled_text(
        [
            ("Position", job.title),
            ("Role summary", clean_and_limit_text(job.description, 1200)),
            ("Requirements", clean_and_limit_text(job.requirements, 1200)),
            (
                "Experience level",
                job.get_experience_level_display() if job.experience_level else "",
            ),
            ("Skills", skills),
        ]
    )


def build_query_text(raw_query: str) -> str:
    """Normalize a free-form search without pretending it is a full JD."""
    return build_labeled_text([("Desired job", raw_query)])
