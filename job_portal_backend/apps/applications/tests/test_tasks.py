from django.test import TestCase

from apps.accounts.models import User
from apps.ai_analysis.models import AIAnalysis
from apps.ai_analysis.tasks import compute_application_match_score
from apps.applications.models import JobApplication
from apps.candidates.models import CandidateProfile
from apps.companies.models import Company
from integrations.gemini.embeddings import (
    current_candidate_embedding_signature,
    current_job_embedding_signature,
)
from apps.jobs.models import JobPost, JobSkill
from apps.skills.models import CandidateSkill, Skill


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
        skill = Skill.objects.create(name="Python", slug="score-python")
        CandidateSkill.objects.create(candidate=self.profile, skill=skill)
        JobSkill.objects.create(job=self.job, skill=skill)
        self.application = JobApplication.objects.create(
            job=self.job,
            candidate=self.profile,
        )

    def test_compute_match_score_uses_cosine_similarity(self):
        result = compute_application_match_score(str(self.application.id))

        self.assertTrue(result)
        analysis = AIAnalysis.objects.get(application=self.application)
        self.assertEqual(analysis.match_score, 100)
        self.assertEqual(analysis.semantic_similarity_score, 100)
        self.assertEqual(analysis.skill_overlap_score, 100)
        self.assertEqual(analysis.matched_skills, ["Python"])
        self.assertEqual(analysis.missing_skills, [])
        self.assertEqual(
            analysis.candidate_embedding_version,
            self.profile.embedding_version,
        )
        self.assertEqual(analysis.job_embedding_version, self.job.embedding_version)
        self.assertFalse(analysis.inputs_are_stale)
