"""Các service ghi dữ liệu và áp dụng quy tắc quản trị skill.

Mọi thay đổi status, gộp skill hoặc trọng số phải qua đây; không gọi tùy tiện
``save()`` trong view.
"""
from uuid import UUID

from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rapidfuzz import fuzz

from apps.core.qstash_client import publish_task
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
    "required_skill_multiplier",
)


def _validate_weight_data(config, data):
    from decimal import Decimal

    weights = [
        Decimal(str(data.get(field, getattr(config, field))))
        for field in WEIGHT_FIELDS[:-1]
    ]
    multiplier = Decimal(str(
        data.get("required_skill_multiplier", config.required_skill_multiplier)
    ))
    if any(not value.is_finite() or value < 0 for value in weights):
        raise ValueError("Các trọng số phải hữu hạn và không âm.")
    if sum(weights) != Decimal("1"):
        raise ValueError("Tổng các trọng số phải bằng 1.0.")
    if not multiplier.is_finite() or multiplier < 1:
        raise ValueError("Hệ số kỹ năng bắt buộc phải hữu hạn và không nhỏ hơn 1.")


FUZZY_SKILL_THRESHOLD = 90
FUZZY_SKILL_MIN_LENGTH = 4


def is_savable_skill(skill: Skill) -> bool:
    """Skill gắn được vào hồ sơ/tin: APPROVED hoặc PENDING (chờ duyệt),
    đang hoạt động. Một quy tắc duy nhất cho toàn hệ thống."""
    return (
        skill.status in (Skill.Status.APPROVED, Skill.Status.PENDING)
        and skill.is_active
    )


def resolve_savable_skill(value) -> Skill:
    """Hàm phân giải duy nhất cho mọi luồng trích xuất của UC-01/UC-02.

    Nhận Skill, chuỗi UUID hoặc tên thô. Tên lạ được tạo ở trạng thái PENDING
    chờ admin duyệt. Phát sinh ValueError nếu tham chiếu không hợp lệ hoặc
    skill không được phép lưu.
    """
    if isinstance(value, Skill):
        skill = value.effective_skill
    else:
        raw = str(value).strip()
        try:
            skill_id = UUID(raw)
        except (ValueError, TypeError):
            skill_id = None

        if skill_id is not None:
            found = Skill.objects.filter(pk=skill_id).select_related("merged_into").first()
            if found is None:
                raise ValueError("Kỹ năng không hợp lệ hoặc chưa được duyệt.")
            skill = found.effective_skill
        else:
            skill = resolve_extracted_skill(raw)

    if not is_savable_skill(skill):
        raise ValueError("Kỹ năng không hợp lệ hoặc chưa được duyệt.")
    return skill


def _invalidate_linked_embeddings(candidate_ids, job_ids) -> None:
    """Tăng version và xếp lại hàng đợi cho vector có tên skill canonical đổi."""
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
        for profile_id, version in candidate_versions:
            publish_task(
                "generate_candidate_embedding",
                {"profile_id": str(profile_id), "profile_version": version},
            )
        for job_id, version in job_versions:
            publish_task(
                "generate_job_embedding",
                {"job_id": str(job_id), "content_version": version},
            )

    transaction.on_commit(enqueue)


def _find_fuzzy_skill(normalized_name: str) -> Skill | None:
    """Trả một fuzzy match rõ ràng; tên ngắn phải exact match với alias."""
    if len(normalized_name) < FUZZY_SKILL_MIN_LENGTH:
        return None

    candidates = {}

    def add_candidate(candidate_text: str, candidate_skill: Skill) -> None:
        effective_skill = candidate_skill.effective_skill
        if not is_savable_skill(effective_skill):
            return

        score = fuzz.ratio(normalized_name, candidate_text)
        if score < FUZZY_SKILL_THRESHOLD:
            return

        current = candidates.get(effective_skill.pk)
        if current is None or score > current[0]:
            candidates[effective_skill.pk] = (score, effective_skill)

    for skill in Skill.objects.select_related("merged_into").all():
        add_candidate(normalize_alias(skill.name), skill)
    for alias in SkillAlias.objects.select_related("skill__merged_into").all():
        add_candidate(alias.normalized_text, alias.skill)

    ranked = sorted(
        candidates.values(), key=lambda candidate: candidate[0], reverse=True
    )
    if not ranked:
        return None

    best_score, best_skill = ranked[0]
    if len(ranked) > 1 and best_score - ranked[1][0] < 3:
        return None
    return best_skill


def resolve_extracted_skill(name: str) -> Skill:
    """Phân giải alias bằng exact/fuzzy match hoặc tạo skill AI chờ duyệt."""
    cleaned_name = name.strip()
    normalized = normalize_alias(cleaned_name)
    alias = SkillAlias.objects.select_related("skill__merged_into").filter(
        normalized_text=normalized
    ).first()
    if alias is not None:
        effective_skill = alias.skill.effective_skill
        if is_savable_skill(effective_skill):
            return effective_skill

    skill = Skill.objects.select_related("merged_into").filter(
        name__iexact=cleaned_name
    ).first()
    if skill is not None:
        effective_skill = skill.effective_skill
        if is_savable_skill(effective_skill):
            return effective_skill

    fuzzy_skill = _find_fuzzy_skill(normalized)
    if fuzzy_skill is not None:
        return fuzzy_skill

    if skill is not None:
        raise ValueError("Kỹ năng không hợp lệ hoặc chưa được duyệt.")

    return Skill.objects.create(
        name=cleaned_name,
        slug=make_unique_slug(cleaned_name),
        status=Skill.Status.PENDING,
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
    """Admin tạo thủ công skill APPROVED và sinh slug duy nhất."""
    if Skill.objects.filter(name__iexact=name).exists():
        raise ValueError("Skill đã tồn tại.")
    skill = Skill.objects.create(
        name=name,
        slug=make_unique_slug(name),
        category=category,
        is_active=is_active,
        status=Skill.Status.APPROVED,
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
    """Gộp các skill trùng vào một đích nhưng giữ nguồn làm audit trail.

    Viết lại FK sang đích để tránh cascade mất CandidateSkill/JobSkill, rồi
    đánh dấu nguồn là MERGED và đặt ``merged_into``.
    """
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


@transaction.atomic
def create_weight_config(user, data: dict) -> MatchingWeightConfig:
    configs = list(MatchingWeightConfig.objects.select_for_update().order_by("pk"))
    probe = MatchingWeightConfig()
    _validate_weight_data(probe, data)
    if data.get("is_active"):
        for other in configs:
            if other.is_active:
                other.is_active = False
                other.save(update_fields=["is_active", "updated_at"])
    return MatchingWeightConfig.objects.create(updated_by=user, **data)


@transaction.atomic
def update_weight_config(config: MatchingWeightConfig, user, data: dict) -> MatchingWeightConfig:
    configs = list(
        MatchingWeightConfig.objects.select_for_update().order_by("pk")
    )
    config = next(item for item in configs if item.pk == config.pk)
    _validate_weight_data(config, data)
    for field in (*WEIGHT_FIELDS, "name", "is_active"):
        if field in data:
            setattr(config, field, data[field])
    config.updated_by = user
    if config.is_active:
        # Chỉ 1 config active tại một thời điểm.
        for other in configs:
            if other.pk != config.pk and other.is_active:
                other.is_active = False
                other.save(update_fields=["is_active", "updated_at"])
    config.save()
    return config
