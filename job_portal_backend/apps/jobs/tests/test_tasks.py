from datetime import timedelta
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import F
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.companies.models import Company
from apps.jobs.models import JDImport, JobPost
from apps.jobs.tasks import (
    MAX_PARSE_ATTEMPTS,
    cleanup_expired_jd_imports,
    generate_job_embedding,
    parse_jd_import,
)
from integrations.gemini.structured_output import ParsedDocumentResult


class JDImportParseAttemptTests(TestCase):
    def setUp(self):
        self.employer = User.objects.create_user(
            username="jd-task-employer",
            email="jd-task-employer@example.com",
            password="password123",
            role=User.Role.EMPLOYER,
        )
        self.company = Company.objects.create(
            owner=self.employer,
            name="JD Task Company",
            status=Company.Status.APPROVED,
        )
        self.jd_import = JDImport.objects.create(
            company=self.company,
            created_by=self.employer,
            file=SimpleUploadedFile("jd.pdf", b"%PDF-1.4 jd", content_type="application/pdf"),
            original_filename="jd.pdf",
            expires_at=timezone.now() + timedelta(hours=24),
        )

    @patch("apps.jobs.tasks.parse_job_description")
    def test_parse_jd_import_stops_after_max_attempts(self, parse_jd):
        parse_jd.side_effect = ValueError("Gemini unavailable")

        for _ in range(MAX_PARSE_ATTEMPTS):
            with self.assertRaises(ValueError):
                parse_jd_import(str(self.jd_import.id))

        self.assertEqual(parse_jd.call_count, MAX_PARSE_ATTEMPTS)
        self.jd_import.refresh_from_db()
        self.assertEqual(self.jd_import.parse_attempts, MAX_PARSE_ATTEMPTS)

        # Lượt gọi thứ N + 1: không parse nữa, giữ FAILED với thông báo cạn lượt.
        self.assertFalse(parse_jd_import(str(self.jd_import.id)))

        self.assertEqual(parse_jd.call_count, MAX_PARSE_ATTEMPTS)
        self.jd_import.refresh_from_db()
        self.assertEqual(self.jd_import.status, JDImport.Status.FAILED)
        self.assertIn("vượt quá", self.jd_import.error_message.lower())

    @patch("apps.jobs.tasks.parse_job_description")
    def test_success_is_stored_and_duplicate_is_idempotent(self, parse_jd):
        parse_jd.return_value = ParsedDocumentResult(
            raw_data={"title": "Backend Developer"},
            validated_data={"title": "Backend Developer"},
        )

        self.assertTrue(parse_jd_import(str(self.jd_import.id)))
        self.assertFalse(parse_jd_import(str(self.jd_import.id)))

        parse_jd.assert_called_once()
        self.jd_import.refresh_from_db()
        self.assertEqual(self.jd_import.status, JDImport.Status.SUCCESS)
        self.assertEqual(self.jd_import.parsed_data["title"], "Backend Developer")

    @patch("apps.jobs.tasks.parse_job_description")
    def test_success_on_final_attempt_is_not_reverted_by_duplicate(self, parse_jd):
        JDImport.objects.filter(pk=self.jd_import.pk).update(
            status=JDImport.Status.FAILED,
            parse_attempts=MAX_PARSE_ATTEMPTS - 1,
        )
        parse_jd.return_value = ParsedDocumentResult(
            raw_data={"title": "Backend Developer"},
            validated_data={"title": "Backend Developer"},
        )

        self.assertTrue(parse_jd_import(str(self.jd_import.id)))
        self.assertFalse(parse_jd_import(str(self.jd_import.id)))

        self.jd_import.refresh_from_db()
        self.assertEqual(self.jd_import.status, JDImport.Status.SUCCESS)
        self.assertEqual(self.jd_import.parse_attempts, MAX_PARSE_ATTEMPTS)

    @patch("apps.jobs.tasks.parse_job_description")
    def test_processing_duplicate_does_not_parse_again(self, parse_jd):
        JDImport.objects.filter(pk=self.jd_import.pk).update(
            status=JDImport.Status.PROCESSING,
            parse_attempts=1,
            updated_at=timezone.now(),
        )

        with self.assertRaises(RuntimeError):
            parse_jd_import(str(self.jd_import.id))

        parse_jd.assert_not_called()

    @patch("apps.jobs.tasks.parse_job_description")
    def test_active_final_attempt_is_not_marked_failed(self, parse_jd):
        JDImport.objects.filter(pk=self.jd_import.pk).update(
            status=JDImport.Status.PROCESSING,
            parse_attempts=MAX_PARSE_ATTEMPTS,
            updated_at=timezone.now(),
        )

        self.assertFalse(parse_jd_import(str(self.jd_import.id)))

        parse_jd.assert_not_called()
        self.jd_import.refresh_from_db()
        self.assertEqual(self.jd_import.status, JDImport.Status.PROCESSING)

    @patch("apps.jobs.tasks.parse_job_description")
    def test_failure_message_does_not_expose_provider_details(self, parse_jd):
        parse_jd.side_effect = RuntimeError("provider-secret-response")

        with self.assertRaises(RuntimeError):
            parse_jd_import(str(self.jd_import.id))

        self.jd_import.refresh_from_db()
        self.assertEqual(self.jd_import.status, JDImport.Status.FAILED)
        self.assertNotIn("provider-secret-response", self.jd_import.error_message)

    @patch("apps.jobs.tasks.parse_job_description")
    def test_expired_worker_cannot_overwrite_newer_attempt(self, parse_jd):
        def newer_worker_claimed(**_kwargs):
            JDImport.objects.filter(pk=self.jd_import.pk).update(
                parse_attempts=F("parse_attempts") + 1,
                status=JDImport.Status.PROCESSING,
                updated_at=timezone.now() + timedelta(seconds=1),
            )
            return ParsedDocumentResult(
                raw_data={"title": "Stale"},
                validated_data={"title": "Stale"},
            )

        parse_jd.side_effect = newer_worker_claimed

        self.assertFalse(parse_jd_import(str(self.jd_import.id)))

        self.jd_import.refresh_from_db()
        self.assertEqual(self.jd_import.status, JDImport.Status.PROCESSING)
        self.assertEqual(self.jd_import.parse_attempts, 2)
        self.assertIsNone(self.jd_import.parsed_data)


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

    @patch("apps.jobs.tasks.embed_document")
    def test_version_changed_during_request_does_not_save_embedding(self, generate):
        def change_version(_content):
            JobPost.objects.filter(pk=self.job.pk).update(
                content_version=F("content_version") + 1
            )
            return [0.2] * 768

        generate.side_effect = change_version

        result = generate_job_embedding(str(self.job.id), self.job.content_version)

        self.assertFalse(result)
        self.job.refresh_from_db()
        self.assertIsNone(self.job.embedding)

    def test_cleanup_removes_expired_import_and_file(self):
        jd_import = JDImport.objects.create(
            company=self.company,
            created_by=self.employer,
            file=SimpleUploadedFile("expired.pdf", b"%PDF-1.4"),
            original_filename="expired.pdf",
            status=JDImport.Status.CONSUMED,
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        storage = jd_import.file.storage
        stored_name = jd_import.file.name

        count = cleanup_expired_jd_imports()

        self.assertEqual(count, 1)
        self.assertFalse(JDImport.objects.filter(pk=jd_import.pk).exists())
        self.assertFalse(storage.exists(stored_name))
