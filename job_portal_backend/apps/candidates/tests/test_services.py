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
        return services.mark_resume_import_parsed(
            resume_import,
            {"full_name": "Parsed User", "skills": ["Python"]},
        )

    def test_create_import_enqueues_only_parser_without_bumping_profile(self):
        with patch("apps.candidates.services.publish_task") as publish_task:
            with self.captureOnCommitCallbacks(execute=True):
                resume_import = services.create_resume_import(
                    self.profile, self._file()
                )

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

    def test_mark_resume_import_parsed_stores_preview_without_updating_profile(self):
        resume_import = services.create_resume_import(self.profile, self._file())

        services.mark_resume_import_parsed(
            resume_import,
            {"full_name": "Parsed User", "skills": ["Python"]},
        )

        self.assertEqual(resume_import.parse_status, ResumeImport.ParseStatus.SUCCESS)
        self.assertEqual(
            resume_import.parsed_data,
            {"full_name": "Parsed User", "skills": ["Python"]},
        )
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.full_name, "Resume User")
        self.assertFalse(CandidateSkill.objects.filter(candidate=self.profile).exists())
        self.assertEqual(self.profile.profile_version, 1)

    def test_full_profile_save_replaces_snapshot_and_enqueues_once(self):
        skill = Skill.objects.create(name="Python", slug="save-python")
        with patch("apps.candidates.services.publish_task"):
            resume_import = services.create_resume_import(self.profile, self._file())
        services.mark_resume_import_parsed(
            resume_import,
            {"headline": "Preview"},
            {"headline": "Preview"},
        )

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
        with patch("apps.candidates.services.publish_task"):
            resume_import = services.create_resume_import(self.profile, self._file())
        services.mark_resume_import_parsed(resume_import, {}, {})
        resume = services.consume_resume_import(resume_import)
        stored_name = resume.file.name

        services.delete_resume_import(resume_import)

        self.assertFalse(ResumeImport.objects.filter(pk=resume_import.pk).exists())
        self.assertTrue(resume.file.storage.exists(stored_name))

    def test_cancelled_import_delete_removes_file(self):
        with patch("apps.candidates.services.publish_task"):
            resume_import = services.create_resume_import(self.profile, self._file())
        stored_name = resume_import.file.name

        with self.captureOnCommitCallbacks(execute=True):
            services.delete_resume_import(resume_import)

        self.assertFalse(resume_import.file.storage.exists(stored_name))
