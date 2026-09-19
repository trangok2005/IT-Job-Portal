"""Xóa mọi JobPost/JobSkill rồi seed 200 tin từ JSON."""
import json
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.companies.models import Company
from apps.jobs import services as job_services
from apps.jobs.models import JobPost, JobSkill
from apps.skills.models import Skill

User = get_user_model()

SEED_PATH = (
    settings.BASE_DIR / "apps" / "core" / "seed_data" / "jobs_200_curated.json"
)

STATUS_EXPIRY_DAYS = {
    JobPost.Status.ACTIVE: 90,
    JobPost.Status.DRAFT: 30,
    JobPost.Status.CLOSED: 0,
    JobPost.Status.EXPIRED: -30,
}


class Command(BaseCommand):
    help = "Xóa sạch JobPost cũ và seed 200 JobPosts chuẩn hóa (120/60/20) rồi sinh embedding."

    def add_arguments(self, parser):
        parser.add_argument(
            "--with-embeddings",
            action="store_true",
            help="Đưa các tin ACTIVE vào QStash sinh embedding.",
        )

    def handle(self, *args, **options):
        run_embeddings = options.get("with_embeddings", False)
        data = json.loads(SEED_PATH.read_text(encoding="utf-8"))
        jobs_data = data["jobs"]

        skill_cache = {
            s.name: s
            for s in Skill.objects.filter(
                status__in=[Skill.Status.APPROVED, Skill.Status.PENDING]
            )
        }

        with transaction.atomic():
            # JobSkill được xóa theo cascade.
            deleted, _ = JobPost.objects.all().delete()
            self.stdout.write(f"Đã xóa {deleted} đối tượng JobPost/JobSkill cũ.")

            company_cache = {}
            created_jobs = 0

            for order, row in enumerate(jobs_data, start=1):
                company = self._get_company(company_cache, row["company_name"])
                job = JobPost(
                    company=company,
                    created_by=company.owner,
                    title=row["title"],
                    description=row["description"],
                    requirements=row["requirements"],
                    benefits=row["benefits"],
                    location=row["location"],
                    workplace_type=row["workplace_type"],
                    job_type=row["job_type"],
                    experience_level=row["experience_level"],
                    required_education_level=row.get("required_education_level"),
                    salary_min=row["salary_min"],
                    salary_max=row["salary_max"],
                    salary_negotiable=row["salary_negotiable"],
                    status=row["status"],
                )
                self._apply_dates(job, order)
                job.save()
                self._attach_skills(job, row["skills"], skill_cache)
                created_jobs += 1

            self.stdout.write(f"Đã tạo {created_jobs} JobPosts.")

        if run_embeddings:
            self._enqueue_embeddings(jobs_data)

        self.stdout.write(self.style.SUCCESS(
            "Seed jobs_200 xong. "
            + (f"Đã đưa {sum(1 for r in jobs_data if r['status'] == 'ACTIVE')} tin ACTIVE vào hàng đợi embedding."
               if run_embeddings
               else "Chạy thêm với --with-embeddings để sinh vector cho tin ACTIVE.")
        ))

    def _get_company(self, cache: dict, name: str) -> Company:
        if name in cache:
            return cache[name]
        slug = name.lower().replace(" ", "").replace(".", "").replace("/", "")[:40]
        email = f"hr.{slug}@jobportal.local"
        owner, _ = User.objects.get_or_create(
            email=email,
            defaults={
                "username": f"hr_{slug}",
                "role": User.Role.EMPLOYER,
            },
        )
        if not owner.check_password("ChangeMe123!"):
            owner.set_password("ChangeMe123!")
            owner.save(update_fields=["password"])
        company, _ = Company.objects.get_or_create(
            owner=owner,
            defaults={
                "name": name,
                "description": f"Công ty {name} - nhà tuyển dụng IT hàng đầu Việt Nam.",
                "website": "",
                "address": "Hà Nội / TP.HCM",
                "company_size": "500+",
                "industry": "IT - Software",
                "status": Company.Status.APPROVED,
            },
        )
        if company.status != Company.Status.APPROVED:
            company.status = Company.Status.APPROVED
            company.save(update_fields=["status", "updated_at"])
        cache[name] = company
        return company

    def _apply_dates(self, job: JobPost, order: int) -> None:
        now = timezone.now()
        if job.status == JobPost.Status.ACTIVE:
            job.published_at = now - timedelta(hours=24 * (200 - order) % 120)
            job.expires_at = now + timedelta(days=90)
        elif job.status == JobPost.Status.DRAFT:
            job.published_at = None
            job.expires_at = now + timedelta(days=30)
        elif job.status == JobPost.Status.CLOSED:
            job.published_at = now - timedelta(days=10)
            job.expires_at = now - timedelta(days=1)
        elif job.status == JobPost.Status.EXPIRED:
            job.published_at = now - timedelta(days=45)
            job.expires_at = now - timedelta(days=15)

    def _attach_skills(self, job: JobPost, skill_specs: list, skill_cache: dict) -> None:
        if not skill_specs or not any(item["is_required"] for item in skill_specs):
            raise CommandError(f"Job '{job.title}' phải có ít nhất một skill bắt buộc.")
        for spec in skill_specs:
            skill = skill_cache.get(spec["name"])
            if skill is None:
                raise CommandError(
                    f"Skill '{spec['name']}' của job '{job.title}' chưa có trong taxonomy."
                )
            JobSkill.objects.create(
                job=job,
                skill=skill,
                is_required=spec["is_required"],
            )

    def _enqueue_embeddings(self, jobs_data) -> None:
        jobs = JobPost.objects.filter(status=JobPost.Status.ACTIVE)
        count = 0
        for job in jobs:
            if job.embedding_is_stale:
                job_services.enqueue_job_embedding_robust(job)
                count += 1
        self.stdout.write(f"Đã enqueue {count} tin ACTIVE để sinh embedding.")
