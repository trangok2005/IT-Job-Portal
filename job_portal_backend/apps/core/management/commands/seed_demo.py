from datetime import timedelta

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.accounts.models import User
from apps.candidates import services as candidate_services
from apps.candidates.models import CandidateProfile, DegreeLevel, Education
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
from apps.jobs.models import JobPost, JobSkill
from apps.skills.models import CandidateSkill, MatchingWeightConfig, Skill


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
        MatchingWeightConfig.objects.update(is_active=False)
        MatchingWeightConfig.objects.update_or_create(
            name="Cấu hình mặc định",
            defaults={
                "is_active": True,
                "weight_semantic_similarity": "0.350",
                "weight_skill_overlap": "0.400",
                "weight_experience_match": "0.200",
                "weight_education_match": "0.050",
                "required_skill_multiplier": "2.000",
                "updated_by": admin,
            },
        )

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

        job_defaults = {
            "created_by": employer,
            "description": JOB["description"],
            "requirements": JOB["requirements"],
            "benefits": JOB["benefits"],
            "location": JOB["location"],
            "workplace_type": JobPost.WorkplaceType.ONSITE,
            "job_type": JobPost.JobType.FULL_TIME,
            "experience_level": JobPost.ExperienceLevel.MID_SENIOR,
            "required_education_level": DegreeLevel.BACHELOR,
            "salary_min": JOB["salary_min"],
            "salary_max": JOB["salary_max"],
            "status": JobPost.Status.ACTIVE,
            "published_at": timezone.now(),
            "expires_at": timezone.now() + timedelta(days=30),
        }
        job, created = JobPost.objects.update_or_create(
            company=company,
            title=JOB["title"],
            defaults=job_defaults,
        )
        if not created:
            job.content_version += 1
            job.embedding = None
            job.embedding_version = 0
            job.embedding_updated_at = None
            job.embedding_signature = ""
            job.save(update_fields=[
                "content_version",
                "embedding",
                "embedding_version",
                "embedding_updated_at",
                "embedding_signature",
                "updated_at",
            ])
        skill_by_name = {
            skill.name: skill
            for skill in Skill.objects.filter(
                name__in=[item["name"] for item in JOB["skills"]]
            )
        }
        missing = [
            item["name"]
            for item in JOB["skills"]
            if item["name"] not in skill_by_name
        ]
        if missing:
            raise CommandError(f"Demo skills chưa có trong taxonomy: {', '.join(missing)}")
        job.job_skills.all().delete()
        JobSkill.objects.bulk_create(
            JobSkill(
                job=job,
                skill=skill_by_name[item["name"]],
                is_required=item["is_required"],
            )
            for item in JOB["skills"]
        )
        if created:
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
            profile = CandidateProfile.objects.create(user=candidate_user, **CANDIDATE_PROFILE)
            self.stdout.write("Created candidate profile")
        else:
            changed_fields = [
                field for field, value in CANDIDATE_PROFILE.items()
                if getattr(profile, field) != value
            ]
            if changed_fields:
                for field in changed_fields:
                    setattr(profile, field, CANDIDATE_PROFILE[field])
                profile.profile_version += 1
                profile.embedding = None
                profile.embedding_version = 0
                profile.embedding_signature = ""
                profile.save(update_fields=[
                    *changed_fields,
                    "profile_version",
                    "embedding",
                    "embedding_version",
                    "embedding_signature",
                    "updated_at",
                ])
        python_skill = Skill.objects.get(name="Python")
        CandidateSkill.objects.get_or_create(candidate=profile, skill=python_skill)
        Education.objects.update_or_create(
            candidate=profile,
            school_name="Đại học Công nghệ",
            defaults={
                "degree": "Cử nhân",
                "degree_level": DegreeLevel.BACHELOR,
                "is_completed": True,
                "is_verified": True,
            },
        )
        if profile.embedding_is_stale:
            candidate_services.enqueue_candidate_embedding(profile)

        self.stdout.write(self.style.SUCCESS(
            f"Seed done. Logins: {ADMIN['email']}/{ADMIN['password']}, "
            f"{EMPLOYER['email']}/{EMPLOYER['password']}, "
            f"{CANDIDATE['email']}/{CANDIDATE['password']}"
        ))
