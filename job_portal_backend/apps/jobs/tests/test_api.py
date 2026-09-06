from datetime import timedelta
from unittest.mock import patch

from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.candidates.models import CandidateProfile
from apps.companies.models import Company
from integrations.gemini.embeddings import (
    current_candidate_embedding_signature,
    current_job_embedding_signature,
)
from apps.jobs.models import JDImport, JobPost, JobSkill
from apps.jobs.tasks import parse_jd_import
from apps.applications.models import JobApplication
from apps.skills.models import CandidateSkill, Skill
from django.core.cache import cache
from integrations.gemini.embeddings import EmbeddingError


class JobApiTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.employer = User.objects.create_user(
            username="api-employer",
            email="api-employer@example.com",
            password="password123",
            role=User.Role.EMPLOYER,
        )
        self.company = Company.objects.create(
            owner=self.employer,
            name="API Company",
            status=Company.Status.APPROVED,
        )
        self.candidate = User.objects.create_user(
            username="api-candidate",
            email="api-candidate@example.com",
            password="password123",
            role=User.Role.CANDIDATE,
        )
        CandidateProfile.objects.create(user=self.candidate, full_name="Candidate")
        self.skill = Skill.objects.create(name="Django", slug="django")

    def _job(self, **overrides):
        data = {
            "company": self.company,
            "created_by": self.employer,
            "title": "Django Developer",
            "description": "Build Django APIs",
            "status": JobPost.Status.ACTIVE,
            "expires_at": timezone.now() + timedelta(days=30),
        }
        data.update(overrides)
        if data.get("embedding") is not None:
            data.setdefault("embedding_signature", current_job_embedding_signature())
        return JobPost.objects.create(**data)

    def test_public_list_hides_draft_and_expired_jobs(self):
        active = self._job()
        self._job(title="Draft", status=JobPost.Status.DRAFT)
        self._job(
            title="Expired",
            expires_at=timezone.now() - timedelta(minutes=1),
        )

        response = self.client.get(reverse("jobs-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], str(active.id))
        self.assertIsNone(response.data["results"][0]["match_score"])
        self.assertEqual(response["X-Search-Mode"], "LATEST")

    @patch("apps.jobs.job_search_service.embed_query")
    def test_keyword_search_ranks_current_embeddings_by_cosine(self, embed_query):
        embed_query.return_value = [1.0] + [0.0] * 767
        second = self._job(
            title="Java role",
            embedding=[0.5, 0.5] + [0.0] * 766,
            embedding_version=1,
        )
        best = self._job(
            title="Unrelated lexical title",
            embedding=[1.0] + [0.0] * 767,
            embedding_version=1,
        )
        self._job(
            title="Python but stale",
            embedding=[1.0] + [0.0] * 767,
            embedding_version=0,
        )

        response = self.client.get(
            reverse("jobs-list"),
            {"keyword": "Python", "ordering": "-created_at"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item["id"] for item in response.data["results"]],
            [str(best.id), str(second.id)],
        )
        self.assertAlmostEqual(response.data["results"][0]["match_score"], 100.0)
        embed_query.assert_called_once_with("Desired job: Python")
        self.assertEqual(response["X-Search-Mode"], "SEMANTIC")
        self.assertFalse(response.data["search_fallback"])

    @patch("apps.jobs.job_search_service.embed_query")
    def test_explicit_python_developer_intent_excludes_java(self, embed_query):
        embed_query.return_value = [1.0] + [0.0] * 767
        python = Skill.objects.create(name="Python", slug="python")
        java = Skill.objects.create(name="Java", slug="java")
        python_job = self._job(
            title="Python Developer",
            embedding=[0.8, 0.2] + [0.0] * 766,
            embedding_version=1,
        )
        java_job = self._job(
            title="Java Developer",
            embedding=[1.0] + [0.0] * 767,
            embedding_version=1,
        )
        JobSkill.objects.create(job=python_job, skill=python, is_required=True)
        JobSkill.objects.create(job=java_job, skill=java, is_required=True)

        response = self.client.get(
            reverse("jobs-list"),
            {"keyword": "dev python"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], str(python_job.id))
        self.assertEqual(response["X-Search-Mode"], "SEMANTIC")

    @patch("apps.jobs.job_search_service.embed_query")
    def test_keyword_search_returns_only_scores_strictly_above_fifty(self, embed_query):
        embed_query.return_value = [1.0] + [0.0] * 767
        above = self._job(
            title="Above threshold",
            embedding=[0.6, 0.8] + [0.0] * 766,
            embedding_version=1,
        )
        self._job(
            title="Exactly threshold",
            embedding=[0.5, 0.8660254037844386] + [0.0] * 766,
            embedding_version=1,
        )
        self._job(
            title="Below threshold",
            embedding=[0.0, 1.0] + [0.0] * 766,
            embedding_version=1,
        )

        response = self.client.get(reverse("jobs-list"), {"keyword": "Django"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], str(above.id))
        self.assertAlmostEqual(
            response.data["results"][0]["match_score"], 60.0, delta=0.001
        )
        self.assertEqual(response["X-Search-Mode"], "SEMANTIC")
        self.assertFalse(response.data["search_fallback"])

    @patch("apps.jobs.job_search_service.embed_query")
    def test_keyword_search_does_not_fallback_when_current_scores_are_too_low(self, embed_query):
        embed_query.return_value = [1.0] + [0.0] * 767
        self._job(
            title="Django lexical match",
            embedding=[0.0, 1.0] + [0.0] * 766,
            embedding_version=1,
        )

        response = self.client.get(reverse("jobs-list"), {"keyword": "Django"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response["X-Search-Mode"], "SEMANTIC")
        self.assertFalse(response.data["search_fallback"])

    @patch(
        "apps.jobs.job_search_service.embed_query",
        side_effect=EmbeddingError("timeout"),
    )
    def test_keyword_search_falls_back_after_hard_filters(self, embed_query):
        expected = self._job(title="Python Developer", location="Hà Nội")
        self._job(title="Python Developer Remote", location="Đà Nẵng")
        self._job(title="Java Developer", location="Hà Nội")

        response = self.client.get(
            reverse("jobs-list"),
            {"keyword": "Python", "location": "Hà Nội"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], str(expected.id))
        self.assertIsNone(response.data["results"][0]["match_score"])
        embed_query.assert_called_once_with("Desired job: Python")
        self.assertEqual(response["X-Search-Mode"], "FALLBACK_BASIC")
        self.assertEqual(response["X-Search-Fallback"], "true")
        self.assertTrue(response.data["search_fallback"])

    @patch("apps.jobs.job_search_service.embed_query")
    def test_keyword_search_uses_basic_search_when_job_embeddings_are_unavailable(self, embed_query):
        embed_query.return_value = [1.0] + [0.0] * 767
        expected = self._job(requirements="Python PostgreSQL")

        response = self.client.get(reverse("jobs-list"), {"keyword": "Python"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["id"], str(expected.id))
        self.assertEqual(response["X-Search-Mode"], "FALLBACK_BASIC")
        self.assertTrue(response.data["search_fallback"])

    @patch(
        "apps.jobs.job_search_service.embed_query",
        side_effect=EmbeddingError("timeout"),
    )
    def test_fallback_expands_dev_shorthand_without_returning_java(self, embed_query):
        expected = self._job(title="Python Developer", requirements="Python Django")
        self._job(title="Java Developer", requirements="Java Spring Boot")

        response = self.client.get(
            reverse("jobs-list"),
            {"keyword": "dev python"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], str(expected.id))
        self.assertEqual(response["X-Search-Mode"], "FALLBACK_BASIC")

    def test_authenticated_search_throttled_after_ten_requests_per_minute(self):
        self.client.force_authenticate(user=self.candidate)
        self._job()

        for _ in range(10):
            response = self.client.get(reverse("jobs-list"), {"keyword": "Django"})
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(reverse("jobs-list"), {"keyword": "Django"})

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    @patch("apps.jobs.jd_parser.parse_job_description")
    def test_parse_jd_throttled_after_two_uploads_per_minute(self, parse_jd):
        parse_jd.return_value = (
            {"title": "Python Developer", "skills": []},
            {"title": "Python Developer"},
        )
        self.client.force_authenticate(user=self.employer)

        first = self.client.post(
            reverse("jobs-parse-jd"),
            {"file": SimpleUploadedFile("jd1.pdf", b"%PDF-1.4")},
            format="multipart",
        )
        second = self.client.post(
            reverse("jobs-parse-jd"),
            {"file": SimpleUploadedFile("jd2.pdf", b"%PDF-1.4")},
            format="multipart",
        )
        third = self.client.post(
            reverse("jobs-parse-jd"),
            {"file": SimpleUploadedFile("jd3.pdf", b"%PDF-1.4")},
            format="multipart",
        )

        self.assertEqual(first.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(second.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(third.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_anon_search_throttled_after_five_requests_per_minute(self):
        self._job()

        for _ in range(5):
            response = self.client.get(reverse("jobs-list"), {"keyword": "Django"})
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(reverse("jobs-list"), {"keyword": "Django"})

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_authenticated_candidate_search_not_throttled(self):
        self.client.force_authenticate(user=self.candidate)
        self._job()

        for _ in range(7):
            response = self.client.get(reverse("jobs-list"), {"keyword": "Django"})
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("apps.jobs.job_search_service.embed_query")
    def test_filter_only_search_skips_gemini(self, embed_query):
        self._job(location="Hà Nội")

        response = self.client.get(reverse("jobs-list"), {"location": "Hà Nội"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        embed_query.assert_not_called()
        self.assertEqual(response["X-Search-Mode"], "FILTER_ONLY")

    def test_five_hard_filters_can_be_combined(self):
        expected = self._job(
            workplace_type=JobPost.WorkplaceType.HYBRID,
            job_type=JobPost.JobType.CONTRACT,
            experience_level=JobPost.ExperienceLevel.MID_SENIOR,
            salary_max=40_000_000,
            location=JobPost.Location.HO_CHI_MINH,
        )
        self._job(title="Wrong workplace", workplace_type=JobPost.WorkplaceType.ONSITE)
        self._job(title="Wrong type", workplace_type=JobPost.WorkplaceType.HYBRID)
        self._job(
            title="Wrong experience",
            workplace_type=JobPost.WorkplaceType.HYBRID,
            job_type=JobPost.JobType.CONTRACT,
            experience_level=JobPost.ExperienceLevel.JUNIOR,
        )
        self._job(
            title="Wrong salary",
            workplace_type=JobPost.WorkplaceType.HYBRID,
            job_type=JobPost.JobType.CONTRACT,
            experience_level=JobPost.ExperienceLevel.MID_SENIOR,
            salary_max=20_000_000,
            location=JobPost.Location.HO_CHI_MINH,
        )

        response = self.client.get(reverse("jobs-list"), {
            "workplace_type": JobPost.WorkplaceType.HYBRID,
            "job_type": JobPost.JobType.CONTRACT,
            "experience_level": JobPost.ExperienceLevel.MID_SENIOR,
            "salary_min": 30_000_000,
            "location": JobPost.Location.HO_CHI_MINH,
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], str(expected.id))

    def test_recommended_jobs_rank_current_embeddings_and_exclude_ineligible(self):
        profile = self.candidate.candidate_profile
        profile.embedding = [1.0] + [0.0] * 767
        profile.embedding_version = profile.profile_version
        profile.embedding_signature = current_candidate_embedding_signature()
        profile.save(update_fields=["embedding", "embedding_version", "embedding_signature"])
        best = self._job(
            title="Best",
            embedding=[1.0] + [0.0] * 767,
            embedding_version=1,
        )
        second = self._job(
            title="Second",
            embedding=[0.5, 0.5] + [0.0] * 766,
            embedding_version=1,
        )
        missing = self._job(title="Missing")
        stale = self._job(
            title="Stale",
            embedding=[1.0] + [0.0] * 767,
            content_version=2,
            embedding_version=1,
        )
        self._job(title="Draft", status=JobPost.Status.DRAFT)
        self._job(title="Expired", expires_at=timezone.now() - timedelta(seconds=1))
        pending_employer = User.objects.create_user(
            username="pending-company-employer",
            email="pending-company-employer@example.com",
            password="password123",
            role=User.Role.EMPLOYER,
        )
        pending_company = Company.objects.create(
            owner=pending_employer,
            name="Pending Company",
            status=Company.Status.PENDING,
        )
        self._job(
            title="Pending company",
            company=pending_company,
            created_by=pending_employer,
        )
        self.client.force_authenticate(self.candidate)

        response = self.client.get(reverse("jobs-recommended"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        self.assertEqual([item["id"] for item in results[:2]], [str(best.id), str(second.id)])
        self.assertEqual({item["id"] for item in results}, {
            str(best.id), str(second.id), str(missing.id), str(stale.id)
        })
        scores = {item["id"]: item["match_score"] for item in results}
        self.assertIsNone(scores[str(missing.id)])
        self.assertIsNone(scores[str(stale.id)])

    @patch("apps.jobs.services.enqueue_candidate_embedding_robust")
    def test_recommended_jobs_with_missing_embedding_enqueue_and_return_newest_null(
        self, enqueue
    ):
        older = self._job(title="Older")
        newer = self._job(title="Newer")
        JobPost.objects.filter(pk=older.pk).update(
            created_at=timezone.now() - timedelta(minutes=1)
        )
        self.client.force_authenticate(self.candidate)

        response = self.client.get(reverse("jobs-recommended"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item["id"] for item in response.data["results"]],
            [str(newer.id), str(older.id)],
        )
        self.assertTrue(all(item["match_score"] is None for item in response.data["results"]))
        enqueue.assert_called_once_with(self.candidate.candidate_profile)

    def test_only_candidate_can_get_recommended_jobs(self):
        self.assertEqual(
            self.client.get(reverse("jobs-recommended")).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.client.force_authenticate(self.employer)
        self.assertEqual(
            self.client.get(reverse("jobs-recommended")).status_code,
            status.HTTP_403_FORBIDDEN,
        )

    @patch("apps.jobs.services.enqueue_job_embedding_robust")
    def test_owner_gets_safe_recommended_candidates_and_missing_job_enqueues(self, enqueue):
        job = self._job()
        skill = Skill.objects.create(name="Python", slug="python")
        CandidateSkill.objects.create(candidate=self.candidate.candidate_profile, skill=skill)
        private_user = User.objects.create_user(
            username="private-candidate",
            email="private-candidate@example.com",
            password="password123",
            role=User.Role.CANDIDATE,
        )
        CandidateProfile.objects.create(
            user=private_user,
            full_name="Private",
            is_public=False,
        )
        self.client.force_authenticate(self.employer)

        response = self.client.get(reverse("jobs-recommended-candidates", args=[job.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        summary = response.data["results"][0]
        self.assertEqual(summary["skills"], ["Python"])
        self.assertIsNone(summary["match_score"])
        self.assertNotIn("email", summary)
        self.assertNotIn("phone", summary)
        enqueue.assert_called_once_with(job)

    def test_recommended_candidates_permissions_for_owner_other_owner_and_admin(self):
        job = self._job(embedding=[1.0] + [0.0] * 767, embedding_version=1)
        profile = self.candidate.candidate_profile
        profile.embedding = [1.0] + [0.0] * 767
        profile.embedding_version = profile.profile_version
        profile.embedding_signature = current_candidate_embedding_signature()
        profile.save(update_fields=["embedding", "embedding_version", "embedding_signature"])
        other = User.objects.create_user(
            username="recommendation-other-employer",
            email="recommendation-other@example.com",
            password="password123",
            role=User.Role.EMPLOYER,
        )
        Company.objects.create(owner=other, name="Other", status=Company.Status.APPROVED)
        admin = User.objects.create_user(
            username="recommendation-admin",
            email="recommendation-admin@example.com",
            password="password123",
            role=User.Role.ADMIN,
        )
        url = reverse("jobs-recommended-candidates", args=[job.id])

        self.client.force_authenticate(other)
        self.assertEqual(self.client.get(url).status_code, status.HTTP_404_NOT_FOUND)
        self.client.force_authenticate(self.candidate)
        self.assertEqual(self.client.get(url).status_code, status.HTTP_403_FORBIDDEN)
        self.client.force_authenticate(admin)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertAlmostEqual(response.data["results"][0]["match_score"], 100.0)

    def test_application_count_is_only_in_my_jobs(self):
        job = self._job()
        JobApplication.objects.create(job=job, candidate=self.candidate.candidate_profile)
        self.client.force_authenticate(self.employer)

        detail = self.client.get(reverse("jobs-detail", args=[job.id]))
        mine = self.client.get(reverse("jobs-my-jobs"))

        self.assertNotIn("application_count", detail.data)
        self.assertEqual(mine.data["results"][0]["application_count"], 1)

    def test_public_cannot_retrieve_draft_but_owner_can(self):
        draft = self._job(status=JobPost.Status.DRAFT)

        public_response = self.client.get(reverse("jobs-detail", args=[draft.id]))
        self.client.force_authenticate(self.employer)
        owner_response = self.client.get(reverse("jobs-detail", args=[draft.id]))

        self.assertEqual(public_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(owner_response.status_code, status.HTTP_200_OK)

    def test_approved_employer_can_create_draft(self):
        self.client.force_authenticate(self.employer)

        response = self.client.post(
            reverse("jobs-list"),
            {
                "title": "Python Developer",
                "description": "Build APIs",
                "required_skills": [{"skill": str(self.skill.id)}],
                "expires_at": (timezone.now() + timedelta(days=10)).isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], JobPost.Status.DRAFT)
        self.assertEqual(response.data["company_name"], self.company.name)
        self.assertEqual(len(response.data["skills"]), 1)

    def test_create_job_accepts_pending_optional_skill(self):
        pending = Skill.objects.create(
            name="PostgresX", slug="job-postgresx", status=Skill.Status.PENDING
        )
        self.client.force_authenticate(self.employer)

        response = self.client.post(
            reverse("jobs-list"),
            {
                "title": "Python Developer",
                "description": "Build APIs",
                "required_skills": [
                    {"skill": str(self.skill.id)},
                    {"skill": str(pending.id), "is_required": False},
                ],
                "expires_at": (timezone.now() + timedelta(days=10)).isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        job_skill_by_name = {
            item["skill_name"]: item for item in response.data["skills"]
        }
        self.assertTrue(job_skill_by_name[self.skill.name]["is_required"])
        self.assertFalse(job_skill_by_name[pending.name]["is_required"])

    def test_create_job_with_raw_unknown_skill_creates_pending(self):
        self.client.force_authenticate(self.employer)

        response = self.client.post(
            reverse("jobs-list"),
            {
                "title": "Python Developer",
                "description": "Build APIs",
                "required_skills": [
                    {"skill": str(self.skill.id)},
                    {"skill": "Thần chú AI Cấp 9"},
                ],
                "expires_at": (timezone.now() + timedelta(days=10)).isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        pending = Skill.objects.get(name="Thần chú AI Cấp 9")
        self.assertEqual(pending.status, Skill.Status.PENDING)
        job_skill_names = {item["skill_name"] for item in response.data["skills"]}
        self.assertIn(pending.name, job_skill_names)

    @patch("apps.jobs.services._enqueue_embedding")
    def test_approved_employer_can_publish_immediately(self, enqueue_embedding):
        self.client.force_authenticate(self.employer)

        response = self.client.post(
            reverse("jobs-list"),
            {
                "title": "Python Developer",
                "description": "Build APIs",
                "required_skills": [{"skill": str(self.skill.id)}],
                "expires_at": (timezone.now() + timedelta(days=10)).isoformat(),
                "publish_immediately": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], JobPost.Status.ACTIVE)
        self.assertIsNotNone(response.data["published_at"])
        enqueue_embedding.assert_called_once()

    @patch("apps.jobs.jd_parser.parse_job_description")
    def test_approved_employer_can_parse_jd_without_creating_draft(self, parse_jd):
        parse_jd.return_value = (
            {"title": "Python Developer", "skills": ["Django"]},
            {
                "title": "Python Developer",
                "description": "Build APIs",
                "job_type": JobPost.JobType.FULL_TIME,
                "experience_level": JobPost.ExperienceLevel.JUNIOR,
                "salary_negotiable": True,
                "required_skills": [str(self.skill.id)],
                "unmatched_skills": [],
            },
        )
        self.client.force_authenticate(self.employer)

        response = self.client.post(
            reverse("jobs-parse-jd"),
            {"file": SimpleUploadedFile("job.pdf", b"%PDF-1.4")},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertTrue(parse_jd_import(response.data["id"]))
        status_response = self.client.get(
            reverse("jobs-jd-import", args=[response.data["id"]])
        )
        self.assertEqual(status_response.status_code, status.HTTP_200_OK)
        self.assertEqual(status_response.data["status"], JDImport.Status.SUCCESS)
        self.assertEqual(
            status_response.data["parsed_data"]["title"], "Python Developer"
        )
        self.assertEqual(
            status_response.data["parsed_data"]["required_skills"],
            [str(self.skill.id)],
        )
        self.assertEqual(JobPost.objects.count(), 0)

    def test_parse_jd_rejects_invalid_file_and_candidate(self):
        self.client.force_authenticate(self.employer)
        invalid = self.client.post(
            reverse("jobs-parse-jd"),
            {"file": SimpleUploadedFile("job.txt", b"text")},
            format="multipart",
        )
        self.assertEqual(invalid.status_code, status.HTTP_400_BAD_REQUEST)

        self.client.force_authenticate(self.candidate)
        forbidden = self.client.post(
            reverse("jobs-parse-jd"),
            {"file": SimpleUploadedFile("job.pdf", b"%PDF-1.4")},
            format="multipart",
        )
        self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)

    def test_candidate_cannot_create_or_list_my_jobs(self):
        self.client.force_authenticate(self.candidate)

        create_response = self.client.post(
            reverse("jobs-list"),
            {"title": "Invalid", "description": "Invalid"},
            format="json",
        )
        my_jobs_response = self.client.get(reverse("jobs-my-jobs"))

        self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(my_jobs_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_filter_returns_400(self):
        invalid_filters = (
            {"salary_min": "invalid"},
            {"workplace_type": "FLEXIBLE"},
            {"job_type": "REMOTE"},
            {"experience_level": "SENIOR"},
            {"location": "Hải Phòng"},
        )
        for params in invalid_filters:
            with self.subTest(params=params):
                response = self.client.get(reverse("jobs-list"), params)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_search_keyword_e4_validation(self):
        # UC-03 E4: từ khóa chứa ký tự đặc biệt hoặc quá dài -> 400.
        invalid_keywords = (
            "<script>alert(1)</script>",
            "python; DROP TABLE jobs",
            "job@#$%",
            "a" * 101,
            # Chuỗi vô nghĩa toàn ký tự kỹ thuật cũng bị loại.
            "+++",
            "---",
            "###...",
            "&/()'",
        )
        for keyword in invalid_keywords:
            cache.clear()
            with self.subTest(keyword=keyword):
                response = self.client.get(
                    reverse("jobs-list"), {"keyword": keyword}
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("keyword", response.data["errors"])

        # Ký tự kỹ thuật hợp lệ của tên skill vẫn được nhận (C++, C#, .NET).
        valid_keywords = ("C++ developer", "C#", "ASP.NET", "Node.js", "HTML/CSS")
        for keyword in valid_keywords:
            cache.clear()
            with self.subTest(keyword=keyword):
                response = self.client.get(reverse("jobs-list"), {"keyword": keyword})
                self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_pending_skill_cannot_be_added_to_job(self):
        pending_skill = Skill.objects.create(
            name="Unknown",
            slug="unknown",
            status=Skill.Status.PENDING,
        )
        self.client.force_authenticate(self.employer)

        response = self.client.post(
            reverse("jobs-list"),
            {
                "title": "Python Developer",
                "description": "Build APIs",
                "required_skills": [str(pending_skill.id)],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_other_employer_cannot_update_job(self):
        job = self._job(status=JobPost.Status.DRAFT)
        other = User.objects.create_user(
            username="other-job-employer",
            email="other-job-employer@example.com",
            password="password123",
            role=User.Role.EMPLOYER,
        )
        Company.objects.create(
            owner=other,
            name="Other Company",
            status=Company.Status.APPROVED,
        )
        self.client.force_authenticate(other)

        response = self.client.patch(
            reverse("jobs-detail", args=[job.id]),
            {"title": "Stolen"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        job.refresh_from_db()
        self.assertEqual(job.title, "Django Developer")
