from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from integrations.gemini.client import (
    GeminiConfigurationError,
    get_gemini_client,
)


class GeminiClientTests(SimpleTestCase):
    def tearDown(self):
        get_gemini_client.cache_clear()

    @override_settings(GEMINI_API_KEY="", GEMINI_TIMEOUT_MS=10000)
    def test_missing_api_key_has_clear_configuration_error(self):
        with self.assertRaisesMessage(GeminiConfigurationError, "GEMINI_API_KEY"):
            get_gemini_client()

    @override_settings(GEMINI_API_KEY="test-key", GEMINI_TIMEOUT_MS=1234)
    @patch("google.genai.Client")
    def test_client_is_created_once_with_shared_timeout(self, client_class):
        first = get_gemini_client()
        second = get_gemini_client()

        self.assertIs(first, second)
        client_class.assert_called_once()
        self.assertEqual(
            client_class.call_args.kwargs["http_options"].timeout,
            1234,
        )
