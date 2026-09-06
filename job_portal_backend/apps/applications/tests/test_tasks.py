from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from apps.accounts.models import User
from apps.ai_analysis.models import ApplicationMatchResult
from apps.ai_analysis.tasks import compute_application_match_score
from apps.applications import services as application_services
from apps.applications.models import JobApplication
from apps.candidates.models import CandidateProfile, Experience
from apps.companies.models import Company
from apps.jobs.models import JobPost, JobSkill
from apps.skills.models import CandidateSkill, MatchingWeightConfig, Skill
from integrations.gemini.embeddings import (
    current_candidate_embedding_signature,
    current_job_embedding_signature,
)


class ApplicationMatchScoreTaskTests(TestCase):
    def setUp(self):
        employer = User.objects.create_user(
            username="score-employer",
            email="score-employer@example.com",
            password="password123",
            role=User.Role.EMPLOYER,
        )
        company = Company.objects.create(
            owner=employer,
            name="Score Company",
            status=Company.Status.APPROVED,
        )
        candidate_user = User.objects.create_user(
            username="score-candidate",
            email="score-candidate@example.com",
            password="password123",
            role=User.Role.CANDIDATE,
        )
        vector = [0.1] * 768
        self.profile = CandidateProfile.objects.create(
            user=candidate_user,
            full_name="Score Candidate",
            phone="0901234567",
            desired_position="Python Developer",
            embedding=vector,
            embedding_version=1,
            embedding_signature=current_candidate_embedding_signature(),
        )
        self.job = JobPost.objects.create(
            company=company,
            created_by=employer,
            title="Python Developer",
            description="Python APIs",
            status=JobPost.Status.ACTIVE,
            embedding=vector,
            embedding_version=1,
            embedding_signature=current_job_embedding_signature(),
        )
        self.skill = Skill.objects.create(name="Python", slug="score-python")
        CandidateSkill.objects.create(candidate=self.profile, skill=self.skill)
        Experience.objects.create(
            candidate=self.profile,
            company_name="Unknown",
            position="Developer",
            start_date=None,
        )
        JobSkill.objects.create(job=self.job, skill=self.skill)
        MatchingWeightConfig.objects.update(is_active=False)
        self.weight_config = MatchingWeightConfig.objects.create(
            name="Scoring weights",
            is_active=True,
            weight_semantic_similarity=Decimal("0.600"),
            weight_skill_overlap=Decimal("0.250"),
            weight_experience_match=Decimal("0.100"),
            weight_education_match=Decimal("0.050"),
        )
        self.application = application_services.apply_to_job(
            candidate_user,
            self.job,
        )

    def test_compute_match_score_uses_snapshot_components(self):
        result = compute_application_match_score(str(self.application.id))

        self.assertTrue(result)
        analysis = ApplicationMatchResult.objects.get(application=self.application)
        self.assertEqual(analysis.match_score, Decimal("100.00"))
        self.assertEqual(analysis.semantic_similarity_score, Decimal("1.00"))
        self.assertEqual(analysis.skill_overlap_score, Decimal("1.00"))
        self.assertIsNone(analysis.experience_score)
        self.assertIsNone(analysis.education_score)
        self.assertFalse(analysis.criteria_applicability["experience"])
        self.assertFalse(analysis.criteria_applicability["education"])
        self.assertEqual(
            self.application.matching_weight_snapshot["config_id"],
            str(self.weight_config.id),
        )
        self.assertEqual(analysis.matched_skills, ["Python"])
        self.assertEqual(analysis.missing_skills, [])

    def test_retry_does_not_overwrite_successful_analysis(self):
        compute_application_match_score(str(self.application.id))
        analysis = ApplicationMatchResult.objects.get(application=self.application)
        original_score = analysis.match_score
        original_created_at = analysis.created_at

        rust = Skill.objects.create(name="Rust", slug="score-rust")
        JobSkill.objects.create(job=self.job, skill=rust)
        MatchingWeightConfig.objects.update(is_active=False)
        MatchingWeightConfig.objects.create(
            name="Changed weights",
            is_active=True,
            weight_semantic_similarity=Decimal("0"),
            weight_skill_overlap=Decimal("1"),
            weight_experience_match=Decimal("0"),
            weight_education_match=Decimal("0"),
        )

        compute_application_match_score(str(self.application.id))
        analysis.refresh_from_db()
        self.assertEqual(analysis.match_score, original_score)
        self.assertEqual(analysis.created_at, original_created_at)

    def test_required_and_preferred_snapshot_skills_use_rho(self):
        self.application.job_snapshot["skills"] = [
            {"id": "r1", "name": "R1", "is_required": True},
            {"id": "r2", "name": "R2", "is_required": True},
            {"id": "p1", "name": "P1", "is_required": False},
            {"id": "p2", "name": "P2", "is_required": False},
        ]
        self.application.profile_snapshot["skills"] = [
            {"id": "r1", "name": "R1", "status": "PENDING", "is_active": True},
            {"id": "p1", "name": "P1", "status": "PENDING", "is_active": True},
            {"id": "p2", "name": "P2", "status": "APPROVED", "is_active": True},
        ]
        self.application.matching_weight_snapshot.update({
            "semantic": "0",
            "skill": "1",
            "experience": "0",
            "education": "0",
            "required_skill_multiplier": "2",
            "rule_version": "matching-v2.2.4",
        })
        self.application.save(update_fields=[
            "profile_snapshot", "job_snapshot", "matching_weight_snapshot",
        ])

        compute_application_match_score(str(self.application.id))

        analysis = ApplicationMatchResult.objects.get(application=self.application)
        self.assertEqual(analysis.match_score, Decimal("66.67"))
        self.assertEqual(analysis.skill_overlap_score, Decimal("0.6667"))
        self.assertEqual(analysis.matched_skills, ["P1", "P2", "R1"])
        self.assertEqual(analysis.missing_skills, ["R2"])

    def test_zero_weight_for_only_applicable_criteria_is_insufficient(self):
        self.application.job_snapshot["skills"] = []
        self.application.matching_weight_snapshot.update({
            "semantic": "0",
            "skill": "1",
            "experience": "0",
            "education": "0",
            "required_skill_multiplier": "2",
            "rule_version": "matching-v2.2.4",
        })
        self.application.save(update_fields=["job_snapshot", "matching_weight_snapshot"])

        compute_application_match_score(str(self.application.id))

        analysis = ApplicationMatchResult.objects.get(application=self.application)
        self.assertIsNone(analysis.match_score)
        self.assertEqual(analysis.status, ApplicationMatchResult.Status.INSUFFICIENT)
        self.application.refresh_from_db()
        self.assertEqual(self.application.match_status, JobApplication.MatchStatus.INSUFFICIENT)

    def test_invalid_embedding_marks_matching_failed_without_fake_score(self):
        self.application.candidate_embedding_snapshot = [0.0] * 768
        self.application.save(update_fields=["candidate_embedding_snapshot"])

        with self.assertRaisesMessage(ValueError, "zero vector"):
            compute_application_match_score(str(self.application.id))

        self.application.refresh_from_db()
        self.assertEqual(self.application.match_status, JobApplication.MatchStatus.FAILED)
        self.assertFalse(
            ApplicationMatchResult.objects.filter(application=self.application).exists()
        )

    def test_profile_changes_after_apply_do_not_change_snapshot_score(self):
        self.profile.candidate_skills.all().delete()
        self.profile.profile_version = 2
        self.profile.embedding = [1.0] + [0.0] * 767
        self.profile.embedding_version = 2
        self.profile.save(
            update_fields=["profile_version", "embedding", "embedding_version"]
        )

        compute_application_match_score(str(self.application.id))

        analysis = ApplicationMatchResult.objects.get(application=self.application)
        self.assertEqual(analysis.match_score, Decimal("100.00"))
        self.assertEqual(analysis.matched_skills, ["Python"])

    @patch("apps.ai_analysis.tasks.embed_document")
    def test_missing_snapshot_vector_calls_gemini_without_overwriting_profile(self, embed):
        self.application.candidate_embedding_snapshot = None
        self.application.save(update_fields=["candidate_embedding_snapshot"])
        self.profile.profile_version = 2
        self.profile.embedding_version = 2
        self.profile.embedding = [1.0] + [0.0] * 767
        self.profile.save(
            update_fields=["profile_version", "embedding_version", "embedding"]
        )
        original_profile_vector = list(self.profile.embedding)
        embed.return_value = [0.1] * 768

        compute_application_match_score(str(self.application.id))

        self.application.refresh_from_db()
        self.profile.refresh_from_db()
        embed.assert_called_once_with(
            self.application.profile_snapshot["embedding_text"]
        )
        self.assertEqual(list(self.application.candidate_embedding_snapshot), [0.1] * 768)
        self.assertEqual(list(self.profile.embedding), original_profile_vector)

    def test_legacy_application_without_snapshot_is_not_retried_forever(self):
        legacy_job = JobPost.objects.create(
            company=self.job.company,
            created_by=self.job.created_by,
            title="Legacy job",
            description="Legacy",
            status=JobPost.Status.ACTIVE,
        )
        legacy = JobApplication.objects.create(
            job=legacy_job,
            candidate=self.profile,
        )

        self.assertFalse(compute_application_match_score(str(legacy.pk)))
        self.assertFalse(
            ApplicationMatchResult.objects.filter(application=legacy).exists()
        )
