import tempfile
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import User
from apps.applications import services
from apps.applications.models import ApplicationStatusHistory, JobApplication
from apps.candidates.models import CandidateProfile, Resume
from apps.companies.models import Company
from apps.jobs.models import JobPost
from apps.skills.models import CandidateSkill, Skill


class ApplicationServiceTests(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.override = override_settings(MEDIA_ROOT=Path(self.temp_dir.name))
        self.override.enable()
        self.addCleanup(self.override.disable)

        self.employer = User.objects.create_user(
            username="application-employer",
            email="application-employer@example.com",
            password="password123",
            role=User.Role.EMPLOYER,
        )
        self.company = Company.objects.create(
            owner=self.employer,
            name="Application Company",
            status=Company.Status.APPROVED,
        )
        self.job = JobPost.objects.create(
            company=self.company,
            created_by=self.employer,
            title="Backend Developer",
            description="Build APIs",
            status=JobPost.Status.ACTIVE,
            expires_at=timezone.now() + timedelta(days=30),
        )
        self.candidate_user = User.objects.create_user(
            username="application-candidate",
            email="application-candidate@example.com",
            password="password123",
            role=User.Role.CANDIDATE,
        )
        self.profile = CandidateProfile.objects.create(
            user=self.candidate_user,
            full_name="Nguyen Van A",
            phone="0901234567",
            desired_position="Backend Developer",
        )
        self.resume = Resume.objects.create(
            candidate=self.profile,
            file=SimpleUploadedFile("cv.pdf", b"%PDF-1.4 test"),
            original_filename="cv.pdf",
            is_primary=True,
        )
        self.skill = Skill.objects.create(
            name="Django",
            slug="application-django",
            status=Skill.Status.APPROVED,
        )
        CandidateSkill.objects.create(candidate=self.profile, skill=self.skill)

    def test_apply_creates_history_and_match_task(self):
        with patch("django_q.tasks.async_task") as async_task:
            with self.captureOnCommitCallbacks(execute=True):
                application = services.apply_to_job(
                    self.candidate_user,
                    self.job,
                    "I am interested",
                    attach_current_resume=True,
                )

        self.assertEqual(application.status, JobApplication.Status.APPLIED)
        self.assertEqual(application.resume, self.resume)
        self.assertEqual(application.profile_snapshot["profile_version"], 1)
        self.assertEqual(application.profile_snapshot["skills"][0]["name"], "Django")
        self.assertIsNotNone(application.snapshot_created_at)
        history = ApplicationStatusHistory.objects.get(application=application)
        self.assertEqual(history.from_status, "")
        self.assertEqual(history.to_status, JobApplication.Status.APPLIED)
        async_task.assert_called_once_with(
            "apps.ai_analysis.tasks.compute_application_match_score",
            str(application.pk),
        )

    def test_incomplete_profile_cannot_apply(self):
        self.profile.phone = ""
        self.profile.save()

        with self.assertRaisesMessage(ValueError, "chưa hoàn chỉnh"):
            services.apply_to_job(self.candidate_user, self.job)

    def test_profile_without_skill_cannot_apply(self):
        self.profile.candidate_skills.all().delete()

        with self.assertRaisesMessage(ValueError, "ít nhất một kỹ năng"):
            services.apply_to_job(self.candidate_user, self.job)

    def test_candidate_can_apply_without_resume_attachment(self):
        application = services.apply_to_job(self.candidate_user, self.job)

        self.assertIsNone(application.resume)

    def test_attaching_resume_requires_a_primary_resume(self):
        self.resume.is_primary = False
        self.resume.save(update_fields=["is_primary"])

        with self.assertRaisesMessage(ValueError, "chưa có CV chính"):
            services.apply_to_job(
                self.candidate_user,
                self.job,
                attach_current_resume=True,
            )

    def test_candidate_cannot_apply_twice(self):
        services.apply_to_job(self.candidate_user, self.job)

        with self.assertRaisesMessage(ValueError, "đã ứng tuyển"):
            services.apply_to_job(self.candidate_user, self.job)

    def test_closed_job_rejects_new_application(self):
        self.job.status = JobPost.Status.CLOSED
        self.job.save()

        with self.assertRaisesMessage(ValueError, "không còn nhận hồ sơ"):
            services.apply_to_job(self.candidate_user, self.job)

    def test_valid_state_machine_reaches_hired(self):
        application = services.apply_to_job(self.candidate_user, self.job)

        services.transition_application(
            application,
            self.employer,
            JobApplication.Status.SHORTLISTED,
        )
        services.transition_application(
            application,
            self.employer,
            JobApplication.Status.INTERVIEWED,
        )
        services.transition_application(
            application,
            self.employer,
            JobApplication.Status.HIRED,
        )

        self.assertEqual(application.status, JobApplication.Status.HIRED)
        self.assertEqual(application.status_history.count(), 4)

    def test_invalid_transition_keeps_original_status(self):
        application = services.apply_to_job(self.candidate_user, self.job)

        with self.assertRaisesMessage(ValueError, "Không thể chuyển"):
            services.transition_application(
                application,
                self.employer,
                JobApplication.Status.HIRED,
            )

        application.refresh_from_db()
        self.assertEqual(application.status, JobApplication.Status.APPLIED)

    def test_existing_application_can_transition_after_job_closed(self):
        application = services.apply_to_job(self.candidate_user, self.job)
        self.job.status = JobPost.Status.CLOSED
        self.job.save()

        services.transition_application(
            application,
            self.employer,
            JobApplication.Status.SHORTLISTED,
        )

        self.assertEqual(application.status, JobApplication.Status.SHORTLISTED)

    def test_model_clean_rejects_invalid_direct_transition(self):
        application = services.apply_to_job(self.candidate_user, self.job)
        application.status = JobApplication.Status.HIRED

        with self.assertRaises(ValidationError):
            application.full_clean()
