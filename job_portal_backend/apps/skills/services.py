"""skills services — write operations + business rules (Admin quản trị Skill).

Mọi thay đổi status / gộp skill / trọng số đều đi qua đây, KHÔNG gọi save()
tuỳ tiện trong views.
"""
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rapidfuzz import fuzz, process

from apps.skills.models import (
    CandidateSkill,
    MatchingWeightConfig,
    Skill,
    SkillAlias,
    SkillCategory,
)
from apps.skills.utils import make_unique_slug, normalize_alias

WEIGHT_FIELDS = (
    "weight_semantic_similarity",
    "weight_skill_overlap",
    "weight_experience_match",
    "weight_education_match",
)
FUZZY_SKILL_THRESHOLD = 90
FUZZY_SKILL_MIN_LENGTH = 4


def _invalidate_linked_embeddings(candidate_ids, job_ids) -> None:
    """Version and requeue vectors whose canonical skill text changed."""
    from apps.candidates.models import CandidateProfile
    from apps.jobs.models import JobPost

    candidate_ids = list(set(candidate_ids))
    job_ids = list(set(job_ids))
    CandidateProfile.objects.filter(pk__in=candidate_ids).update(
        profile_version=F("profile_version") + 1
    )
    JobPost.objects.filter(pk__in=job_ids).update(
        content_version=F("content_version") + 1
    )
    candidate_versions = list(
        CandidateProfile.objects.filter(pk__in=candidate_ids).values_list(
            "pk", "profile_version"
        )
    )
    job_versions = list(
        JobPost.objects.filter(
            pk__in=job_ids, status=JobPost.Status.ACTIVE
        ).values_list("pk", "content_version")
    )

    def enqueue():
        from django_q.tasks import async_task

        for profile_id, version in candidate_versions:
            async_task(
                "apps.candidates.tasks.generate_candidate_embedding",
                str(profile_id),
                version,
            )
        for job_id, version in job_versions:
            async_task(
                "apps.jobs.tasks.generate_job_embedding", str(job_id), version
            )

    transaction.on_commit(enqueue)


def _find_fuzzy_skill(normalized_name: str) -> Skill | None:
    """Return one unambiguous near-match; short names require exact aliases."""
    if len(normalized_name) < FUZZY_SKILL_MIN_LENGTH:
        return None

    choices = {}
    for skill in Skill.objects.select_related("merged_into").all():
        choices.setdefault(normalize_alias(skill.name), skill)
    for alias in SkillAlias.objects.select_related("skill__merged_into").all():
        choices.setdefault(alias.normalized_text, alias.skill)

    matches = process.extract(
        normalized_name,
        choices.keys(),
        scorer=fuzz.ratio,
        score_cutoff=FUZZY_SKILL_THRESHOLD,
        limit=2,
    )
    if not matches:
        return None

    best_key, best_score, _ = matches[0]
    best_skill = choices[best_key].effective_skill
    if len(matches) > 1:
        second_key, second_score, _ = matches[1]
        second_skill = choices[second_key].effective_skill
        if second_skill.pk != best_skill.pk and best_score - second_score < 3:
            return None
    return best_skill


def resolve_extracted_skill(name: str, source: str) -> Skill:
    """Resolve exact/fuzzy taxonomy aliases or create a pending AI skill."""
    cleaned_name = name.strip()
    normalized = normalize_alias(cleaned_name)
    alias = SkillAlias.objects.select_related("skill__merged_into").filter(
        normalized_text=normalized
    ).first()
    if alias is not None:
        return alias.skill.effective_skill

    skill = Skill.objects.select_related("merged_into").filter(
        name__iexact=cleaned_name
    ).first()
    if skill is not None:
        return skill.effective_skill

    fuzzy_skill = _find_fuzzy_skill(normalized)
    if fuzzy_skill is not None:
        return fuzzy_skill

    return Skill.objects.create(
        name=cleaned_name,
        slug=make_unique_slug(cleaned_name),
        status=Skill.Status.PENDING,
        source=source,
    )


def _mark_reviewed(skill: Skill, user, status) -> Skill:
    skill.status = status
    skill.reviewed_by = user
    skill.reviewed_at = timezone.now()
    skill.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])
    return skill


@transaction.atomic
def approve_skill(skill: Skill, user) -> Skill:
    """Duyệt skill PENDING; sinh lại vector cho hồ sơ/JD đang dùng skill này."""
    result = _mark_reviewed(skill, user, Skill.Status.APPROVED)
    candidate_ids = list(
        CandidateSkill.objects.filter(skill=skill).values_list(
            "candidate_id", flat=True
        )
    )
    from apps.jobs.models import JobSkill

    job_ids = list(
        JobSkill.objects.filter(skill=skill).values_list("job_id", flat=True)
    )
    _invalidate_linked_embeddings(candidate_ids, job_ids)
    return result


def reject_skill(skill: Skill, user) -> Skill:
    return _mark_reviewed(skill, user, Skill.Status.REJECTED)


def _create_alias(skill: Skill, alias_text: str) -> SkillAlias:
    normalized = normalize_alias(alias_text)
    if SkillAlias.objects.filter(alias_text=alias_text).exists():
        raise ValueError(f"Alias '{alias_text}' đã tồn tại.")
    if SkillAlias.objects.filter(normalized_text=normalized).exists():
        raise ValueError(f"Alias '{alias_text}' trùng với alias đã có.")
    return SkillAlias.objects.create(
        skill=skill, alias_text=alias_text, normalized_text=normalized,
    )


