from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings

from integrations.gemini.embeddings import (
    EmbeddingError,
    embed_query,
    generate_embedding,
)
from apps.core.text_processing import (
    build_labeled_text,
    build_skills_line,
    clean_and_limit_text,
    clean_text_field,
)


class TextProcessingTests(SimpleTestCase):
    def test_clean_text_field_removes_markup_and_identifiers(self):
        raw = (
            "<p>Python&nbsp; Developer</p> test@example.com 0901 234 567 "
            "https://example.com 550e8400-e29b-41d4-a716-446655440000"
        )

        self.assertEqual(clean_text_field(raw), "Python Developer")

    def test_clean_text_field_removes_script_and_style_contents(self):
        raw = (
            "Backend <script>alert('noise')</script>"
            "<style>.hidden { display: none; }</style> Python"
        )

        self.assertEqual(clean_text_field(raw), "Backend Python")

    def test_labeled_text_omits_empty_values(self):
        self.assertEqual(
            build_labeled_text(
                [("Title", " Backend  Developer "), ("Summary", None)]
            ),
            "Title: Backend Developer",
        )

    def test_skills_are_cleaned_and_deduplicated_in_order(self):
        self.assertEqual(
            build_skills_line(["Python", " Python ", "Django", ""]),
            "Python, Django",
        )

    def test_long_text_is_cleaned_and_cut_at_a_word_boundary(self):
        self.assertEqual(
            clean_and_limit_text("<p>Python   backend developer</p>", 15),
            "Python backend",
        )


class EmbeddingAdapterTests(SimpleTestCase):
    @override_settings(GEMINI_API_KEY="test-key")
    @patch("integrations.gemini.embeddings.EMBEDDING_MODEL", "test-model")
    @patch("integrations.gemini.embeddings.EMBEDDING_DIMENSIONS", 3)
    @patch("integrations.gemini.embeddings.get_gemini_client")
    def test_generate_embedding_uses_shared_model_and_dimension(self, get_client):
        models = Mock()
        models.embed_content.return_value = SimpleNamespace(
            embeddings=[SimpleNamespace(values=[0.1, 0.2, 0.3])]
        )
        get_client.return_value = SimpleNamespace(models=models)

        result = generate_embedding("Search query: Python")

        self.assertEqual(result, [0.1, 0.2, 0.3])
        call = models.embed_content.call_args
        self.assertEqual(call.kwargs["model"], "test-model")
        self.assertEqual(call.kwargs["contents"], "Search query: Python")
        self.assertEqual(call.kwargs["config"].output_dimensionality, 3)
        self.assertEqual(call.kwargs["config"].task_type, "RETRIEVAL_DOCUMENT")

    @override_settings(GEMINI_API_KEY="test-key")
    @patch("integrations.gemini.embeddings.EMBEDDING_MODEL", "test-model")
    @patch("integrations.gemini.embeddings.EMBEDDING_DIMENSIONS", 3)
    @patch("integrations.gemini.embeddings.get_gemini_client")
    def test_embed_query_sends_retrieval_query_task_type(self, get_client):
        models = Mock()
        models.embed_content.return_value = SimpleNamespace(
            embeddings=[SimpleNamespace(values=[0.1, 0.2, 0.3])]
        )
        get_client.return_value = SimpleNamespace(models=models)

        result = embed_query("Python backend")

        self.assertEqual(result, [0.1, 0.2, 0.3])
        call = models.embed_content.call_args
        self.assertEqual(call.kwargs["config"].task_type, "RETRIEVAL_QUERY")

    @override_settings(GEMINI_API_KEY="test-key")
    @patch("integrations.gemini.embeddings.get_gemini_client")
    def test_generate_embedding_rejects_unknown_task_type(self, get_client):
        with self.assertRaisesMessage(EmbeddingError, "task_type"):
            generate_embedding("Python", task_type="CLASSIFICATION")

    @override_settings(GEMINI_API_KEY="test-key")
    @patch("integrations.gemini.embeddings.EMBEDDING_DIMENSIONS", 3)
    @patch("integrations.gemini.embeddings.get_gemini_client")
    def test_generate_embedding_rejects_zero_vector(self, get_client):
        models = Mock()
        models.embed_content.return_value = SimpleNamespace(
            embeddings=[SimpleNamespace(values=[0.0, 0.0, 0.0])]
        )
        get_client.return_value = SimpleNamespace(models=models)

        with self.assertRaisesMessage(EmbeddingError, "zero vector"):
            generate_embedding("Search query: Python")

    @patch("integrations.gemini.embeddings.EMBEDDING_DIMENSIONS", 3)
    @patch("integrations.gemini.embeddings.get_gemini_client")
    def test_generate_embedding_rejects_wrong_dimensions(self, get_client):
        models = Mock()
        models.embed_content.return_value = SimpleNamespace(
            embeddings=[SimpleNamespace(values=[0.1, 0.2])]
        )
        get_client.return_value = SimpleNamespace(models=models)

        with self.assertRaisesMessage(EmbeddingError, "2 chiều"):
            generate_embedding("Python")

    @patch("integrations.gemini.embeddings.EMBEDDING_DIMENSIONS", 3)
    @patch("integrations.gemini.embeddings.get_gemini_client")
    def test_generate_embedding_rejects_non_finite_values(self, get_client):
        for invalid_value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(invalid_value=invalid_value):
                models = Mock()
                models.embed_content.return_value = SimpleNamespace(
                    embeddings=[SimpleNamespace(values=[0.1, invalid_value, 0.3])]
                )
                get_client.return_value = SimpleNamespace(models=models)

                with self.assertRaisesMessage(EmbeddingError, "không hợp lệ"):
                    generate_embedding("Python")
