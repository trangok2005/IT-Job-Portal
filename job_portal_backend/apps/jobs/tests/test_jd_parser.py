import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import TestCase

from apps.jobs.services import build_jd_parse_result
from apps.skills.models import Skill, SkillAlias
from integrations.gemini.jd_parser import parse_job_description


class JobDescriptionParserTests(TestCase):
    @patch("integrations.gemini.jd_parser.get_gemini_client")
    def test_parse_returns_validated_fields_and_normalized_skills(self, get_client):
        python = Skill.objects.create(name="Python", slug="python")
        SkillAlias.objects.create(
            skill=python,
            alias_text="Python 3",
            normalized_text="python 3",
        )
        response = SimpleNamespace(
            text=json.dumps(
                {
                    "title": "Backend Developer",
                    "description": "Build services",
                    "requirements": "2 years experience",
                    "benefits": "Remote work",
                    "location": "Ho Chi Minh City",
                    "workplace_type": "REMOTE",
                    "job_type": "FULL_TIME",
                    "experience_level": "JUNIOR",
                    "required_education_level": "BACHELOR",
                    "salary_min": 20000000,
                    "salary_max": 30000000,
                    "salary_negotiable": False,
                    "expires_at": None,
                    "skills": [
                        {"name": "Python 3", "is_required": True},
                        {"name": "New Framework", "is_required": False},
                        {"name": "python 3", "is_required": False},
                    ],
                }
            )
        )
        client = Mock()
        client.models.generate_content.return_value = response
        get_client.return_value = client

        result = parse_job_description(
            filename="job.pdf",
            mime_type="application/pdf",
            file_data=b"%PDF-1.4",
        )
        parsed = build_jd_parse_result(result.validated_data)

        self.assertEqual(parsed["title"], "Backend Developer")
        self.assertEqual(parsed["location"], "Hồ Chí Minh")
        self.assertEqual(parsed["workplace_type"], "REMOTE")
        self.assertEqual(parsed["required_education_level"], "BACHELOR")
        pending = Skill.objects.get(name="New Framework")
        self.assertEqual(pending.status, Skill.Status.PENDING)
        # Kỹ năng lạ đã được tự tạo PENDING và nằm luôn trong matched
        # (nhất quán với luồng CV) thay vì bị bỏ vào unmatched.
        self.assertEqual(
            parsed["required_skills"], [str(python.id), str(pending.id)]
        )
        self.assertEqual(parsed["unmatched_skills"], [])
        self.assertEqual(
            parsed["resolved_skills"],
            [
                {"id": str(python.id), "name": "Python", "status": Skill.Status.APPROVED, "is_required": True},
                {"id": str(pending.id), "name": "New Framework", "status": Skill.Status.PENDING, "is_required": False},
            ],
        )
        client.models.generate_content.assert_called_once()
        config = client.models.generate_content.call_args.kwargs["config"]
        self.assertEqual(config.response_mime_type, "application/json")
        self.assertIsNotNone(config.response_schema)

    def test_aliases_resolving_to_same_skill_keep_required_flag(self):
        react = Skill.objects.create(name="React", slug="react")
        SkillAlias.objects.create(
            skill=react,
            alias_text="ReactJS",
            normalized_text="reactjs",
        )

        parsed = build_jd_parse_result(
            {
                "skills": ["React", "ReactJS"],
                "_skill_required_flags": {"react": False, "reactjs": True},
            }
        )

        self.assertEqual(parsed["unmatched_skills"], [])
        self.assertEqual(len(parsed["resolved_skills"]), 1)
        self.assertEqual(parsed["resolved_skills"][0]["id"], str(react.id))
        self.assertTrue(parsed["resolved_skills"][0]["is_required"])

    def test_exact_skill_name_is_reused(self):
        django = Skill.objects.create(name="Django", slug="django")

        parsed = build_jd_parse_result({"skills": [" Django "]})

        self.assertEqual(parsed["unmatched_skills"], [])
        self.assertEqual(len(parsed["resolved_skills"]), 1)
        self.assertEqual(parsed["resolved_skills"][0]["id"], str(django.id))
        self.assertFalse(Skill.objects.filter(status=Skill.Status.PENDING).exists())

    @patch("integrations.gemini.jd_parser.get_gemini_client")
    def test_parser_does_not_create_skill_before_business_resolution(self, get_client):
        client = Mock()
        client.models.generate_content.return_value = SimpleNamespace(
            text=json.dumps({"skills": [{"name": "New Tool", "is_required": True}]})
        )
        get_client.return_value = client

        result = parse_job_description(
            filename="job.pdf",
            mime_type="application/pdf",
            file_data=b"%PDF-1.4",
        )

        self.assertFalse(Skill.objects.filter(name="New Tool").exists())
        parsed = build_jd_parse_result(result.validated_data)
        self.assertEqual(parsed["resolved_skills"][0]["status"], Skill.Status.PENDING)
