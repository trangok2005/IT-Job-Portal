import tempfile
from pathlib import Path
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings

from apps.accounts.models import User
from apps.candidates.models import CandidateProfile, Education, Resume, ResumeImport
from apps.candidates import services
from apps.skills.models import CandidateSkill, Skill


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
        with patch("django_q.tasks.async_task") as async_task:
            with self.captureOnCommitCallbacks(execute=True):
                services.update_profile(self.profile, {"headline": "Backend Developer"})

        self.assertEqual(self.profile.profile_version, 2)
        self.assertTrue(self.profile.embedding_is_stale)
        async_task.assert_called_once_with(
            "apps.candidates.tasks.generate_candidate_embedding",
            str(self.profile.pk),
            2,
        )

    def test_empty_profile_update_does_not_bump_version(self):
        services.update_profile(self.profile, {})

        self.assertEqual(self.profile.profile_version, 1)

    def test_current_profile_version_can_be_enqueued_without_bumping(self):
        with patch("django_q.tasks.async_task") as async_task:
            with self.captureOnCommitCallbacks(execute=True):
                services.enqueue_candidate_embedding(self.profile)

        self.assertEqual(self.profile.profile_version, 1)
        async_task.assert_called_once_with(
            "apps.candidates.tasks.generate_candidate_embedding",
            str(self.profile.pk),
            1,
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

    def test_upload_enqueues_only_parser_without_bumping_profile(self):
        with patch("django_q.tasks.async_task") as async_task:
            with self.captureOnCommitCallbacks(execute=True):
                resume = services.upload_resume(self.profile, self._file())

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.profile_version, 1)
        async_task.assert_called_once_with(
            "apps.candidates.tasks.parse_resume",
            str(resume.pk),
        )

    def test_first_resume_is_primary_and_second_can_replace_it(self):
        first = services.upload_resume(self.profile, self._file("first.pdf"))
        second = services.upload_resume(
            self.profile,
            self._file("second.pdf"),
            is_primary=True,
        )

        first.refresh_from_db()
        self.assertFalse(first.is_primary)
        self.assertTrue(second.is_primary)
        self.assertEqual(self.profile.resumes.filter(is_primary=True).count(), 1)

    def test_deleting_primary_selects_newest_remaining_resume(self):
        first = services.upload_resume(self.profile, self._file("first.pdf"))
        second = services.upload_resume(self.profile, self._file("second.pdf"))

        services.delete_resume(first)

        second.refresh_from_db()
        self.assertTrue(second.is_primary)

    def test_database_rejects_multiple_primary_resumes(self):
        services.upload_resume(self.profile, self._file("first.pdf"))

        with self.assertRaises(IntegrityError), transaction.atomic():
            Resume.objects.create(
                candidate=self.profile,
                file=self._file("second.pdf"),
                original_filename="second.pdf",
                is_primary=True,
            )

    def test_mark_resume_parsed_stores_preview_without_updating_profile(self):
        resume = services.upload_resume(self.profile, self._file())

        services.mark_resume_parsed(
            resume,
            {"full_name": "Parsed User", "skills": ["Python"]},
        )

        self.assertEqual(resume.parse_status, Resume.ParseStatus.SUCCESS)
        self.assertEqual(
            resume.raw_extracted_json,
            {"full_name": "Parsed User", "skills": ["Python"]},
        )
        self.assertEqual(
            resume.parsed_data,
            {"full_name": "Parsed User", "skills": ["Python"]},
        )
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.full_name, "Resume User")
        self.assertFalse(CandidateSkill.objects.filter(candidate=self.profile).exists())
        self.assertEqual(self.profile.profile_version, 1)

    def test_full_profile_save_replaces_snapshot_and_enqueues_once(self):
        skill = Skill.objects.create(name="Python", slug="save-python")
        with patch("django_q.tasks.async_task"):
            resume_import = services.create_resume_import(self.profile, self._file())
        services.mark_resume_import_parsed(
            resume_import,
            {"headline": "Preview"},
            {"headline": "Preview"},
        )

        with patch("django_q.tasks.async_task") as async_task:
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
                        "skills": [{"skill": skill, "level": "ADVANCED"}],
                        "resume_import_id": resume_import.id,
                    },
                )

        self.profile.refresh_from_db()
        resume_import.refresh_from_db()
        self.assertEqual(self.profile.profile_version, 2)
        self.assertEqual(self.profile.full_name, "Reviewed User")
        self.assertEqual(self.profile.educations.get().source, "MANUAL")
        self.assertEqual(self.profile.experiences.get().source, "MANUAL")
        self.assertEqual(
            self.profile.candidate_skills.get().source,
            CandidateSkill.Source.MANUAL,
        )
        self.assertEqual(resume_import.parse_status, ResumeImport.ParseStatus.CONSUMED)
        primary = self.profile.resumes.get(is_primary=True)
        self.assertEqual(primary.original_filename, resume_import.original_filename)
        self.assertNotEqual(primary.file.name, resume_import.file.name)
        async_task.assert_called_once_with(
            "apps.candidates.tasks.generate_candidate_embedding",
            str(self.profile.pk),
            2,
        )

    def test_consume_rejects_non_success_import(self):
        with patch("django_q.tasks.async_task"):
            resume_import = services.create_resume_import(self.profile, self._file())

        with self.assertRaisesMessage(ValueError, "parse thành công"):
            services.consume_resume_import(resume_import)

    def test_delete_consumed_import_keeps_primary_resume_file(self):
        with patch("django_q.tasks.async_task"):
            resume_import = services.create_resume_import(self.profile, self._file())
        services.mark_resume_import_parsed(resume_import, {}, {})
        resume = services.consume_resume_import(resume_import)
        stored_name = resume.file.name

        services.delete_resume_import(resume_import)

        self.assertFalse(ResumeImport.objects.filter(pk=resume_import.pk).exists())
        self.assertTrue(resume.file.storage.exists(stored_name))

    def test_cancelled_import_delete_removes_file(self):
        with patch("django_q.tasks.async_task"):
            resume_import = services.create_resume_import(self.profile, self._file())
        stored_name = resume_import.file.name

        with self.captureOnCommitCallbacks(execute=True):
            services.delete_resume_import(resume_import)

        self.assertFalse(resume_import.file.storage.exists(stored_name))
