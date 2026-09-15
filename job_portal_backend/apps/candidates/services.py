from pathlib import Path

from django.core.files.base import File
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.candidates.models import CandidateProfile, Education, Experience, Resume, ResumeImport
from apps.skills.models import CandidateSkill, Skill
from apps.skills.services import is_savable_skill as _is_savable_skill
from apps.skills.services import resolve_savable_skill
from integrations.qstash.publisher import publish_task


def _enqueue_task(task_name: str, payload: dict) -> None:
    """Chỉ enqueue sau khi transaction commit."""

    def enqueue():
        publish_task(task_name, payload)

    transaction.on_commit(enqueue)


def _resolve_candidate_skill(value) -> Skill:
    return resolve_savable_skill(value)


def _bump_profile_version(profile: CandidateProfile) -> None:
    now = timezone.now()
    CandidateProfile.objects.filter(pk=profile.pk).update(
        profile_version=F("profile_version") + 1,
        updated_at=now,
    )
    profile.refresh_from_db(fields=["profile_version", "updated_at"])
    enqueue_candidate_embedding(profile)


def enqueue_candidate_embedding(profile: CandidateProfile) -> None:
    _enqueue_task(
        "generate_candidate_embedding",
        {
            "profile_id": str(profile.pk),
            "profile_version": profile.profile_version,
        },
    )


@transaction.atomic
def update_profile(profile: CandidateProfile, data: dict) -> CandidateProfile:
    if not data:
        return profile
    for field, value in data.items():
        setattr(profile, field, value)
    profile.save(update_fields=[*data.keys(), "updated_at"])
    _bump_profile_version(profile)
    return profile


@transaction.atomic
def create_education(profile: CandidateProfile, data: dict) -> Education:
    education = Education.objects.create(candidate=profile, **data)
    _bump_profile_version(profile)
    return education


@transaction.atomic
def update_education(education: Education, data: dict) -> Education:
    if not data:
        return education
    for field, value in data.items():
        setattr(education, field, value)
    education.save(update_fields=[*data.keys(), "updated_at"])
    _bump_profile_version(education.candidate)
    return education


@transaction.atomic
def delete_education(education: Education) -> None:
    candidate = education.candidate
    education.delete()
    _bump_profile_version(candidate)


@transaction.atomic
def create_experience(profile: CandidateProfile, data: dict) -> Experience:
    experience = Experience.objects.create(candidate=profile, **data)
    _bump_profile_version(profile)
    return experience


@transaction.atomic
def update_experience(experience: Experience, data: dict) -> Experience:
    if not data:
        return experience
    for field, value in data.items():
        setattr(experience, field, value)
    experience.save(update_fields=[*data.keys(), "updated_at"])
    _bump_profile_version(experience.candidate)
    return experience


@transaction.atomic
def delete_experience(experience: Experience) -> None:
    candidate = experience.candidate
    experience.delete()
    _bump_profile_version(candidate)


@transaction.atomic
def create_candidate_skill(
    profile: CandidateProfile,
    skill: Skill,
    years_of_experience: int | None = None,
) -> CandidateSkill:
    """PENDING được lưu nhưng chưa tham gia bộ lọc cứng."""
    if not _is_savable_skill(skill):
        raise ValueError(
            "Kỹ năng phải đang hoạt động (đã duyệt hoặc chờ duyệt)."
        )
    if CandidateSkill.objects.filter(candidate=profile, skill=skill).exists():
        raise ValueError("Kỹ năng này đã có trong hồ sơ.")
    candidate_skill = CandidateSkill.objects.create(
        candidate=profile,
        skill=skill,
        years_of_experience=years_of_experience,
    )
    _bump_profile_version(profile)
    return candidate_skill


@transaction.atomic
def update_candidate_skill(
    candidate_skill: CandidateSkill,
    data: dict,
) -> CandidateSkill:
    if not data:
        return candidate_skill
    for field, value in data.items():
        if field == "skill":
            if not _is_savable_skill(value):
                raise ValueError(
                    "Kỹ năng phải đang hoạt động (đã duyệt hoặc chờ duyệt)."
                )
            if (
                value.pk != candidate_skill.skill_id
                and CandidateSkill.objects.filter(
                    candidate=candidate_skill.candidate,
                    skill=value,
                ).exists()
            ):
                raise ValueError("Kỹ năng này đã có trong hồ sơ.")
        setattr(candidate_skill, field, value)
    candidate_skill.save(update_fields=[*data.keys(), "updated_at"])
    _bump_profile_version(candidate_skill.candidate)
    return candidate_skill


@transaction.atomic
def delete_candidate_skill(candidate_skill: CandidateSkill) -> None:
    candidate = candidate_skill.candidate
    candidate_skill.delete()
    _bump_profile_version(candidate)


@transaction.atomic
def delete_resume(resume: Resume) -> None:
    candidate = CandidateProfile.objects.select_for_update().get(
        pk=resume.candidate_id,
    )
    locked = Resume.objects.select_for_update().get(pk=resume.pk)
    if locked.applications.exists():
        raise ValueError("Không thể xóa CV đã được dùng để ứng tuyển.")
    was_primary = locked.is_primary
    storage = locked.file.storage
    stored_name = locked.file.name
    locked.delete()

    if was_primary:
        replacement = candidate.resumes.order_by("-created_at").first()
        if replacement is not None:
            replacement.is_primary = True
            replacement.save(update_fields=["is_primary", "updated_at"])

    if stored_name:
        transaction.on_commit(lambda: storage.delete(stored_name))


