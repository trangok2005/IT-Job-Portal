import tempfile
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import User
from apps.candidates import services
from apps.candidates.models import CandidateProfile, Resume, ResumeImport
from apps.skills.models import Skill


class CandidateServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="candidate",
            email="candidate@example.com",
            password="password123",
            role=User.Role.CANDIDATE,
        )
        self.profile = CandidateProfile.objects.create(
            user=self.user,
            full_name="Nguyen Van A",
        )

    def test_profile_update_bumps_version_and_enqueues_embedding(self):
        with patch("apps.candidates.services.publish_task") as publish_task:
            with self.captureOnCommitCallbacks(execute=True):
                services.update_profile(self.profile, {"headline": "Backend Developer"})

        self.assertEqual(self.profile.profile_version, 2)
        self.assertTrue(self.profile.embedding_is_stale)
        publish_task.assert_called_once_with(
            "generate_candidate_embedding",
            {"profile_id": str(self.profile.pk), "profile_version": 2},
        )

    def test_empty_profile_update_does_not_bump_version(self):
        services.update_profile(self.profile, {})

        self.assertEqual(self.profile.profile_version, 1)

    def test_current_profile_version_can_be_enqueued_without_bumping(self):
        with patch("apps.candidates.services.publish_task") as publish_task:
            with self.captureOnCommitCallbacks(execute=True):
                services.enqueue_candidate_embedding(self.profile)

        self.assertEqual(self.profile.profile_version, 1)
        publish_task.assert_called_once_with(
            "generate_candidate_embedding",
            {"profile_id": str(self.profile.pk), "profile_version": 1},
        )

    def test_education_changes_bump_profile_version(self):
        education = services.create_education(
            self.profile,
            {"school_name": "HUST", "major": "Software Engineering"},
        )
        services.update_education(education, {"degree": "Engineer"})
        services.delete_education(education)

        self.assertEqual(self.profile.profile_version, 4)

    def test_duplicate_candidate_skill_is_rejected(self):
        skill = Skill.objects.create(name="Python", slug="python")
        services.create_candidate_skill(self.profile, skill)

        with self.assertRaisesMessage(ValueError, "đã có"):
            services.create_candidate_skill(self.profile, skill)

    def test_adding_pending_skill_is_allowed_consistently_with_save_all(self):
        pending = Skill.objects.create(
            name="PostgresX", slug="postgresx", status=Skill.Status.PENDING
        )
        version_before = self.profile.profile_version

        candidate_skill = services.create_candidate_skill(self.profile, pending)

        self.assertEqual(candidate_skill.skill.status, Skill.Status.PENDING)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.profile_version, version_before + 1)


