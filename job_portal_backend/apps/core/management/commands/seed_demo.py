from datetime import timedelta

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import User
from apps.candidates import services as candidate_services
from apps.candidates.models import CandidateProfile
from apps.companies.models import Company
from apps.core.seed_data.demo import (
    ADMIN,
    CANDIDATE,
    CANDIDATE_PROFILE,
    COMPANY,
    EMPLOYER,
    JOB,
)
from apps.jobs import services as job_services
from apps.jobs.models import JobPost
from apps.skills.models import Skill


class Command(BaseCommand):
    help = "Seed demo data: admin user, skills, company, job post."

    def handle(self, *args, **options):
        admin, created = User.objects.get_or_create(
            username=ADMIN["username"],
            defaults={
                "email": ADMIN["email"],
                "role": User.Role.ADMIN,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if created:
            admin.set_password(ADMIN["password"])
            admin.save()
            self.stdout.write(f"Created admin user ({ADMIN['email']}/{ADMIN['password']})")

        call_command("seed_skills_taxonomy")

        employer, created = User.objects.get_or_create(
            username=EMPLOYER["username"],
            defaults={"email": EMPLOYER["email"], "role": User.Role.EMPLOYER},
        )
        if created:
            employer.set_password(EMPLOYER["password"])
            employer.save()

        company_defaults = dict(COMPANY["defaults"], owner=employer)
        company, created = Company.objects.get_or_create(
            name=COMPANY["name"],
            defaults={
                **company_defaults,
                "status": Company.Status.APPROVED,
            },
        )
        if created:
            self.stdout.write(f"Created company: {COMPANY['name']} (APPROVED)")

        job = JobPost.objects.filter(company=company).first()
        if job is None:
            job = JobPost.objects.create(
                company=company,
                created_by=employer,
                title=JOB["title"],
                description=JOB["description"],
                requirements=JOB["requirements"],
                benefits=JOB["benefits"],
                location=JOB["location"],
                workplace_type=JobPost.WorkplaceType.ONSITE,
                job_type=JobPost.JobType.FULL_TIME,
                experience_level=JobPost.ExperienceLevel.MID_SENIOR,
                salary_min=JOB["salary_min"],
                salary_max=JOB["salary_max"],
                status=JobPost.Status.ACTIVE,
                published_at=timezone.now(),
                expires_at=timezone.now() + timedelta(days=30),
            )
            required_skills = Skill.objects.filter(
                slug__in=JOB["required_skill_slugs"]
            )
            if required_skills.exists():
                job.required_skills.add(*required_skills)
            self.stdout.write(f"Created active job: {JOB['title']}")
        if job.embedding_is_stale:
            job_services.enqueue_job_embedding_robust(job)

        candidate_user, created = User.objects.get_or_create(
            username=CANDIDATE["username"],
            defaults={"email": CANDIDATE["email"], "role": User.Role.CANDIDATE},
        )
        if created:
            candidate_user.set_password(CANDIDATE["password"])
            candidate_user.save()
        profile = CandidateProfile.objects.filter(user=candidate_user).first()
        if profile is None:
            profile = CandidateProfile.objects.create(
                user=candidate_user,
                **CANDIDATE_PROFILE,
            )
            self.stdout.write("Created candidate profile")
        if profile.embedding_is_stale:
            candidate_services.enqueue_candidate_embedding(profile)

        self.stdout.write(self.style.SUCCESS(
            f"Seed done. Logins: {ADMIN['email']}/{ADMIN['password']}, "
            f"{EMPLOYER['email']}/{EMPLOYER['password']}, "
            f"{CANDIDATE['email']}/{CANDIDATE['password']}"
        ))
