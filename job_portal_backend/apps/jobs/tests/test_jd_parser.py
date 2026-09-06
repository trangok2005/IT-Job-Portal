import json
import io
import zipfile
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from apps.jobs.jd_parser import _extract_docx_text, parse_job_description
from apps.skills.models import Skill, SkillAlias


@override_settings(GEMINI_API_KEY="test-key")
class JobDescriptionParserTests(TestCase):
    def test_extract_docx_text(self):
        document_xml = b'''<?xml version="1.0" encoding="UTF-8"?>
        <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
          <w:body><w:p><w:r><w:t>Backend Developer</w:t></w:r></w:p></w:body>
        </w:document>'''
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("word/document.xml", document_xml)

        self.assertEqual(_extract_docx_text(buffer.getvalue()), "Backend Developer")

    @patch("apps.jobs.jd_parser._get_client")
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

        _, parsed = parse_job_description(
            SimpleUploadedFile("job.pdf", b"%PDF-1.4")
        )

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