class ResumeServiceTests(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.override = override_settings(MEDIA_ROOT=Path(self.temp_dir.name))
        self.override.enable()
        self.addCleanup(self.override.disable)

        user = User.objects.create_user(
            username="candidate-resume",
            email="resume@example.com",
            password="password123",
            role=User.Role.CANDIDATE,
        )
        self.profile = CandidateProfile.objects.create(user=user, full_name="Resume User")

    def _file(self, name="cv.pdf"):
        return SimpleUploadedFile(name, b"%PDF-1.4 test", content_type="application/pdf")

    def _parsed_import(self, name="cv.pdf"):
        resume_import = services.create_resume_import(self.profile, self._file(name))
        resume_import.parse_status = ResumeImport.ParseStatus.SUCCESS
        resume_import.parsed_data = {"full_name": "Parsed User", "skills": ["Python"]}
        resume_import.save()
        return resume_import

    def test_create_import_enqueues_only_parser_without_bumping_profile(self):
        with patch("apps.candidates.services.publish_task") as publish_task:
            with self.captureOnCommitCallbacks(execute=True):
                resume_import = services.create_resume_import(
                    self.profile, self._file()
                )
                publish_task.assert_not_called()

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.profile_version, 1)
        publish_task.assert_called_once_with(
            "parse_resume_import",
            {"resume_import_id": str(resume_import.pk)},
        )

    def test_consumed_resume_replaces_primary_flag(self):
        first = services.consume_resume_import(
            self._parsed_import("first.pdf")
        )
        second = services.consume_resume_import(
            self._parsed_import("second.pdf")
        )

        first.refresh_from_db()
        self.assertFalse(first.is_primary)
        self.assertTrue(second.is_primary)
        self.assertEqual(self.profile.resumes.filter(is_primary=True).count(), 1)

    def test_deleting_primary_selects_newest_remaining_resume(self):
        first = services.consume_resume_import(self._parsed_import("first.pdf"))
        second = services.consume_resume_import(self._parsed_import("second.pdf"))

        services.delete_resume(first)

        second.refresh_from_db()
        self.assertTrue(second.is_primary)

    def test_database_rejects_multiple_primary_resumes(self):
        services.consume_resume_import(self._parsed_import("first.pdf"))

        with self.assertRaises(IntegrityError), transaction.atomic():
            Resume.objects.create(
                candidate=self.profile,
                file=self._file("second.pdf"),
                original_filename="second.pdf",
                is_primary=True,
            )

    def test_full_profile_save_replaces_snapshot_and_enqueues_once(self):
        skill = Skill.objects.create(name="Python", slug="save-python")
        resume_import = self._parsed_import()

        with patch("apps.candidates.services.publish_task") as publish_task:
            with self.captureOnCommitCallbacks(execute=True):
                services.save_full_profile(
                    self.profile,
                    {
                        "full_name": "Reviewed User",
                        "phone": "0901234567",
                        "headline": "Backend Developer",
                        "summary": "Reviewed summary",
                        "desired_position": "Backend Developer",
                        "educations": [{"school_name": "HUST", "major": "IT"}],
                        "experiences": [{
                            "company_name": "Tech",
                            "position": "Developer",
                            "is_current": True,
                        }],
                        "skills": [{"skill": skill}],
                        "resume_import_id": resume_import.id,
                    },
                )

        self.profile.refresh_from_db()
        resume_import.refresh_from_db()
        self.assertEqual(self.profile.profile_version, 2)
        self.assertEqual(self.profile.full_name, "Reviewed User")
        self.assertEqual(self.profile.educations.count(), 1)
        self.assertEqual(self.profile.experiences.count(), 1)
        self.assertEqual(self.profile.candidate_skills.count(), 1)
        self.assertEqual(resume_import.parse_status, ResumeImport.ParseStatus.CONSUMED)
        primary = self.profile.resumes.get(is_primary=True)
        self.assertEqual(primary.original_filename, resume_import.original_filename)
        self.assertNotEqual(primary.file.name, resume_import.file.name)
        publish_task.assert_called_once_with(
            "generate_candidate_embedding",
            {"profile_id": str(self.profile.pk), "profile_version": 2},
        )

    def test_consume_rejects_non_success_import(self):
        with patch("apps.candidates.services.publish_task"):
            resume_import = services.create_resume_import(self.profile, self._file())

        with self.assertRaisesMessage(ValueError, "parse thành công"):
            services.consume_resume_import(resume_import)

    def test_delete_consumed_import_keeps_primary_resume_file(self):
        resume_import = self._parsed_import()
        resume = services.consume_resume_import(resume_import)
        stored_name = resume.file.name
        import_id = resume_import.pk
        temporary_name = resume_import.file.name

        with self.captureOnCommitCallbacks(execute=True):
            services.delete_resume_import(resume_import)
            self.assertTrue(resume_import.file.storage.exists(temporary_name))

        self.assertFalse(ResumeImport.objects.filter(pk=import_id).exists())
        self.assertTrue(resume.file.storage.exists(stored_name))
        self.assertFalse(resume_import.file.storage.exists(temporary_name))

    def test_save_rejects_expired_import_without_changing_profile(self):
        resume_import = self._parsed_import()
        resume_import.expires_at = timezone.now() - timedelta(seconds=1)
        resume_import.save()

        with self.assertRaises(ValueError):
            services.save_full_profile(self.profile, {
                "full_name": "Changed",
                "educations": [],
                "experiences": [],
                "skills": [],
                "resume_import_id": resume_import.pk,
            })

        self.profile.refresh_from_db()
        resume_import.refresh_from_db()
        self.assertEqual(self.profile.full_name, "Resume User")
        self.assertEqual(self.profile.profile_version, 1)
        self.assertEqual(resume_import.parse_status, ResumeImport.ParseStatus.SUCCESS)
        self.assertFalse(self.profile.resumes.exists())

    def test_consume_rejects_expired_import(self):
        resume_import = self._parsed_import()
        resume_import.expires_at = timezone.now() - timedelta(seconds=1)

        with self.assertRaisesMessage(ValueError, "hết hạn"):
            services.consume_resume_import(resume_import)

    def test_save_checks_import_status(self):
        record = self._parsed_import()
        for parse_status in (
            ResumeImport.ParseStatus.PENDING,
            ResumeImport.ParseStatus.PROCESSING,
            ResumeImport.ParseStatus.FAILED,
            ResumeImport.ParseStatus.CONSUMED,
        ):
            with self.subTest(status=parse_status):
                ResumeImport.objects.filter(pk=record.pk).update(parse_status=parse_status)
                with self.assertRaises(ValueError):
                    services.save_full_profile(self.profile, {
                        "educations": [], "experiences": [], "skills": [],
                        "resume_import_id": record.pk,
                    })
        self.assertFalse(self.profile.resumes.exists())

    def test_cancelled_import_delete_removes_file(self):
        with patch("apps.candidates.services.publish_task"):
            resume_import = services.create_resume_import(self.profile, self._file())
        stored_name = resume_import.file.name

        with self.captureOnCommitCallbacks(execute=True):
            services.delete_resume_import(resume_import)

        self.assertFalse(resume_import.file.storage.exists(stored_name))