@transaction.atomic
def set_primary_resume(resume: Resume) -> Resume:
    if resume.is_primary:
        return resume
    CandidateProfile.objects.select_for_update().get(pk=resume.candidate_id)
    resume.candidate.resumes.filter(is_primary=True).update(is_primary=False)
    resume.is_primary = True
    resume.save(update_fields=["is_primary", "updated_at"])
    return resume


@transaction.atomic
def save_full_profile(profile: CandidateProfile, data: dict) -> CandidateProfile:
    locked = CandidateProfile.objects.select_for_update().get(pk=profile.pk)
    educations = data.pop("educations")
    experiences = data.pop("experiences")
    skills = data.pop("skills")
    resume_import_id = data.pop("resume_import_id", None)
    if resume_import_id is not None:
        from apps.candidates.models import ResumeImport
        resume_import = ResumeImport.objects.select_for_update().filter(
            pk=resume_import_id,
            candidate=locked,
            parse_status=ResumeImport.ParseStatus.SUCCESS,
        ).first()
        if resume_import is None:
            raise ValueError("CV preview không hợp lệ hoặc chưa phân tích xong.")
        consume_resume_import(resume_import)

    for field, value in data.items():
        setattr(locked, field, value)
    locked.save(update_fields=[*data.keys(), "updated_at"])

    locked.educations.all().delete()
    Education.objects.bulk_create(
        Education(candidate=locked, **item)
        for item in educations
    )
    locked.experiences.all().delete()
    Experience.objects.bulk_create(
        Experience(candidate=locked, **item)
        for item in experiences
    )
    locked.candidate_skills.all().delete()
    seen_skills = set()
    candidate_skills = []
    for item in skills:
        skill = _resolve_candidate_skill(item["skill"])
        if skill.pk in seen_skills:
            continue
        seen_skills.add(skill.pk)
        candidate_skills.append(
            CandidateSkill(
                candidate=locked,
                skill=skill,
                years_of_experience=item.get("years_of_experience"),
            )
        )
    CandidateSkill.objects.bulk_create(candidate_skills)

    _bump_profile_version(locked)
    return locked


@transaction.atomic
def create_resume_import(profile: CandidateProfile, file) -> ResumeImport:
    """Tạo bản import tạm, không đổi CV chính hoặc profile version."""
    resume_import = ResumeImport.objects.create(
        candidate=profile,
        file=file,
        original_filename=Path(file.name).name,
        file_size_bytes=getattr(file, "size", None),
        parse_status=ResumeImport.ParseStatus.PENDING,
        expires_at=timezone.now() + timezone.timedelta(hours=24),
    )
    _enqueue_task(
        "parse_resume_import",
        {"resume_import_id": str(resume_import.pk)},
    )
    return resume_import


@transaction.atomic
def mark_resume_import_parsed(
    resume_import: ResumeImport,
    raw_data: dict,
    parsed_data: dict | None = None,
) -> ResumeImport:
    if parsed_data is None:
        parsed_data = raw_data

    resume_import.parsed_data = parsed_data
    resume_import.parse_status = ResumeImport.ParseStatus.SUCCESS
    resume_import.parse_error_message = ""
    resume_import.save(
        update_fields=[
            "parsed_data",
            "parse_status",
            "parse_error_message",
            "updated_at",
        ]
    )
    return resume_import


def mark_resume_import_failed(resume_import: ResumeImport, error_message: str) -> ResumeImport:
    resume_import.parse_status = ResumeImport.ParseStatus.FAILED
    resume_import.parse_error_message = error_message[:2000]
    resume_import.save(
        update_fields=["parse_status", "parse_error_message", "updated_at"]
    )
    return resume_import


@transaction.atomic
def consume_resume_import(resume_import: ResumeImport) -> Resume:
    """Sao chép file vì bản import sẽ bị dọn sau 24 giờ."""
    if resume_import.parse_status != ResumeImport.ParseStatus.SUCCESS:
        raise ValueError("Chỉ có thể dùng CV đã parse thành công.")

    candidate = resume_import.candidate
    candidate.resumes.filter(is_primary=True).update(is_primary=False)

    with resume_import.file.open("rb") as source:
        copied = File(source, name=Path(resume_import.file.name).name)
        resume = Resume.objects.create(
            candidate=candidate,
            file=copied,
            original_filename=resume_import.original_filename,
            file_size_bytes=resume_import.file_size_bytes,
            is_primary=True,
        )

    resume_import.parse_status = ResumeImport.ParseStatus.CONSUMED
    resume_import.save(update_fields=["parse_status", "updated_at"])

    return resume


@transaction.atomic
def delete_resume_import(resume_import: ResumeImport) -> None:
    """Bản đã dùng chỉ xóa record vì file đã được sao chép sang Resume."""
    storage = resume_import.file.storage
    stored_name = resume_import.file.name
    consumed = resume_import.parse_status == ResumeImport.ParseStatus.CONSUMED
    resume_import.delete()
    if stored_name and not consumed:
        transaction.on_commit(lambda: storage.delete(stored_name))
