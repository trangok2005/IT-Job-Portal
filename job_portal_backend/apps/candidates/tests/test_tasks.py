import json
import io
import tempfile
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from apps.accounts.models import User
from apps.candidates.models import CandidateProfile, Education, Resume, ResumeImport
from apps.candidates.tasks import (
    MAX_PARSE_ATTEMPTS,
    _normalize_parsed_data,
    cleanup_expired_resume_imports,
    generate_candidate_embedding,
    parse_resume_import,
)


class CandidateEmbeddingTaskTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(
            username="embedding-user",
            email="embedding@example.com",
            password="password123",
            role=User.Role.CANDIDATE,
        )
        self.profile = CandidateProfile.objects.create(
            user=user,
            full_name="Embedding User",
            headline="Python Developer",
        )

    @patch("apps.candidates.tasks.embed_document", return_value=[0.1] * 768)
    def test_embedding_is_saved_for_current_version(self, generate):

        result = generate_candidate_embedding(
            str(self.profile.id),
            self.profile.profile_version,
        )

        self.assertTrue(result)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.embedding_version, self.profile.profile_version)
        self.assertFalse(self.profile.embedding_is_stale)
        self.assertEqual(
            generate.call_args.args[0],
            "Headline: Python Developer",
        )

    @patch("apps.candidates.tasks.embed_document")
    def test_stale_task_does_not_call_gemini(self, generate):
        result = generate_candidate_embedding(str(self.profile.id), 999)

        self.assertFalse(result)
        generate.assert_not_called()


