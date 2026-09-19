import io
import zipfile

from django.test import SimpleTestCase

from integrations.gemini.document_input import (
    DocumentInputError,
    prepare_document_input,
)


class DocumentInputTests(SimpleTestCase):
    def test_extracts_docx_text(self):
        xml = b'''<?xml version="1.0" encoding="UTF-8"?>
        <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
          <w:body><w:p><w:r><w:t>Backend Developer</w:t></w:r></w:p></w:body>
        </w:document>'''
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("word/document.xml", xml)

        result = prepare_document_input(
            "resume.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            buffer.getvalue(),
        )

        self.assertEqual(result, "Backend Developer")

    def test_prepares_pdf_part(self):
        result = prepare_document_input("resume.pdf", "application/pdf", b"%PDF-1.4")

        self.assertEqual(result.inline_data.mime_type, "application/pdf")

    def test_rejects_empty_or_unsupported_document(self):
        with self.assertRaises(DocumentInputError):
            prepare_document_input("resume.pdf", "application/pdf", b"")
        with self.assertRaises(DocumentInputError):
            prepare_document_input("resume.txt", "text/plain", b"content")
