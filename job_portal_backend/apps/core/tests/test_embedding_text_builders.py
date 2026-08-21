from datetime import date

from django.test import TestCase

from apps.accounts.models import User
from apps.candidates.models import CandidateProfile, Education, Experience
from apps.companies.models import Company
from apps.core.embedding_text_builders import (
    build_candidate_text,
    build_job_text,
    build_query_text,
)
from apps.jobs.models import JobPost, JobSkill
from apps.skills.models import CandidateSkill, Skill


class EmbeddingTextBuilderTests(TestCase):
    def setUp(self):
        candidate_user = User.objects.create_user(
            username="builder-candidate",
            email="builder-candidate@example.com",
            password="password123",
            role=User.Role.CANDIDATE,
        )
        self.profile = CandidateProfile.objects.create(
            user=candidate_user,
            full_name="Private Name",
            address="Private Address",
            desired_position="Backend Developer",
            headline="Python Developer",
            summary="Build <b>APIs</b>",
        )
        Education.objects.create(
            candidate=self.profile,
            school_name="Private University",
            degree="Bachelor",
            major="Computer Science",
            end_date=date(2024, 6, 1),
        )
        Experience.objects.create(
            candidate=self.profile,
            company_name="Old Company",
            position="Junior Developer",
            end_date=date(2022, 1, 1),
            description="Maintained APIs",
        )
        Experience.objects.create(
            candidate=self.profile,
            company_name="Current Company",
            position="Backend Developer",
            is_current=True,
            description="Build microservices",
        )
        skill = Skill.objects.create(name="Python", slug="builder-python")
        CandidateSkill.objects.create(candidate=self.profile, skill=skill)

        employer = User.objects.create_user(
            username="builder-employer",
            email="builder-employer@example.com",
            password="password123",
            role=User.Role.EMPLOYER,
        )
        company = Company.objects.create(
            owner=employer,
            name="Builder Company",
            status=Company.Status.APPROVED,
        )
        self.job = JobPost.objects.create(
            company=company,
            created_by=employer,
            title="Backend Intern",
            description="Build <script>noise()</script> Python APIs",
            requirements="Know Python",
            experience_level=JobPost.ExperienceLevel.INTERN,
        )
        JobSkill.objects.create(job=self.job, skill=skill)

    def test_candidate_text_is_focused_and_recent_experience_is_first(self):
        text = build_candidate_text(self.profile)

        self.assertIn("Desired position: Backend Developer", text)
        self.assertIn("Education: Degree: Bachelor; Major: Computer Science", text)
        self.assertLess(
            text.index("Position: Backend Developer"),
            text.index("Position: Junior Developer"),
        )
        self.assertNotIn("Private Name", text)
        self.assertNotIn("Private University", text)
        self.assertNotIn("Current Company", text)

    def test_job_text_contains_only_focused_fields(self):
        text = build_job_text(self.job)

        self.assertEqual(
            text,
            "Position: Backend Intern\n"
            "Role summary: Build Python APIs\n"
            "Requirements: Know Python\n"
            "Experience level: Thực tập sinh\n"
            "Skills: Python",
        )

    def test_pending_skills_in_candidate_text_but_not_job_text(self):
        # UC-01 bước 11: skill PENDING của ứng viên vẫn tính vào text vector;
        # pending chỉ bị loại khỏi bộ lọc SQL cứng. Phía JD giữ nguyên APPROVED-only.
        pending = Skill.objects.create(
            name="Secret Skill",
            slug="builder-pending",
            status=Skill.Status.PENDING,
        )
        CandidateSkill.objects.create(candidate=self.profile, skill=pending)
        JobSkill.objects.create(job=self.job, skill=pending)

        candidate_text = build_candidate_text(self.profile)
        job_text = build_job_text(self.job)

        self.assertIn("Skills: Python, Secret Skill", candidate_text)
        self.assertNotIn("Secret Skill", job_text)

    def test_query_text_uses_desired_job_label_and_shared_cleaner(self):
        self.assertEqual(
            build_query_text("<b>Python</b> backend"),
            "Desired job: Python backend",
        )
