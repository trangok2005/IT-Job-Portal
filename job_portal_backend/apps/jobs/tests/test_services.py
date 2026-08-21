from datetime import timedelta
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.companies.models import Company
from apps.jobs import services
from apps.jobs.models import JDImport, JobPost
from apps.skills.models import Skill


class JobServiceTests(TestCase):
    def setUp(self):
        self.employer = User.objects.create_user(
            username="job-employer",
            email="job-employer@example.com",
            password="password123",
            role=User.Role.EMPLOYER,
        )
        self.company = Company.objects.create(
            owner=self.employer,
            name="Job Company",
            status=Company.Status.APPROVED,
        )
        self.skill = Skill.objects.create(name="Python", slug="python")

    def _create_job(self, **overrides):
        data = {
            "title": "Backend Developer",
            "description": "Build APIs",
            "expires_at": timezone.now() + timedelta(days=30),
        }
        data.update(overrides)
        return services.create_job(
            self.employer,
            self.company,
            data,
            required_skills=[self.skill],
        )

    def test_create_job_always_creates_draft(self):
        job = self._create_job()

        self.assertEqual(job.status, JobPost.Status.DRAFT)
        self.assertEqual(job.created_by, self.employer)
        self.assertEqual(list(job.required_skills.all()), [self.skill])

    def test_create_job_consumes_successful_jd_import(self):
        jd_import = JDImport.objects.create(
            company=self.company,
            created_by=self.employer,
            file=SimpleUploadedFile("job.pdf", b"%PDF-1.4"),
            original_filename="job.pdf",
            status=JDImport.Status.SUCCESS,
            raw_extracted_json={"title": "Backend Developer"},
            parsed_data={"title": "Backend Developer"},
            expires_at=timezone.now() + timedelta(hours=1),
        )

        job = services.create_job(
            self.employer,
            self.company,
            {"title": "Backend Developer", "description": "Build APIs"},
            jd_import_id=jd_import.id,
        )

        jd_import.refresh_from_db()
        self.assertEqual(jd_import.status, JDImport.Status.CONSUMED)
        self.assertEqual(jd_import.consumed_job, job)
        self.assertEqual(job.raw_extracted_json, jd_import.raw_extracted_json)
        self.assertEqual(job.raw_jd_file.name, jd_import.file.name)

    def test_cancel_jd_import_deletes_unconsumed_import(self):
        jd_import = JDImport.objects.create(
            company=self.company,
            created_by=self.employer,
            file=SimpleUploadedFile("job.pdf", b"%PDF-1.4"),
            original_filename="job.pdf",
            status=JDImport.Status.SUCCESS,
            expires_at=timezone.now() + timedelta(hours=1),
        )

        services.cancel_jd_import(jd_import)

        self.assertFalse(JDImport.objects.filter(pk=jd_import.pk).exists())

    def test_create_job_rejects_unapproved_company(self):
        self.company.status = Company.Status.PENDING
        self.company.save()

        with self.assertRaisesMessage(ValueError, "chưa được duyệt"):
            self._create_job()

    def test_publish_enqueues_embedding_after_commit(self):
        job = self._create_job()

        with patch("django_q.tasks.async_task") as async_task:
            with self.captureOnCommitCallbacks(execute=True):
                services.publish_job(job)

        self.assertEqual(job.status, JobPost.Status.ACTIVE)
        self.assertIsNotNone(job.published_at)
        async_task.assert_called_once_with(
            "apps.jobs.tasks.generate_job_embedding",
            str(job.pk),
            job.content_version,
        )

    def test_closed_job_cannot_be_published_again(self):
        job = self._create_job()
        services.publish_job(job)
        services.close_job(job)

        with self.assertRaisesMessage(ValueError, "tin nháp"):
            services.publish_job(job)

    def test_active_update_bumps_version_and_enqueues_embedding(self):
        job = self._create_job()
        services.publish_job(job)

        with patch("django_q.tasks.async_task") as async_task:
            with self.captureOnCommitCallbacks(execute=True):
                services.update_job(job, {"description": "Updated APIs"})

        self.assertEqual(job.content_version, 2)
        async_task.assert_called_once_with(
            "apps.jobs.tasks.generate_job_embedding",
            str(job.pk),
            2,
        )

    def test_expire_jobs_marks_only_past_active_jobs(self):
        expired = JobPost.objects.create(
            company=self.company,
            created_by=self.employer,
            title="Expired",
            description="Expired job",
            status=JobPost.Status.ACTIVE,
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        current = JobPost.objects.create(
            company=self.company,
            created_by=self.employer,
            title="Current",
            description="Current job",
            status=JobPost.Status.ACTIVE,
            expires_at=timezone.now() + timedelta(days=1),
        )

        count = services.expire_jobs()

        expired.refresh_from_db()
        current.refresh_from_db()
        self.assertEqual(count, 1)
        self.assertEqual(expired.status, JobPost.Status.EXPIRED)
        self.assertEqual(current.status, JobPost.Status.ACTIVE)
