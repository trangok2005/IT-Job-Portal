from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from apps.core.seed_data.demo import JOB
from apps.jobs.models import JobPost


class SeedDemoCommandTests(TestCase):
    def test_demo_job_has_explicit_required_and_optional_skills(self):
        call_command("seed_demo", stdout=StringIO())

        job = JobPost.objects.get(title=JOB["title"])
        flags = {
            link.skill.name: link.is_required
            for link in job.job_skills.select_related("skill")
        }
        self.assertEqual(
            flags,
            {
                "Python": True,
                "Django": True,
                "Django REST Framework": True,
                "PostgreSQL": False,
                "Docker": False,
            },
        )

        call_command("seed_demo", stdout=StringIO())
        self.assertEqual(JobPost.objects.filter(title=JOB["title"]).count(), 1)
