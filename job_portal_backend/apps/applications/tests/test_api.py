import tempfile
from datetime import timedelta
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.applications.models import JobApplication
from apps.ai_analysis.models import ApplicationMatchResult
from apps.candidates.models import CandidateProfile, Resume
from apps.companies.models import Company
from apps.jobs.models import JobPost
from apps.skills.models import CandidateSkill, Skill


class ApplicationApiTests(APITestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.override = override_settings(MEDIA_ROOT=Path(self.temp_dir.name))
        self.override.enable()
        self.addCleanup(self.override.disable)

        self.employer = User.objects.create_user(
            username="api-application-employer",
            email="api-application-employer@example.com",
            password="password123",
            role=User.Role.EMPLOYER,
        )
        self.company = Company.objects.create(
            owner=self.employer,
            name="API Application Company",
            status=Company.Status.APPROVED,
        )
        self.job = JobPost.objects.create(
            company=self.company,
            created_by=self.employer,
            title="Django Developer",
            description="Build APIs",
            status=JobPost.Status.ACTIVE,
            expires_at=timezone.now() + timedelta(days=30),
        )
        self.candidate = User.objects.create_user(
            username="api-application-candidate",
            email="api-application-candidate@example.com",
            password="password123",
            role=User.Role.CANDIDATE,
        )
        self.profile = CandidateProfile.objects.create(
            user=self.candidate,
            full_name="API Candidate",
            phone="0901234567",
            desired_position="Django Developer",
        )
        self.resume = Resume.objects.create(
            candidate=self.profile,
            file=SimpleUploadedFile("cv.pdf", b"%PDF-1.4 test"),
            original_filename="cv.pdf",
            is_primary=True,
        )
        self.skill = Skill.objects.create(
            name="Django",
            slug="api-application-django",
            status=Skill.Status.APPROVED,
        )
        CandidateSkill.objects.create(candidate=self.profile, skill=self.skill)

    def test_candidate_can_apply_and_list_own_applications(self):
        self.client.force_authenticate(self.candidate)

        create_response = self.client.post(
            reverse("applications-list"),
            {
                "job": str(self.job.id),
                "cover_letter": "Please consider me",
                "attach_current_resume": True,
            },
            format="json",
        )
        list_response = self.client.get(reverse("applications-list"))

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(create_response.data["status"], JobApplication.Status.APPLIED)
        self.assertNotIn("match_score", create_response.data)
        self.assertEqual(create_response.data["submitted_resume"]["id"], str(self.resume.id))
        self.assertNotIn("file_url", create_response.data["submitted_resume"])
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data["count"], 1)

    def test_candidate_can_apply_without_a_resume(self):
        self.resume.delete()
        self.client.force_authenticate(self.candidate)

        response = self.client.post(
            reverse("applications-list"),
            {
                "job": str(self.job.id),
                "attach_current_resume": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data["submitted_resume"])

    def test_employer_cannot_apply(self):
        self.client.force_authenticate(self.employer)

        response = self.client.post(
            reverse("applications-list"),
            {"job": str(self.job.id)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_employer_can_transition_owned_application(self):
        self.client.force_authenticate(self.candidate)
        created = self.client.post(
            reverse("applications-list"),
            {"job": str(self.job.id)},
            format="json",
        )
        self.client.force_authenticate(self.employer)

        response = self.client.post(
            reverse("applications-transition", args=[created.data["id"]]),
            {
                "status": JobApplication.Status.SHORTLISTED,
                "expected_status": JobApplication.Status.APPLIED,
                "note": "Good profile",
                "candidate_message": "Bạn đã vượt qua vòng xem xét.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], JobApplication.Status.SHORTLISTED)
        self.assertIsNone(response.data["match_score"])
        self.assertEqual(len(response.data["history"]), 2)
        latest = response.data["history"][0]
        self.assertEqual(latest["note"], "Good profile")
        self.assertEqual(
            latest["candidate_message"],
            "Bạn đã vượt qua vòng xem xét.",
        )
        self.assertEqual(latest["notification_status"], "PENDING")

        self.client.force_authenticate(self.candidate)
        candidate_response = self.client.get(
            reverse("applications-detail", args=[created.data["id"]])
        )
        candidate_history = candidate_response.data["history"][0]
        self.assertNotIn("note", candidate_history)
        self.assertNotIn("changed_by_email", candidate_history)
        self.assertEqual(
            candidate_history["candidate_message"],
            "Bạn đã vượt qua vòng xem xét.",
        )

    def test_candidate_cannot_transition_application(self):
        application = JobApplication.objects.create(
            job=self.job,
            candidate=self.profile,
            resume=self.resume,
        )
        self.client.force_authenticate(self.candidate)

        response = self.client.post(
            reverse("applications-transition", args=[application.id]),
            {"status": JobApplication.Status.SHORTLISTED},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_cannot_transition_application(self):
        application = JobApplication.objects.create(
            job=self.job,
            candidate=self.profile,
            resume=self.resume,
        )
        admin = User.objects.create_user(
            username="transition-admin",
            email="transition-admin@example.com",
            password="password123",
            role=User.Role.ADMIN,
        )
        self.client.force_authenticate(admin)

        response = self.client.post(
            reverse("applications-transition", args=[application.id]),
            {
                "status": JobApplication.Status.SHORTLISTED,
                "expected_status": JobApplication.Status.APPLIED,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_other_employer_cannot_view_application(self):
        application = JobApplication.objects.create(
            job=self.job,
            candidate=self.profile,
            resume=self.resume,
        )
        other = User.objects.create_user(
            username="other-application-employer",
            email="other-application-employer@example.com",
            password="password123",
            role=User.Role.EMPLOYER,
        )
        Company.objects.create(
            owner=other,
            name="Other Application Company",
            status=Company.Status.APPROVED,
        )
        self.client.force_authenticate(other)

        response = self.client.get(
            reverse("applications-detail", args=[application.id])
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_submitted_resume_cannot_be_deleted(self):
        JobApplication.objects.create(
            job=self.job,
            candidate=self.profile,
            resume=self.resume,
        )
        self.client.force_authenticate(self.candidate)

        response = self.client.delete(
            reverse("candidate-resume-detail", args=[self.resume.id])
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(Resume.objects.filter(pk=self.resume.pk).exists())

    def test_application_resume_download_url_respects_application_scope(self):
        application = JobApplication.objects.create(
            job=self.job,
            candidate=self.profile,
            resume=self.resume,
        )
        url = reverse("applications-resume-download-url", args=[application.id])

        self.client.force_authenticate(self.candidate)
        candidate_response = self.client.get(url)
        self.assertEqual(candidate_response.status_code, status.HTTP_200_OK)
        self.assertTrue(candidate_response.data["url"].startswith("http://testserver/media/"))

        self.client.force_authenticate(self.employer)
        self.assertEqual(self.client.get(url).status_code, status.HTTP_200_OK)

        admin = User.objects.create_user(
            username="resume-download-admin",
            email="resume-download-admin@example.com",
            password="password123",
            role=User.Role.ADMIN,
        )
        self.client.force_authenticate(admin)
        self.assertEqual(self.client.get(url).status_code, status.HTTP_200_OK)

        other = User.objects.create_user(
            username="resume-download-other-employer",
            email="resume-download-other@example.com",
            password="password123",
            role=User.Role.EMPLOYER,
        )
        Company.objects.create(
            owner=other,
            name="Resume Download Other",
            status=Company.Status.APPROVED,
        )
        self.client.force_authenticate(other)
        self.assertEqual(self.client.get(url).status_code, status.HTTP_404_NOT_FOUND)

    def test_owner_can_get_empty_match_result_shape(self):
        application = JobApplication.objects.create(
            job=self.job,
            candidate=self.profile,
            resume=self.resume,
        )
        self.client.force_authenticate(self.employer)

        response = self.client.get(
            reverse("applications-match-result", args=[application.id])
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(set(response.data), {
            "match_score", "status", "semantic_similarity_score", "skill_overlap_score",
            "experience_score", "education_score",
            "matched_skills", "missing_skills",
            "criteria_applicability", "original_weights", "normalized_weights",
            "missing_information", "rule_version", "embedding_metadata",
            "weight_config_id", "weight_config_name",
            "embedding_model_version",
            "created_at",
            "snapshot_created_at",
        })
        self.assertIsNone(response.data["match_score"])
        self.assertEqual(response.data["matched_skills"], [])

    def test_owner_and_admin_get_match_result_but_others_do_not(self):
        application = JobApplication.objects.create(
            job=self.job,
            candidate=self.profile,
            resume=self.resume,
        )
        ApplicationMatchResult.objects.create(
            application=application,
            match_score="82.50",
            matched_skills=["Django"],
            missing_skills=["PostgreSQL"],
            embedding_model_version="test-model",
        )
        url = reverse("applications-match-result", args=[application.id])

        self.client.force_authenticate(self.employer)
        owner_response = self.client.get(url)
        self.assertEqual(owner_response.status_code, status.HTTP_200_OK)
        self.assertEqual(owner_response.data["match_score"], "82.50")
        self.assertEqual(owner_response.data["matched_skills"], ["Django"])
        self.assertIn("snapshot_created_at", owner_response.data)

        self.client.force_authenticate(self.candidate)
        self.assertEqual(self.client.get(url).status_code, status.HTTP_403_FORBIDDEN)
        other = User.objects.create_user(
            username="analysis-other-employer",
            email="analysis-other@example.com",
            password="password123",
            role=User.Role.EMPLOYER,
        )
        Company.objects.create(owner=other, name="Analysis Other", status=Company.Status.APPROVED)
        self.client.force_authenticate(other)
        self.assertEqual(self.client.get(url).status_code, status.HTTP_404_NOT_FOUND)
        admin = User.objects.create_user(
            username="analysis-admin",
            email="analysis-admin@example.com",
            password="password123",
            role=User.Role.ADMIN,
        )
        self.client.force_authenticate(admin)
        self.assertEqual(self.client.get(url).data["match_score"], "82.50")
