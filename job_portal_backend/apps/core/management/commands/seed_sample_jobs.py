"""Seed 100 balanced, searchable JobPosts from the bundled JD CSV."""
import ast
import csv
from datetime import timedelta
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.companies.models import Company
from apps.jobs import services as job_services
from apps.jobs.models import JobPost, JobSkill
from apps.skills.models import Skill, SkillCategory
from apps.skills.utils import make_unique_slug


User = get_user_model()
CSV_PATH = Path(__file__).with_name("job_descriptions_500_balanced.csv")

# Keep the original 20 rows, then fill every role family to 10 jobs.
INITIAL_GROUP_ROWS = {
    "Backend": [3, 4],
    "Frontend": [17, 33],
    "Full-stack": [0, 1],
    "QA": [21, 30],
    "Mobile": [11, 37],
    "Software/.NET": [44, 242],
    "Game": [51, 99],
    "AI": [59, 94],
    "Business": [23, 127],
    "DevOps/Data": [14, 18],
}

ROLE_GROUPS = {
    "Backend": {
        "Backend Developer", "Backend Engineer", "Backend Intern",
        "Java Developer", "Java Engineer", "Java Software Engineer",
        "PHP Developer", "Senior Java Developer",
    },
    "Frontend": {"Frontend Developer", "Web Developer", "UX/UI Designer"},
    "Full-stack": {
        "Full-stack Developer", "Fullstack Developer",
        "Java/Golang/Angular Developer", "Magento Developer",
    },
    "QA": {
        "QA Engineer", "Automation Tester", "Software Tester",
        "Senior QA Engineer", "Quality Control Engineer",
        "Software Quality Assurance Engineer", "Automation Test Lead",
        "Leader Tester Engineer", "Quality Assurance Manager",
    },
    "Mobile": {
        "Mobile Developer", "Flutter Developer", "iOS Developer",
        "Leader React Native",
    },
    "Software/.NET": {
        "Software Engineer", "Software Developer", ".NET Developer",
        "Senior .NET Developer", "Senior Software Engineer",
        "C#.NET Leader", "C/C++ Developer", "C++ Developer",
        "Senior C++ Developer", "C++/C# Developer",
    },
    "Game": {
        "Game Developer", "Unity Developer", "Playable Ads Developer",
        "Game Designer",
    },
    "AI": {
        "AI Engineer", "Machine Learning Engineer", "Data Scientist",
        "AI Analyst", "Quantitative Developer",
    },
    "Business": {
        "Business Analyst", "Product Manager", "IT Project Manager",
        "Project Manager", "Technical Project Manager",
    },
    "DevOps/Data": {
        "DevOps Engineer", "DevSecOps Engineer", "Data Engineer",
        "Data Engineer Intern", "Data Analyst", "Data Integration Engineer",
        "Cloud Engineer", "Site Reliability Engineer", "Database Engineer",
        "Database Developer", "Database Administrator",
    },
}

SKILL_ALIASES = {
    "ReactJS": "React",
    "React.js": "React",
    "NextJS": "Next.js",
    "NodeJS": "Node.js",
    "ExpressJS": "Express",
    "Golang": "Go",
    "Postgres": "PostgreSQL",
    "Spring": "Spring Boot",
    "Spring Framework": "Spring Boot",
    "REST": "REST API",
    "RESTful": "REST API",
    "RESTful API": "REST API",
    "RESTful APIs": "REST API",
    ".NET": "ASP.NET Core",
    ".NET Core": "ASP.NET Core",
    "ASP.NET": "ASP.NET Core",
    "ASP.NET MVC": "ASP.NET Core",
    "HTML": "HTML/CSS",
    "CSS": "HTML/CSS",
}

SALARY_BY_LEVEL = {
    JobPost.ExperienceLevel.INTERN: (5_000_000, 10_000_000),
    JobPost.ExperienceLevel.FRESHER: (9_000_000, 15_000_000),
    JobPost.ExperienceLevel.JUNIOR: (12_000_000, 22_000_000),
    JobPost.ExperienceLevel.MIDDLE: (20_000_000, 35_000_000),
    JobPost.ExperienceLevel.SENIOR: (30_000_000, 50_000_000),
    JobPost.ExperienceLevel.LEAD: (40_000_000, 70_000_000),
    "": (15_000_000, 30_000_000),
}


def _list_field(raw: str) -> list[str]:
    try:
        value = ast.literal_eval(raw or "[]")
    except (SyntaxError, ValueError):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _experience_level(title: str, description: str) -> str:
    text = f"{title} {description}".lower()
    if "intern" in text or "internship" in text:
        return JobPost.ExperienceLevel.INTERN
    if "fresher" in text or "graduate" in text:
        return JobPost.ExperienceLevel.FRESHER
    if "lead" in text or "manager" in text or "principal" in text:
        return JobPost.ExperienceLevel.LEAD
    if "senior" in text or " sr." in text:
        return JobPost.ExperienceLevel.SENIOR
    if "middle" in text or " mid" in text:
        return JobPost.ExperienceLevel.MIDDLE
    if "junior" in text:
        return JobPost.ExperienceLevel.JUNIOR
    return ""


