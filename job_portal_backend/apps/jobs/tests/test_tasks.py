from datetime import timedelta
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.companies.models import Company
from apps.jobs.models import JDImport, JobPost
from apps.jobs.tasks import cleanup_expired_jd_imports, generate_job_embedding


class JobEmbeddingTaskTests(TestCase):
    def setUp(self):
        self.employer = User.objects.create_user(
            username="task-employer",
            email="task-employer@example.com",
            password="password123",
            role=User.Role.EMPLOYER,
        )
        self.company = Company.objects.create(
            owner=self.employer,
            name="Task Company",
            status=Company.Status.APPROVED,
        )
        self.job = JobPost.objects.create(
            company=self.company,
            created_by=self.employer,
            title="Backend Developer",
            description="Python Django",
            status=JobPost.Status.ACTIVE,
        )

    @patch("apps.jobs.tasks.embed_document", return_value=[0.2] * 768)
    def test_embedding_is_saved_for_current_content_version(self, generate):

        result = generate_job_embedding(
            str(self.job.id),
            self.job.content_version,
        )

        self.assertTrue(result)
        self.job.refresh_from_db()
        self.assertEqual(self.job.embedding_version, self.job.content_version)
        self.assertFalse(self.job.embedding_is_stale)
        self.assertEqual(
            generate.call_args.args[0],
            "Position: Backend Developer\n"
            "Role summary: Python Django",
        )

    @patch("apps.jobs.tasks.embed_document")
    def test_stale_task_does_not_call_gemini(self, generate):
        result = generate_job_embedding(str(self.job.id), 999)

        self.assertFalse(result)
        generate.assert_not_called()

    def test_cleanup_removes_expired_import_and_file(self):
        jd_import = JDImport.objects.create(
            company=self.company,
            created_by=self.employer,
            file=SimpleUploadedFile("expired.pdf", b"%PDF-1.4"),
            original_filename="expired.pdf",
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        storage = jd_import.file.storage
        stored_name = jd_import.file.name

        count = cleanup_expired_jd_imports()

        self.assertEqual(count, 1)
        self.assertFalse(JDImport.objects.filter(pk=jd_import.pk).exists())
        self.assertFalse(storage.exists(stored_name))