def create_skill(user, name: str, category=None, aliases=None, is_active=True) -> Skill:
    """Admin tạo tay skill APPROVED + sinh slug unique."""
    if Skill.objects.filter(name__iexact=name).exists():
        raise ValueError("Skill đã tồn tại.")
    skill = Skill.objects.create(
        name=name,
        slug=make_unique_slug(name),
        category=category,
        is_active=is_active,
        status=Skill.Status.APPROVED,
        source=Skill.Source.ADMIN_MANUAL,
        reviewed_by=user,
        reviewed_at=timezone.now(),
    )
    for alias_text in aliases or []:
        _create_alias(skill, alias_text)
    return skill


@transaction.atomic
def update_skill(skill: Skill, user, name=None, category=None, is_active=None, aliases=None) -> Skill:
    renamed = bool(name and name != skill.name)
    candidate_ids = list(
        CandidateSkill.objects.filter(skill=skill).values_list("candidate_id", flat=True)
    ) if renamed else []
    from apps.jobs.models import JobSkill
    job_ids = list(
        JobSkill.objects.filter(skill=skill).values_list("job_id", flat=True)
    ) if renamed else []
    if name and name != skill.name:
        if Skill.objects.filter(name__iexact=name).exclude(pk=skill.pk).exists():
            raise ValueError("Skill đã tồn tại.")
        skill.name = name
        skill.slug = make_unique_slug(name, exclude_pk=skill.pk)
    if category is not None:
        skill.category = category
    if is_active is not None:
        skill.is_active = is_active
    skill.save()
    if aliases is not None:
        skill.aliases.all().delete()
        for alias_text in aliases:
            _create_alias(skill, alias_text)
    if renamed:
        _invalidate_linked_embeddings(candidate_ids, job_ids)
    return skill


@transaction.atomic
def merge_skills(user, source_ids: list, target_id) -> Skill:
    """Gộp các skill trùng về 1 đích. KHÔNG xoá skill nguồn (giữ audit trail,
    tránh cascade mất CandidateSkill/JobSkill đang hiển thị trên hồ sơ) mà
    rewrite FK sang đích rồi đánh dấu nguồn là MERGED + merged_into."""
    from apps.jobs.models import JobSkill

    target = Skill.objects.get(pk=target_id)
    target = target.effective_skill
    if target is None:
        raise ValueError("Skill đích không hợp lệ.")

    source_ids = [pk for pk in source_ids if str(pk) != str(target.pk)]
    if not source_ids:
        raise ValueError("Không có skill nguồn hợp lệ.")

    sources = list(Skill.objects.filter(pk__in=source_ids).exclude(pk=target.pk))
    affected_skill_ids = [target.pk, *(source.pk for source in sources)]
    candidate_ids = list(
        CandidateSkill.objects.filter(skill_id__in=affected_skill_ids).values_list(
            "candidate_id", flat=True
        )
    )
    job_ids = list(
        JobSkill.objects.filter(skill_id__in=affected_skill_ids).values_list(
            "job_id", flat=True
        )
    )
    now = timezone.now()

    # Xoá các bản ghi nối sẽ trùng (candidate/job đã có sẵn skill đích)
    # trước khi rewrite, tránh vi phạm UniqueConstraint.
    for source in sources:
        CandidateSkill.objects.filter(
            skill=source, candidate__candidate_skills__skill=target,
        ).delete()
        JobSkill.objects.filter(
            skill=source, job__job_skills__skill=target,
        ).delete()

    CandidateSkill.objects.filter(skill__in=sources).update(skill=target)
    JobSkill.objects.filter(skill__in=sources).update(skill=target)

    # Di chuyển alias sang đích (bỏ alias trùng normalized với alias của đích).
    target_norms = set(target.aliases.values_list("normalized_text", flat=True))
    for alias in SkillAlias.objects.filter(skill__in=sources):
        if alias.normalized_text in target_norms:
            alias.delete()
        else:
            alias.skill = target
            alias.save(update_fields=["skill"])

    for source in sources:
        if source.status == Skill.Status.MERGED:
            continue
        source.status = Skill.Status.MERGED
        source.merged_into = target
        source.reviewed_by = user
        source.reviewed_at = now
        source.is_active = False
        source.save(
            update_fields=[
                "status", "merged_into", "reviewed_by", "reviewed_at",
                "is_active", "updated_at",
            ]
        )
    _invalidate_linked_embeddings(candidate_ids, job_ids)
    return target


def create_category(name: str) -> SkillCategory:
    category, _ = SkillCategory.objects.get_or_create(name=name)
    return category


def update_weight_config(config: MatchingWeightConfig, user, data: dict) -> MatchingWeightConfig:
    for field in (*WEIGHT_FIELDS, "name", "is_active"):
        if field in data:
            setattr(config, field, data[field])
    config.updated_by = user
    if config.is_active:
        # Chỉ 1 config active tại một thời điểm.
        MatchingWeightConfig.objects.exclude(pk=config.pk).update(is_active=False)
    config.save()
    return config
