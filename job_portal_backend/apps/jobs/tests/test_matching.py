from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.candidates.models import CandidateProfile, DegreeLevel, Education, Experience
from apps.companies.models import Company
from apps.core.matching import (
    required_degree_level,
    total_experience_years,
)
from apps.jobs.models import JobPost, JobSkill
from apps.jobs.selectors import get_recommended_candidates, get_recommended_jobs
from apps.skills.models import CandidateSkill, MatchingWeightConfig, Skill
from apps.skills.selectors import get_active_matching_weights
from integrations.gemini.embeddings import (
    current_candidate_embedding_signature,
    current_job_embedding_signature,
)


class WeightedRecommendationTests(TestCase):
    def setUp(self):
        self.employer = User.objects.create_user(
            username="matching-employer",
            email="matching-employer@example.com",
            password="password123",
            role=User.Role.EMPLOYER,
        )
        self.company = Company.objects.create(
            owner=self.employer,
            name="Matching Company",
            status=Company.Status.APPROVED,
        )
        self.candidate_user = User.objects.create_user(
            username="matching-candidate",
            email="matching-candidate@example.com",
            password="password123",
            role=User.Role.CANDIDATE,
        )
        self.profile = CandidateProfile.objects.create(
            user=self.candidate_user,
            full_name="Matching Candidate",
            embedding=[1.0] + [0.0] * 767,
            embedding_version=1,
            embedding_signature=current_candidate_embedding_signature(),
        )
        self.python = Skill.objects.create(name="Python matching", slug="python-matching")
        self.java = Skill.objects.create(name="Java matching", slug="java-matching")
        CandidateSkill.objects.create(candidate=self.profile, skill=self.python)

    def _job(self, title, vector, **overrides):
        data = {
            "company": self.company,
            "created_by": self.employer,
            "title": title,
            "description": title,
            "status": JobPost.Status.ACTIVE,
            "expires_at": timezone.now() + timedelta(days=30),
            "embedding": vector,
            "embedding_version": 1,
            "embedding_signature": current_job_embedding_signature(),
        }
        data.update(overrides)
        return JobPost.objects.create(**data)

    def _weights(self, semantic, skill, experience=0, education=0):
        MatchingWeightConfig.objects.update(is_active=False)
        MatchingWeightConfig.objects.create(
            name="Test active weights",
            is_active=True,
            weight_semantic_similarity=Decimal(str(semantic)),
            weight_skill_overlap=Decimal(str(skill)),
            weight_experience_match=Decimal(str(experience)),
            weight_education_match=Decimal(str(education)),
        )

    def test_candidate_config_reverses_global_order_and_reports_components(self):
        semantic_job = self._job("Semantic", [1.0] + [0.0] * 767)
        JobSkill.objects.create(job=semantic_job, skill=self.java)
        skill_job = self._job("Skill", [0.0, 1.0] + [0.0] * 766)
        JobSkill.objects.create(job=skill_job, skill=self.python)

        self._weights(1, 0)
        self.assertEqual(get_recommended_jobs(self.profile).first().pk, semantic_job.pk)

        self._weights(0, 1)
        results = list(get_recommended_jobs(self.profile))

        self.assertEqual([item.pk for item in results], [skill_job.pk, semantic_job.pk])
        self.assertEqual(results[0].skill_score, 100.0)
        self.assertEqual(results[1].skill_score, 0.0)
        self.assertEqual(results[0].match_score, 100.0)

    def test_components_include_neutral_skill_experience_and_education(self):
        Experience.objects.create(
            candidate=self.profile,
            company_name="One year",
            position="Developer",
            start_date=timezone.localdate() - timedelta(days=366),
            end_date=timezone.localdate(),
        )
        Education.objects.create(
            candidate=self.profile,
            school_name="University",
            degree="Bachelor of Engineering",
            degree_level=DegreeLevel.BACHELOR,
            is_completed=True,
            is_verified=True,
        )
        neutral = self._job(
            "Neutral",
            [1.0] + [0.0] * 767,
            requirements="Không yêu cầu bằng đại học",
            experience_level=JobPost.ExperienceLevel.ENTRY,
            required_education_level=DegreeLevel.NONE,
        )
        demanding = self._job(
            "Demanding",
            [1.0] + [0.0] * 767,
            requirements="Master's degree required",
            experience_level=JobPost.ExperienceLevel.MID_SENIOR,
            required_education_level=DegreeLevel.MASTER,
        )
        self._weights(0, 0, experience=Decimal("0.333"), education=Decimal("0.667"))

        by_id = {item.pk: item for item in get_recommended_jobs(self.profile)}

        self.assertEqual(by_id[neutral.pk].skill_score, 0.0)
        self.assertEqual(by_id[neutral.pk].experience_score, 100.0)
        self.assertEqual(by_id[neutral.pk].education_score, 0.0)
        self.assertEqual(by_id[neutral.pk].match_score, 100.0)
        self.assertAlmostEqual(by_id[demanding.pk].experience_score, 33.4, delta=0.2)
        self.assertEqual(by_id[demanding.pk].education_score, 75.0)
        self.assertAlmostEqual(by_id[demanding.pk].match_score, 61.13, delta=0.2)

    def test_employer_direction_ignores_weights_and_stale_candidate_is_null_last(self):
        job = self._job("Employer ranking", [1.0] + [0.0] * 767)
        JobSkill.objects.create(job=job, skill=self.python)
        semantic_user = User.objects.create_user(
            username="semantic-only",
            email="semantic-only@example.com",
            password="password123",
            role=User.Role.CANDIDATE,
        )
        semantic_profile = CandidateProfile.objects.create(
            user=semantic_user,
            full_name="Semantic only",
            embedding=[1.0] + [0.0] * 767,
            embedding_version=1,
            embedding_signature=current_candidate_embedding_signature(),
        )
        skill_user = User.objects.create_user(
            username="skill-only",
            email="skill-only@example.com",
            password="password123",
            role=User.Role.CANDIDATE,
        )
        skill_profile = CandidateProfile.objects.create(
            user=skill_user,
            full_name="Skill only",
            embedding=[0.0, 1.0] + [0.0] * 766,
            embedding_version=1,
            embedding_signature=current_candidate_embedding_signature(),
        )
        CandidateSkill.objects.create(candidate=skill_profile, skill=self.python)
        self.profile.profile_version = 2
        self.profile.save(update_fields=["profile_version"])

        # Trọng số DB không ảnh hưởng chiều NTD -> candidate (cosine thuần).
        self._weights(1, 0)
        results = list(get_recommended_candidates(job))
        self.assertEqual(results[0].pk, semantic_profile.pk)

        self._weights(0, 1)
        results = list(get_recommended_candidates(job))
        self.assertEqual([item.pk for item in results[:2]], [semantic_profile.pk, skill_profile.pk])
        self.assertEqual(results[0].match_score, 100.0)
        stale = next(item for item in results if item.pk == self.profile.pk)
        self.assertIsNone(stale.match_score)
        self.assertEqual(results[-1].pk, stale.pk)

    def test_missing_active_config_returns_no_weights(self):
        MatchingWeightConfig.objects.all().delete()
        self.assertIsNone(get_active_matching_weights())


class DegreeRequirementTests(TestCase):
    def test_degree_detection_is_accent_insensitive_and_honors_negation(self):
        self.assertEqual(required_degree_level("Tốt nghiệp Thạc sĩ CNTT"), 3)
        self.assertEqual(required_degree_level("Yêu cầu bằng cao đẳng"), 1)
        self.assertEqual(required_degree_level("PhD or doctorate required"), 4)
        self.assertEqual(required_degree_level("Không yêu cầu bằng đại học"), 0)
        self.assertEqual(required_degree_level("Strong communication skills"), 0)
        self.assertEqual(required_degree_level("3 years of software engineering"), 0)

    def test_experience_ignores_invalid_intervals_and_merges_overlaps(self):
        today = timezone.localdate()
        intervals = [
            (today - timedelta(days=365), today, False),
            (today - timedelta(days=365), None, True),
            (None, today, False),
            (today, today - timedelta(days=1), False),
            (today - timedelta(days=30), None, False),
        ]

        self.assertAlmostEqual(total_experience_years(intervals, today), 1.0, delta=0.01)
