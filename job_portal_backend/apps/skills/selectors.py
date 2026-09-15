import re

from django.db.models import Count, Q

from apps.core.matching import (
    MatchingWeights,
    normalize_matching_text,
)
from apps.jobs.models import JobPost
from apps.skills.models import MatchingWeightConfig, Skill, SkillCategory


def get_skills_for_review(status=None):
    qs = Skill.objects.select_related("category", "merged_into").order_by("-created_at")
    if status:
        qs = qs.filter(status=status)
    return qs


def get_public_skills():
    return (
        Skill.objects.filter(status=Skill.Status.APPROVED, is_active=True)
        .select_related("category")
        .order_by("name")
    )


def get_skill_ids_mentioned_in_text(value: str) -> list:
    normalized = normalize_matching_text(value)
    if not normalized:
        return []
    matched = []
    skills = get_public_skills().prefetch_related("aliases")
    for skill in skills:
        terms = {
            normalize_matching_text(skill.name),
            *(alias.normalized_text for alias in skill.aliases.all()),
        }
        if any(
            term
            and re.search(rf"(?<!\w){re.escape(term)}(?!\w)", normalized)
            for term in terms
        ):
            matched.append(skill.pk)
    return matched


def get_hot_skills(limit=6):
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
    return MatchingWeightConfig.objects.filter(is_active=True).first()


def get_active_matching_weights():
    config = MatchingWeightConfig.objects.filter(is_active=True).first()
    if config is None:
        return None
    return MatchingWeights(
        semantic=config.weight_semantic_similarity,
        skill=config.weight_skill_overlap,
        experience=config.weight_experience_match,
        education=config.weight_education_match,
        required_skill_multiplier=config.required_skill_multiplier,
    )
