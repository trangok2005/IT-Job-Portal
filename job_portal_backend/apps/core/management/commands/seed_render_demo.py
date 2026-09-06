import json
import os
from datetime import date, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.candidates.models import CandidateProfile, DegreeLevel, Education, Experience
from apps.companies.models import Company
from apps.core.matching import recognized_degree_level
from apps.core.seed_data.candidates import CANDIDATES
from apps.jobs.models import JobPost, JobSkill
from apps.skills.models import CandidateSkill, Skill
from apps.skills.services import resolve_savable_skill


User = get_user_model()
JOB_COUNT = 50


class Command(BaseCommand):
    help = "Seed idempotent Render demo data: taxonomy, 50 jobs, 10 candidates, employer, admin."

    def handle(self, *args, **options):
        passwords = {
            "admin": self._required_env("SEED_ADMIN_PASSWORD"),
            "employer": self._required_env("SEED_EMPLOYER_PASSWORD"),
            "candidate": self._required_env("SEED_CANDIDATE_PASSWORD"),
        }
        admin_email = os.getenv("SEED_ADMIN_EMAIL", "admin.demo@jobportal.local")
        employer_email = os.getenv(
            "SEED_EMPLOYER_EMAIL", "employer.demo@jobportal.local"
        )

        call_command("seed_skills_taxonomy")
        with transaction.atomic():
            admin = self._upsert_user(
                email=admin_email,
                username="render_demo_admin",
                password=passwords["admin"],
                role=User.Role.ADMIN,
                is_staff=True,
                is_superuser=True,
            )
            employer = self._upsert_user(
                email=employer_email,
                username="render_demo_employer",
                password=passwords["employer"],
                role=User.Role.EMPLOYER,
            )
            company, _ = Company.objects.update_or_create(
                owner=employer,
                defaults={
                    "name": "IT Job Portal Demo Company",
                    "description": "Công ty demo phục vụ kiểm thử hệ thống tuyển dụng IT.",
                    "website": "https://example.com",
                    "address": "Hồ Chí Minh, Việt Nam",
                    "company_size": "100-500",
                    "industry": "IT - Software",
                    "status": Company.Status.APPROVED,
                    "reviewed_by": admin,
                    "reviewed_at": timezone.now(),
                    "rejection_reason": "",
                },
            )
            self._seed_candidates(passwords["candidate"])
            self._seed_jobs(company, employer)

        self.stdout.write(
            self.style.SUCCESS(
                "Render demo seed ready: taxonomy, 50 jobs, 10 candidates, "
                "1 employer and 1 admin. Passwords were read from environment."
            )
        )

    @staticmethod
    def _required_env(name: str) -> str:
        value = os.getenv(name, "")
        if len(value) < 8:
            raise CommandError(f"{name} is required and must contain at least 8 characters.")
        return value

    @staticmethod
    def _upsert_user(
        *, email, username, password, role, is_staff=False, is_superuser=False
    ):
        user, _ = User.objects.get_or_create(
            email=email,
            defaults={"username": username},
        )
        user.role = role
        user.is_active = True
        user.is_staff = is_staff
        user.is_superuser = is_superuser
        user.set_password(password)
        user.save()
        return user

    def _seed_candidates(self, password: str) -> None:
        genders = [CandidateProfile.Gender.MALE, CandidateProfile.Gender.FEMALE]
        for index, data in enumerate(CANDIDATES, start=1):
            user = self._upsert_user(
                email=data["email"],
                username=data["username"],
                password=password,
                role=User.Role.CANDIDATE,
            )
            profile, _ = CandidateProfile.objects.update_or_create(
                user=user,
                defaults={
                    "full_name": data["full_name"],
                    "phone": f"090000{index:04d}",
                    "dob": date(1992 + index % 7, (index % 12) + 1, 10),
                    "gender": genders[index % len(genders)],
                    "address": data["address"],
                    "headline": data["headline"],
                    "summary": data["summary"],
                    "desired_position": data["desired_position"],
                    "is_public": True,
                },
            )
            education = data["education"]
            degree_rank = recognized_degree_level(education["degree"])
            degree_level = {
                1: DegreeLevel.ASSOCIATE,
                2: DegreeLevel.BACHELOR,
                3: DegreeLevel.MASTER,
                4: DegreeLevel.PHD,
            }.get(degree_rank, DegreeLevel.NONE)
            Education.objects.update_or_create(
                candidate=profile,
                school_name=education["school_name"],
                major=education["major"],
                defaults={
                    "degree": education["degree"],
                    "degree_level": degree_level,
                    "is_completed": True,
                    "is_verified": True,
                    "start_date": education["start_date"],
                    "end_date": education["end_date"],
                },
            )
            for experience in data["experiences"]:
                Experience.objects.update_or_create(
                    candidate=profile,
                    company_name=experience["company_name"],
                    position=experience["position"],
                    defaults={
                        "start_date": experience["start_date"],
                        "end_date": experience["end_date"],
                        "is_current": experience["is_current"],
                        "description": experience["description"],
                    },
                )
            for skill_name, _level, years in data["skills"]:
                skill = resolve_savable_skill(skill_name)
                CandidateSkill.objects.update_or_create(
                    candidate=profile,
                    skill=skill,
                    defaults={"years_of_experience": max(1, round(years))},
                )

    def _seed_jobs(self, company: Company, employer) -> None:
        seed_path = (
            settings.BASE_DIR
            / "apps"
            / "core"
            / "seed_data"
            / "jobs_200_curated.json"
        )
        jobs = json.loads(seed_path.read_text(encoding="utf-8"))["jobs"][:JOB_COUNT]
        if len(jobs) != JOB_COUNT:
            raise CommandError(f"Expected {JOB_COUNT} jobs in the curated dataset.")

        skill_names = {
            specification["name"]
            for row in jobs
            for specification in row["skills"]
        }
        skills = {skill.name: skill for skill in Skill.objects.filter(name__in=skill_names)}
        missing = sorted(skill_names - skills.keys())
        if missing:
            raise CommandError(f"Job skills are missing: {', '.join(missing)}")

        now = timezone.now()
        for index, row in enumerate(jobs, start=1):
            title = f"{row['title']} - {row['company_name']} #{index:02d}"
            job, _ = JobPost.objects.update_or_create(
                company=company,
                title=title,
                defaults={
                    "created_by": employer,
                    "description": row["description"],
                    "requirements": row["requirements"],
                    "benefits": row["benefits"],
                    "location": row["location"],
                    "workplace_type": row["workplace_type"],
                    "job_type": row["job_type"],
                    "experience_level": row["experience_level"],
                    "required_education_level": DegreeLevel.BACHELOR,
                    "salary_min": row["salary_min"],
                    "salary_max": row["salary_max"],
                    "salary_negotiable": row["salary_negotiable"],
                    "status": JobPost.Status.ACTIVE,
                    "published_at": now - timedelta(days=index % 30),
                    "expires_at": now + timedelta(days=90),
                    "embedding": None,
                    "embedding_version": 0,
                    "embedding_updated_at": None,
                    "embedding_signature": "",
                },
            )
            job.job_skills.all().delete()
            JobSkill.objects.bulk_create(
                JobSkill(
                    job=job,
                    skill=skills[specification["name"]],
                    is_required=specification["is_required"],
                )
                for specification in row["skills"]
            )
