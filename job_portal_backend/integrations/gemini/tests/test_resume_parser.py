import io
import json
import zipfile
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError

from integrations.gemini.resume_parser import (
    normalize_resume_data,
    parse_resume_document,
)


class ResumeParserTests(SimpleTestCase):
    def _client_for(self, data):
        models = Mock()
        models.generate_content.return_value = SimpleNamespace(text=json.dumps(data))
        return SimpleNamespace(models=models), models

    @patch("integrations.gemini.resume_parser.get_gemini_client")
    def test_parses_valid_pdf_in_json_mode(self, get_client):
        client, models = self._client_for(
            {
                "full_name": "Candidate",
                "educations": [],
                "experiences": [],
                "skills": [" Python "],
            }
        )
        get_client.return_value = client

        result = parse_resume_document(
            filename="resume.pdf",
            mime_type="application/pdf",
            file_data=b"%PDF-1.4",
        )

        self.assertEqual(result.validated_data["full_name"], "Candidate")
        self.assertEqual(result.validated_data["skills"], ["Python"])
        config = models.generate_content.call_args.kwargs["config"]
        self.assertEqual(config.response_mime_type, "application/json")
        self.assertIsNotNone(config.response_schema)

    @patch("integrations.gemini.resume_parser.get_gemini_client")
    def test_docx_uses_extracted_text(self, get_client):
        client, models = self._client_for(
            {"educations": [], "experiences": [], "skills": []}
        )
        get_client.return_value = client
        xml = b'''<?xml version="1.0" encoding="UTF-8"?>
        <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
          <w:body><w:p><w:r><w:t>Python Developer</w:t></w:r></w:p></w:body>
        </w:document>'''
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("word/document.xml", xml)

        parse_resume_document(
            filename="resume.docx",
            mime_type=(
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ),
            file_data=buffer.getvalue(),
        )

        self.assertEqual(
            models.generate_content.call_args.kwargs["contents"][1],
            "Python Developer",
        )

    def test_false_string_does_not_become_true(self):
        normalized = normalize_resume_data(
            {
                "educations": [
                    {"school_name": "HUST", "is_completed": "false"}
                ],
                "experiences": [
                    {
                        "company_name": "Company",
                        "position": "Developer",
                        "is_current": "false",
                    }
                ],
            }
        )

        self.assertFalse(normalized["educations"][0]["is_completed"])
        self.assertFalse(normalized["educations"][0]["is_verified"])
        self.assertFalse(normalized["experiences"][0]["is_current"])

    def test_invalid_items_are_not_written_to_logs(self):
        secret = "private-company-and-school"

        with self.assertLogs("integrations.gemini.resume_parser", level="WARNING") as logs:
            normalize_resume_data(
                {
                    "educations": [{"description": secret}],
                    "experiences": [{"description": secret}],
                }
            )

        self.assertNotIn(secret, " ".join(logs.output))
        self.assertIn("educations[0]", logs.output[0])
        self.assertIn("experiences[0]", logs.output[1])

    @patch("integrations.gemini.resume_parser.get_gemini_client")
    def test_serializer_rejects_invalid_data(self, get_client):
        client, _ = self._client_for(
            {
                "phone": "1" * 21,
                "educations": [],
                "experiences": [],
                "skills": [],
            }
        )
        get_client.return_value = client

        with self.assertRaises(ValidationError):
            parse_resume_document(
                filename="resume.pdf",
                mime_type="application/pdf",
                file_data=b"%PDF-1.4",
            )