class ResumeParseTaskTests(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.override = override_settings(MEDIA_ROOT=Path(self.temp_dir.name))
        self.override.enable()
        self.addCleanup(self.override.disable)

        user = User.objects.create_user(
            username="parse-user",
            email="parse@example.com",
            password="password123",
            role=User.Role.CANDIDATE,
        )
        self.profile = CandidateProfile.objects.create(user=user, full_name="Before Parse")
        self.resume = Resume.objects.create(
            candidate=self.profile,
            file=SimpleUploadedFile(
                "cv.pdf",
                b"%PDF-1.4 test",
                content_type="application/pdf",
            ),
            original_filename="cv.pdf",
            is_primary=True,
        )

    @patch("apps.candidates.tasks._get_client")
    def test_parse_resume_import_stores_review_preview_without_mutating_profile(self, get_client):
        raw_data = {
            "full_name": "After Parse",
            "phone": "0901234567",
            "headline": "Backend Developer",
            "summary": "Python developer",
            "educations": [
                {
                    "school_name": "HUST",
                    "major": "Software Engineering",
                    "degree": "Engineer",
                    "start_date": "2020-01-01",
                    "end_date": "2024-01-01",
                    "description": "",
                }
            ],
            "experiences": [],
            "skills": ["Python"],
        }
        models = Mock()
        models.generate_content.return_value = SimpleNamespace(
            text=json.dumps(raw_data)
        )
        get_client.return_value = SimpleNamespace(models=models)

        resume_import = ResumeImport.objects.create(
            candidate=self.profile,
            file=SimpleUploadedFile("cv.pdf", b"%PDF-1.4 test", content_type="application/pdf"),
            original_filename="cv.pdf",
        )

        result = parse_resume_import(str(resume_import.id))

        self.assertEqual(result, raw_data)
        resume_import.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertEqual(
            resume_import.parse_status, ResumeImport.ParseStatus.SUCCESS
        )
        self.assertEqual(resume_import.parsed_data["full_name"], "After Parse")
        self.assertEqual(
            resume_import.parsed_data["educations"][0]["school_name"], "HUST"
        )
        self.assertEqual(self.profile.full_name, "Before Parse")
        self.assertFalse(Education.objects.filter(candidate=self.profile).exists())

    @patch("apps.candidates.tasks._get_client")
    def test_parse_docx_sends_extracted_text_to_gemini(self, get_client):
        document_xml = b'''<?xml version="1.0" encoding="UTF-8"?>
        <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
          <w:body><w:p><w:r><w:t>Python Intern Developer</w:t></w:r></w:p></w:body>
        </w:document>'''
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("word/document.xml", document_xml)
        models = Mock()
        models.generate_content.return_value = SimpleNamespace(
            text=json.dumps({"educations": [], "experiences": [], "skills": []})
        )
        get_client.return_value = SimpleNamespace(models=models)
        resume_import = ResumeImport.objects.create(
            candidate=self.profile,
            file=SimpleUploadedFile(
                "cv.docx",
                buffer.getvalue(),
                content_type=(
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                ),
            ),
            original_filename="cv.docx",
        )

        parse_resume_import(str(resume_import.id))

        contents = models.generate_content.call_args.kwargs["contents"]
        self.assertEqual(contents[1], "Python Intern Developer")

    @patch("apps.candidates.tasks._get_client")
    def test_parse_resume_import_stops_after_max_attempts(self, get_client):
        models = Mock()
        models.generate_content.side_effect = RuntimeError("Gemini unavailable")
        get_client.return_value = SimpleNamespace(models=models)

        resume_import = ResumeImport.objects.create(
            candidate=self.profile,
            file=SimpleUploadedFile("cv.pdf", b"%PDF-1.4 test", content_type="application/pdf"),
            original_filename="cv.pdf",
        )

        for _ in range(MAX_PARSE_ATTEMPTS):
            with self.assertRaises(RuntimeError):
                parse_resume_import(str(resume_import.id))

        self.assertEqual(models.generate_content.call_count, MAX_PARSE_ATTEMPTS)
        resume_import.refresh_from_db()
        self.assertEqual(resume_import.parse_attempts, MAX_PARSE_ATTEMPTS)

        # Lượt gọi thứ N + 1: không đụng Gemini nữa, chốt FAILED vĩnh viễn.
        result = parse_resume_import(str(resume_import.id))

        self.assertEqual(result, {})
        self.assertEqual(models.generate_content.call_count, MAX_PARSE_ATTEMPTS)
        resume_import.refresh_from_db()
        self.assertEqual(resume_import.parse_status, ResumeImport.ParseStatus.FAILED)
        self.assertIn("vượt quá", resume_import.parse_error_message.lower())

    def test_parse_resume_import_missing_record_returns_empty(self):
        ghost_id = "00000000-0000-0000-0000-000000000000"

        self.assertEqual(parse_resume_import(ghost_id), {})

    @patch("apps.candidates.tasks._get_client")
    def test_processing_duplicate_does_not_call_gemini(self, get_client):
        resume_import = ResumeImport.objects.create(
            candidate=self.profile,
            file=SimpleUploadedFile("cv.pdf", b"%PDF-1.4 test", content_type="application/pdf"),
            original_filename="cv.pdf",
            parse_status=ResumeImport.ParseStatus.PROCESSING,
            parse_attempts=1,
        )

        with self.assertRaises(RuntimeError):
            parse_resume_import(str(resume_import.id))

        get_client.assert_not_called()
        resume_import.refresh_from_db()
        self.assertEqual(resume_import.parse_status, ResumeImport.ParseStatus.PROCESSING)

    def test_cleanup_removes_expired_pending_imports(self):
        from datetime import timedelta

        from django.utils import timezone

        expired_pending = ResumeImport.objects.create(
            candidate=self.profile,
            file=SimpleUploadedFile("old.pdf", b"%PDF-1.4", content_type="application/pdf"),
            original_filename="old.pdf",
        )
        ResumeImport.objects.filter(pk=expired_pending.pk).update(
            expires_at=timezone.now() - timedelta(hours=25)
        )
        fresh = ResumeImport.objects.create(
            candidate=self.profile,
            file=SimpleUploadedFile("new.pdf", b"%PDF-1.4", content_type="application/pdf"),
            original_filename="new.pdf",
        )

        removed = cleanup_expired_resume_imports()

        self.assertEqual(removed, 1)
        self.assertFalse(ResumeImport.objects.filter(pk=expired_pending.pk).exists())
        self.assertTrue(ResumeImport.objects.filter(pk=fresh.pk).exists())

    def test_normalize_parsed_data_converts_nullable_text_fields(self):
        normalized = _normalize_parsed_data({
            "headline": None,
            "educations": [{"school_name": "HUST", "degree": None}],
            "experiences": [{
                "company_name": "TechCorp",
                "position": "Developer",
                "description": None,
                "is_current": None,
            }],
            "skills": [" Python ", None, ""],
        })

        self.assertEqual(normalized["headline"], "")
        self.assertEqual(normalized["educations"][0]["degree"], "")
        self.assertEqual(normalized["experiences"][0]["description"], "")
        self.assertFalse(normalized["experiences"][0]["is_current"])
        self.assertEqual(normalized["skills"], ["Python"])
