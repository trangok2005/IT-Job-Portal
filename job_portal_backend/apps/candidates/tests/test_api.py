import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import patch

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.candidates.models import (
    CandidateProfile,
    Education,
    Resume,
    ResumeImport,
)
from apps.candidates.tasks import parse_resume_import
from apps.skills.models import Skill, SkillAlias
from integrations.gemini.structured_output import ParsedDocumentResult


class CandidateApiTests(APITestCase):
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
        self.employer = User.objects.create_user(
            username="employer-candidate-test",
            email="employer-candidate@example.com",
            password="password123",
            role=User.Role.EMPLOYER,
        )

    def test_candidate_can_update_own_profile(self):
        self.client.force_authenticate(self.user)

        response = self.client.patch(
            reverse("candidate-me"),
            {"desired_position": "Backend Developer"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.desired_position, "Backend Developer")
        self.assertEqual(self.profile.profile_version, 2)
        self.assertEqual(response.data["embedding_version"], 0)
        self.assertTrue(response.data["embedding_is_stale"])
        self.assertIsNone(response.data["embedding_updated_at"])

    def test_candidate_can_save_one_reviewed_profile_snapshot(self):
        skill = Skill.objects.create(name="Python", slug="api-save-python")
        self.client.force_authenticate(self.user)

        response = self.client.put(
            reverse("candidate-me"),
            {
                "full_name": "Reviewed Candidate",
                "phone": "0901234567",
                "dob": None,
                "gender": "",
                "address": "Hà Nội",
                "avatar_url": "",
                "headline": "Backend Developer",
                "summary": "Python APIs",
                "desired_position": "Backend Developer",
                "is_public": True,
                "educations": [{"school_name": "HUST", "major": "IT"}],
                "experiences": [{
                    "company_name": "Tech",
                    "position": "Developer",
                    "is_current": True,
                }],
                "skills": [
                    {"skill": str(skill.id), "years_of_experience": 3}
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.profile_version, 2)
        self.assertEqual(self.profile.full_name, "Reviewed Candidate")
        self.assertEqual(self.profile.educations.count(), 1)
        self.assertEqual(self.profile.experiences.count(), 1)
        self.assertEqual(self.profile.candidate_skills.count(), 1)
        self.assertEqual(
            self.profile.candidate_skills.get().years_of_experience,
            3,
        )

    def test_save_profile_normalizes_new_skill_name(self):
        self.client.force_authenticate(self.user)

        response = self.client.put(
            reverse("candidate-me"),
            {
                "full_name": "Skill Normalizer",
                "phone": "",
                "dob": None,
                "gender": "",
                "address": "",
                "avatar_url": "",
                "headline": "",
                "summary": "",
                "desired_position": "",
                "is_public": True,
                "educations": [],
                "experiences": [],
                "skills": [{"skill": "  Python  "}],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.profile.refresh_from_db()
        candidate_skill = self.profile.candidate_skills.get()
        skill = candidate_skill.skill
        self.assertEqual(skill.name, "Python")

    def test_save_profile_dedupes_skills_resolving_to_same_skill(self):
        self.client.force_authenticate(self.user)
        python = Skill.objects.create(
            name="Python",
            slug="dedupe-python",
            status=Skill.Status.APPROVED,
            is_active=True,
        )
        SkillAlias.objects.create(
            skill=python,
            alias_text="Python Developer",
            normalized_text="python developer",
        )

        response = self.client.put(
            reverse("candidate-me"),
            {
                "full_name": "Dedupe Candidate",
                "phone": "",
                "dob": None,
                "gender": "",
                "address": "",
                "avatar_url": "",
                "headline": "",
                "summary": "",
                "desired_position": "",
                "is_public": True,
                "educations": [],
                "experiences": [],
                "skills": [
                    {"skill": str(python.id)},
                    {"skill": "Python Developer"},
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.candidate_skills.count(), 1)
        self.assertEqual(self.profile.candidate_skills.get().skill, python)

    def test_save_profile_allows_pending_skill_until_admin_reviews(self):
        self.client.force_authenticate(self.user)
        pending = Skill.objects.create(
            name="Rust",
            slug="pending-rust",
            status=Skill.Status.PENDING,
        )

        response = self.client.put(
            reverse("candidate-me"),
            {
                "full_name": "Pending Skill Candidate",
                "phone": "",
                "dob": None,
                "gender": "",
                "address": "",
                "avatar_url": "",
                "headline": "",
                "summary": "",
                "desired_position": "",
                "is_public": True,
                "educations": [],
                "experiences": [],
                "skills": [{"skill": str(pending.id)}],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.profile.refresh_from_db()
        candidate_skill = self.profile.candidate_skills.get()
        self.assertEqual(candidate_skill.skill, pending)
        self.assertEqual(candidate_skill.skill.status, Skill.Status.PENDING)

    def test_employer_cannot_manage_candidate_profile(self):
        self.client.force_authenticate(self.employer)

        response = self.client.get(reverse("candidate-me"))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_candidate_cannot_update_another_candidates_education(self):
        other_user = User.objects.create_user(
            username="other-candidate",
            email="other-candidate@example.com",
            password="password123",
            role=User.Role.CANDIDATE,
        )
        other_profile = CandidateProfile.objects.create(
            user=other_user,
            full_name="Other",
        )
        education = Education.objects.create(
            candidate=other_profile,
            school_name="Other School",
        )
        self.client.force_authenticate(self.user)

        response = self.client.patch(
            reverse("candidate-education-detail", args=[education.id]),
            {"school_name": "Changed"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_education_partial_update_validates_existing_start_date(self):
        education = Education.objects.create(
            candidate=self.profile,
            school_name="HUST",
            start_date=date(2024, 1, 1),
        )
        self.client.force_authenticate(self.user)

        response = self.client.patch(
            reverse("candidate-education-detail", args=[education.id]),
            {"end_date": "2023-01-01"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class CandidateResumeApiTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.override = override_settings(MEDIA_ROOT=Path(self.temp_dir.name))
        self.override.enable()
        self.addCleanup(self.override.disable)

        self.user = User.objects.create_user(
            username="candidate-upload",
            email="candidate-upload@example.com",
            password="password123",
            role=User.Role.CANDIDATE,
        )
        self.profile = CandidateProfile.objects.create(
            user=self.user,
            full_name="Upload User",
        )
        self.client.force_authenticate(self.user)

    def test_upload_resume_import(self):
        file = SimpleUploadedFile(
            "cv.pdf",
            b"%PDF-1.4 test",
            content_type="application/pdf",
        )

        response = self.client.post(
            reverse("candidate-resume-import-create"),
            {"file": file},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        resume_import = ResumeImport.objects.get(candidate=self.profile)
        self.assertEqual(
            resume_import.parse_status, ResumeImport.ParseStatus.PENDING
        )
        self.assertIsNotNone(resume_import.expires_at)

    def test_upload_resume_import_rejects_unsupported_file(self):
        file = SimpleUploadedFile("cv.exe", b"invalid")

        response = self.client.post(
            reverse("candidate-resume-import-create"),
            {"file": file},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(
            ResumeImport.objects.filter(candidate=self.profile).exists()
        )

    @patch("apps.candidates.tasks.parse_resume_document")
    def test_only_owner_can_read_and_consume_uploaded_import(self, parse_document):
        upload = self.client.post(
            reverse("candidate-resume-import-create"),
            {"file": SimpleUploadedFile("cv.pdf", b"%PDF-1.4")},
            format="multipart",
        )
        self.assertEqual(upload.status_code, status.HTTP_201_CREATED)
        parse_document.assert_not_called()
        import_id = upload.data["id"]
        parse_document.return_value = ParsedDocumentResult(
            raw_data={"full_name": "Reviewed"},
            validated_data={"full_name": "Reviewed"},
        )
        parse_resume_import(import_id)
        detail_url = reverse("candidate-resume-import-detail", args=[import_id])
        payload = {
            "full_name": "Reviewed",
            "educations": [],
            "experiences": [],
            "skills": [],
            "resume_import_id": import_id,
        }
        other_user = User.objects.create_user(
            username="import-other", email="import-other@example.com",
            password="password123", role=User.Role.CANDIDATE,
        )
        other_profile = CandidateProfile.objects.create(user=other_user, full_name="Other")
        self.client.force_authenticate(other_user)

        self.assertEqual(self.client.get(detail_url).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.delete(detail_url).status_code, status.HTTP_404_NOT_FOUND)
        denied = self.client.put(reverse("candidate-me"), payload, format="json")
        self.assertEqual(denied.status_code, status.HTTP_400_BAD_REQUEST)
        other_profile.refresh_from_db()
        self.assertEqual(other_profile.full_name, "Other")
        self.assertEqual(other_profile.profile_version, 1)
        self.assertFalse(other_profile.resumes.exists())
        record = ResumeImport.objects.get(pk=import_id)
        self.assertEqual(record.parse_status, ResumeImport.ParseStatus.SUCCESS)

        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.get(detail_url).status_code, status.HTTP_200_OK)
        saved = self.client.put(reverse("candidate-me"), payload, format="json")
        self.assertEqual(saved.status_code, status.HTTP_200_OK)
        record.refresh_from_db()
        self.assertEqual(record.parse_status, ResumeImport.ParseStatus.CONSUMED)
        self.assertEqual(self.profile.resumes.count(), 1)
        repeated = self.client.put(reverse("candidate-me"), payload, format="json")
        self.assertEqual(repeated.status_code, status.HTTP_400_BAD_REQUEST)

    def test_owner_can_cancel_uploaded_import(self):
        upload = self.client.post(
            reverse("candidate-resume-import-create"),
            {"file": SimpleUploadedFile("cv.pdf", b"%PDF-1.4")},
            format="multipart",
        )
        self.assertEqual(upload.status_code, status.HTTP_201_CREATED)
        response = self.client.delete(
            reverse("candidate-resume-import-detail", args=[upload.data["id"]])
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ResumeImport.objects.filter(pk=upload.data["id"]).exists())

    def test_upload_resume_import_throttled_after_two_per_minute(self):
        for i in range(2):
            file = SimpleUploadedFile(
                f"cv{i}.pdf",
                b"%PDF-1.4 test",
                content_type="application/pdf",
            )
            response = self.client.post(
                reverse("candidate-resume-import-create"),
                {"file": file},
                format="multipart",
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        third = SimpleUploadedFile(
            "cv3.pdf",
            b"%PDF-1.4 test",
            content_type="application/pdf",
        )
        response = self.client.post(
            reverse("candidate-resume-import-create"),
            {"file": third},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_candidate_can_get_own_resume_download_url(self):
        resume = Resume.objects.create(
            candidate=self.profile,
            file=SimpleUploadedFile("private-cv.pdf", b"%PDF-1.4 test"),
            original_filename="private-cv.pdf",
        )

        response = self.client.get(
            reverse("candidate-resume-download-url", args=[resume.id])
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["url"].startswith("http://testserver/media/"))
        self.assertIn("expires_at", response.data)

    def test_candidate_cannot_get_another_candidates_resume_download_url(self):
        other_user = User.objects.create_user(
            username="other-resume-candidate",
            email="other-resume-candidate@example.com",
            password="password123",
            role=User.Role.CANDIDATE,
        )
        other_profile = CandidateProfile.objects.create(
            user=other_user,
            full_name="Other Resume Candidate",
        )
        resume = Resume.objects.create(
            candidate=other_profile,
            file=SimpleUploadedFile("other.pdf", b"%PDF-1.4 test"),
            original_filename="other.pdf",
        )

        response = self.client.get(
            reverse("candidate-resume-download-url", args=[resume.id])
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
