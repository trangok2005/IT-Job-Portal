from types import SimpleNamespace

from django.test import SimpleTestCase

from integrations.gemini.structured_output import (
    StructuredOutputError,
    parse_json_object_response,
)


class StructuredOutputTests(SimpleTestCase):
    def test_reads_valid_json_object(self):
        result = parse_json_object_response(SimpleNamespace(text='{"title": "Python"}'))

        self.assertEqual(result, {"title": "Python"})

    def test_removes_markdown_json_fence(self):
        result = parse_json_object_response(
            SimpleNamespace(text='```JSON\n{"title": "Python"}\n```')
        )

        self.assertEqual(result, {"title": "Python"})

    def test_rejects_empty_response(self):
        for response in (None, SimpleNamespace(text=None), SimpleNamespace(text="  ")):
            with self.subTest(response=response):
                with self.assertRaises(StructuredOutputError):
                    parse_json_object_response(response)

    def test_rejects_invalid_json(self):
        with self.assertRaisesMessage(StructuredOutputError, "JSON không hợp lệ"):
            parse_json_object_response(SimpleNamespace(text="{invalid"))

    def test_rejects_non_object_json(self):
        with self.assertRaisesMessage(StructuredOutputError, "JSON object"):
            parse_json_object_response(SimpleNamespace(text='["Python"]'))
