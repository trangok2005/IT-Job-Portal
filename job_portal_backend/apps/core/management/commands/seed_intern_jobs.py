"""Seed 50 coherent internship variants from unused rows in the JD CSV."""
import csv
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.companies.models import Company
from apps.core.management.commands.seed_sample_jobs import (
    CSV_PATH,
    ROLE_GROUPS,
    SKILL_ALIASES,
    _location,
    _list_field,
    _select_rows,
    _workplace_type,
)
from apps.core.seed_data.sample_jobs import EXTRA_GROUP_ROLES, GROUP_QUOTAS
from apps.jobs import services as job_services
from apps.jobs.models import JobPost, JobSkill
from apps.skills.models import Skill


User = get_user_model()


def _is_explicit_intern(row: dict) -> bool:
    text = f"{row['title']} {row['it_role_type']}".lower()
    return any(word in text for word in ("intern", "fresher", "trainee"))


def _select_intern_sources(rows: list[dict]) -> list[tuple[str, int, dict]]:
    original_indices = {index for index, _ in _select_rows(rows)}
    selected = []
    used_indices = set(original_indices)
    used_companies = set()

    for group, quota in GROUP_QUOTAS.items():
        roles = ROLE_GROUPS[group] | EXTRA_GROUP_ROLES.get(group, set())
        candidates = [
            (index, row)
            for index, row in enumerate(rows)
            if index not in used_indices
            and row["it_role_type"] in roles
            and row["title"].strip()
            and row["company"].strip()
        ]
        candidates.sort(key=lambda item: (not _is_explicit_intern(item[1]), item[0]))
        group_rows = []
        for index, row in candidates:
            company = row["company"].strip()
            if company in used_companies:
                continue
            group_rows.append((group, index, row))
            used_indices.add(index)
            used_companies.add(company)
            if len(group_rows) == quota:
                break
        if len(group_rows) != quota:
            raise ValueError(
                f"Nhóm {group} chỉ chọn được {len(group_rows)}/{quota} JD."
            )
        selected.extend(group_rows)
    return selected


def _intern_title(group: str, skills: list[str]) -> str:
    focus = ", ".join(skills[:2])
    return f"{group} Intern{f' ({focus})' if focus else ''}"[:255]


class Command(BaseCommand):
    help = "Seed 50 synthetic internship jobs based on unused source JD rows."

    def handle(self, *args, **options):
        with CSV_PATH.open(encoding="utf-8-sig", newline="") as source:
            rows = list(csv.DictReader(source))
        selected = _select_intern_sources(rows)
        jobs_to_embed = []
        created_count = 0

        with transaction.atomic():
            for order, (group, source_index, row) in enumerate(selected, start=1):
                email = f"intern.jd.demo.{source_index:03d}@jobportal.local"
                owner, owner_created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        "username": f"intern_jd_{source_index:03d}",
                        "role": User.Role.EMPLOYER,
                    },
                )
                if owner_created:
                    owner.set_password("ChangeMe123!")
                    owner.save(update_fields=["password"])

                source_company = row["company"].strip() or f"Intern Company {order}"
                company, _ = Company.objects.update_or_create(
                    owner=owner,
                    defaults={
                        "name": f"{source_company} - Internship Demo"[:255],
                        "description": (
                            "Công ty demo cho bộ dữ liệu thực tập, chuyển thể từ "
                            "job_descriptions_500_balanced.csv."
                        ),
                        "address": (row["location"].strip() or row["city"].strip())[:500],
                        "industry": "IT - Software",
                        "status": Company.Status.APPROVED,
                    },
                )

                raw_skills = [
                    *_list_field(row["main_programming_languages"]),
                    *_list_field(row["key_technologies"]),
                ]
                canonical_names = list(
                    dict.fromkeys(
                        SKILL_ALIASES.get(name, name)
                        for name in raw_skills
                        if name and name != "Not Specified"
                    )
                )
                title = _intern_title(group, canonical_names)
                skill_summary = ", ".join(canonical_names[:6]) or "công nghệ phần mềm"
                job, created = JobPost.objects.get_or_create(
                    company=company,
                    title=title,
                    defaults={
                        "created_by": owner,
                        "description": (
                            f"Vị trí thực tập {group} có mentor hướng dẫn. Intern hỗ trợ "
                            f"các tác vụ thực tế liên quan đến {skill_summary}, viết tài liệu, "
                            "kiểm thử và tham gia review cùng đội ngũ kỹ thuật."
                        ),
                        "requirements": (
                            "Sinh viên năm cuối hoặc mới tốt nghiệp ngành CNTT; có kiến thức "
                            f"nền tảng về {skill_summary}; chủ động học hỏi và sử dụng Git."
                        ),
                        "benefits": (
                            "Được mentoring, tham gia dự án thực tế, hỗ trợ thực tập và có "
                            "cơ hội trở thành nhân viên chính thức."
                        ),
                        "location": _location(row["city"].strip() or row["location"].strip()),
                        "workplace_type": _workplace_type(title, row["description"]),
                        "job_type": JobPost.JobType.FULL_TIME,
                        "experience_level": JobPost.ExperienceLevel.ENTRY,
                        "salary_min": 4_000_000,
                        "salary_max": 10_000_000,
                        "salary_negotiable": False,
                        "status": JobPost.Status.ACTIVE,
                        "published_at": timezone.now() - timedelta(minutes=50 - order),
                        "expires_at": timezone.now() + timedelta(days=120),
                        "is_active": True,
                    },
                )
                if created:
                    created_count += 1
                    for skill_name in canonical_names:
                        skill = Skill.objects.filter(
                            name__iexact=skill_name,
                            status__in=[Skill.Status.APPROVED, Skill.Status.PENDING],
                        ).first()
                        if skill is None:
                            continue
                        JobSkill.objects.get_or_create(job=job, skill=skill)
                if created or job.embedding_is_stale:
                    jobs_to_embed.append(job)

        for job in jobs_to_embed:
            job_services.enqueue_job_embedding_robust(job)

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded 50 internship jobs ({created_count} new); "
                f"queued {len(jobs_to_embed)} embeddings."
            )
        )
