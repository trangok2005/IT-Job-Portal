from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import User
from apps.candidates import services as candidate_services
from apps.candidates.models import CandidateProfile
from apps.companies.models import Company
from apps.jobs import services as job_services
from apps.jobs.models import JobPost
from apps.skills.models import Skill, SkillCategory


class Command(BaseCommand):
    help = "Seed demo data: admin user, skills, company, job post."

    def handle(self, *args, **options):
        admin, created = User.objects.get_or_create(
            username="admin",
            defaults={"email": "admin@gmail.com", "role": User.Role.ADMIN, "is_staff": True, "is_superuser": True},
        )
        if created:
            admin.set_password("admin123")
            admin.save()
            self.stdout.write("Created admin user (admin@gmail.com/admin123)")

        category, _ = SkillCategory.objects.get_or_create(name="Programming Language")
        skill_names = ["Python", "Django", "React", "PostgreSQL", "Docker", "TypeScript"]
        for name in skill_names:
            skill, created = Skill.objects.get_or_create(
                slug=name.lower(),
                defaults={"name": name, "category": category},
            )
            if created:
                self.stdout.write(f"Created skill: {name}")

        employer, created = User.objects.get_or_create(
            username="employer",
            defaults={"email": "employer@gmail.com", "role": User.Role.EMPLOYER},
        )
        if created:
            employer.set_password("employer123")
            employer.save()

        company, created = Company.objects.get_or_create(
            name="TechCorp Vietnam",
            defaults={
                "owner": employer,
                "tax_code": "0123456789",
                "description": "Công ty công nghệ chuyên phát triển sản phẩm phần mềm.",
                "website": "https://techcorp.example.com",
                "address": "Hà Nội, Việt Nam",
                "company_size": "50-100",
                "industry": "IT - Software",
                "status": Company.Status.APPROVED,
            },
        )
        if created:
            self.stdout.write("Created company: TechCorp Vietnam (APPROVED)")

        job = JobPost.objects.filter(company=company).first()
        if job is None:
            job = JobPost.objects.create(
                company=company,
                created_by=employer,
                title="Backend Developer (Python/Django)",
                description="Phát triển hệ thống job portal với Django REST Framework, PostgreSQL + pgvector.",
                requirements="3 năm kinh nghiệm Python/Django, PostgreSQL, Docker.",
                benefits="Lương thưởng hấp dẫn, bảo hiểm đầy đủ, môi trường trẻ trung.",
                location="Hà Nội",
                job_type=JobPost.JobType.FULL_TIME,
                experience_level=JobPost.ExperienceLevel.MIDDLE,
                salary_min=15000000,
                salary_max=25000000,
                status=JobPost.Status.ACTIVE,
                published_at=timezone.now(),
                expires_at=timezone.now() + timedelta(days=30),
            )
            python_skill = Skill.objects.get(slug="python")
            django_skill = Skill.objects.get(slug="django")
            job.required_skills.add(python_skill, django_skill)
            self.stdout.write("Created active job: Backend Developer (Python/Django)")
        if job.embedding_is_stale:
            job_services.enqueue_job_embedding_robust(job)

        candidate_user, created = User.objects.get_or_create(
            username="candidate",
            defaults={"email": "candidate@gmail.com", "role": User.Role.CANDIDATE},
        )
        if created:
            candidate_user.set_password("candidate123")
            candidate_user.save()
        profile = CandidateProfile.objects.filter(user=candidate_user).first()
        if profile is None:
            profile = CandidateProfile.objects.create(
                user=candidate_user,
                full_name="Nguyễn Văn Ứng Viên",
                headline="Backend Developer 2 năm kinh nghiệm",
                summary="Yêu thích Python/Django.",
            )
            self.stdout.write("Created candidate profile")
        if profile.embedding_is_stale:
            candidate_services.enqueue_candidate_embedding(profile)

        self.stdout.write(self.style.SUCCESS(
            "Seed done. Logins: admin@gmail.com/admin123, "
            "employer@gmail.com/employer123, "
            "candidate@gmail.com/candidate123"
        ))