def _job_type(title: str, description: str) -> str:
    text = f"{title} {description}".lower()
    if "intern" in text:
        return JobPost.JobType.INTERNSHIP
    if "part-time" in text or "part time" in text:
        return JobPost.JobType.PART_TIME
    if "contract" in text or "freelance" in text:
        return JobPost.JobType.CONTRACT
    if "remote" in text:
        return JobPost.JobType.REMOTE
    return JobPost.JobType.FULL_TIME


def _select_rows(rows: list[dict]) -> list[tuple[int, dict]]:
    selected_by_group = {
        group: list(indices) for group, indices in INITIAL_GROUP_ROWS.items()
    }
    used_indices = {
        index for indices in selected_by_group.values() for index in indices
    }
    used_companies = {rows[index]["company"].strip() for index in used_indices}

    for group, roles in ROLE_GROUPS.items():
        for index, row in enumerate(rows):
            if len(selected_by_group[group]) >= 10:
                break
            company = row["company"].strip()
            if (
                index in used_indices
                or row["it_role_type"] not in roles
                or not row["title"].strip()
                or not company
                or company in used_companies
            ):
                continue
            selected_by_group[group].append(index)
            used_indices.add(index)
            used_companies.add(company)

    incomplete = {
        group: len(indices)
        for group, indices in selected_by_group.items()
        if len(indices) != 10
    }
    if incomplete:
        raise ValueError(f"Không đủ JD cho các nhóm: {incomplete}")
    return [
        (index, rows[index])
        for group in ROLE_GROUPS
        for index in selected_by_group[group]
    ]


class Command(BaseCommand):
    help = "Seed 100 balanced ACTIVE jobs from job_descriptions_500_balanced.csv."

    def handle(self, *args, **options):
        with CSV_PATH.open(encoding="utf-8-sig", newline="") as source:
            rows = list(csv.DictReader(source))
        selected = _select_rows(rows)
        skill_category, _ = SkillCategory.objects.get_or_create(name="Imported JD")
        jobs_to_embed = []
        created_count = 0

        with transaction.atomic():
            for order, (source_index, row) in enumerate(selected, start=1):
                email = f"jd.demo.{source_index:03d}@jobportal.local"
                owner, owner_created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        "username": f"jd_demo_{source_index:03d}",
                        "role": User.Role.EMPLOYER,
                    },
                )
                if owner_created:
                    owner.set_password("ChangeMe123!")
                    owner.save(update_fields=["password"])

                company_name = (row["company"].strip() or f"Demo Company {order}")[:255]
                company, _ = Company.objects.update_or_create(
                    owner=owner,
                    defaults={
                        "name": company_name,
                        "description": "Công ty demo nhập từ bộ dữ liệu JD cân bằng.",
                        "address": (row["location"].strip() or row["city"].strip())[:500],
                        "industry": "IT - Software",
                        "status": Company.Status.APPROVED,
                    },
                )

                title = row["title"].strip()[:255]
                description = row["description"].strip()
                languages = _list_field(row["main_programming_languages"])
                technologies = _list_field(row["key_technologies"])
                level = _experience_level(title, description)
                salary_min, salary_max = SALARY_BY_LEVEL[level]
                job, created = JobPost.objects.get_or_create(
                    company=company,
                    title=title,
                    defaults={
                        "created_by": owner,
                        "description": description,
                        "requirements": "\n".join(
                            part
                            for part in [
                                f"Programming languages: {', '.join(languages)}" if languages else "",
                                f"Key technologies: {', '.join(technologies)}" if technologies else "",
                            ]
                            if part
                        ),
                        "location": (row["city"].strip() or row["location"].strip())[:255],
                        "job_type": _job_type(title, description),
                        "experience_level": level,
                        "salary_min": salary_min,
                        "salary_max": salary_max,
                        "salary_negotiable": False,
                        "status": JobPost.Status.ACTIVE,
                        "published_at": timezone.now() - timedelta(hours=100 - order),
                        "expires_at": timezone.now() + timedelta(days=90),
                        "is_active": True,
                    },
                )
                if created:
                    created_count += 1
                    canonical_names = dict.fromkeys(
                        SKILL_ALIASES.get(name, name)
                        for name in [*languages, *technologies]
                        if name and name != "Not Specified"
                    )
                    for skill_name in canonical_names:
                        skill = Skill.objects.filter(name__iexact=skill_name).first()
                        if skill is None:
                            skill = Skill.objects.create(
                                name=skill_name,
                                slug=make_unique_slug(skill_name),
                                category=skill_category,
                                status=Skill.Status.APPROVED,
                                source=Skill.Source.ADMIN_MANUAL,
                            )
                        JobSkill.objects.get_or_create(job=job, skill=skill)
                if created or job.embedding_is_stale:
                    jobs_to_embed.append(job)

        for job in jobs_to_embed:
            job_services.enqueue_job_embedding_robust(job)

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded 100 ACTIVE jobs ({created_count} new); "
                f"queued {len(jobs_to_embed)} embeddings."
            )
        )
