import os
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from apps.accounts.models import User
from apps.companies.models import Company
from apps.core.seed_data.candidates import CANDIDATES
from apps.jobs.models import JobPost


SEED_ENV = {
    "SEED_ADMIN_PASSWORD": "AdminDemo!2026",
    "SEED_EMPLOYER_PASSWORD": "EmployerDemo!2026",
    "SEED_CANDIDATE_PASSWORD": "CandidateDemo!2026",
}


class SeedRenderDemoTests(TestCase):
    @patch.dict(os.environ, SEED_ENV)
    def test_seed_is_complete_and_idempotent(self):
        call_command("seed_render_demo", stdout=StringIO())
        call_command("seed_render_demo", stdout=StringIO())

        admin = User.objects.get(email="admin.demo@jobportal.local")
        employer = User.objects.get(email="employer.demo@jobportal.local")
        company = Company.objects.get(owner=employer)

        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.check_password(SEED_ENV["SEED_ADMIN_PASSWORD"]))
        self.assertEqual(employer.role, User.Role.EMPLOYER)
        self.assertEqual(company.status, Company.Status.APPROVED)
        self.assertEqual(JobPost.objects.filter(company=company).count(), 50)
        self.assertEqual(
            User.objects.filter(email__in=[item["email"] for item in CANDIDATES]).count(),
            10,
        )

        with patch(
            "apps.core.management.commands.rebuild_embeddings.publish_task"
        ) as publish_task:
            call_command(
                "rebuild_embeddings",
                stagger_seconds=5,
                stdout=StringIO(),
            )

        self.assertEqual(publish_task.call_count, 60)
        self.assertIsNone(publish_task.call_args_list[0].kwargs["delay"])
        self.assertEqual(publish_task.call_args_list[-1].kwargs["delay"], 295)
