from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings

from integrations.qstash.client import QStashConfigurationError
from integrations.qstash.publisher import dispatcher_url, publish_task


class QStashPublisherTests(SimpleTestCase):
    @override_settings(BACKEND_PUBLIC_URL="https://api.example/")
    def test_dispatcher_url_joins_public_url(self):
        self.assertEqual(
            dispatcher_url(),
            "https://api.example/api/internal/tasks/",
        )

    @override_settings(BACKEND_PUBLIC_URL="")
    def test_dispatcher_url_requires_public_url(self):
        with self.assertRaisesMessage(
            QStashConfigurationError, "BACKEND_PUBLIC_URL"
        ):
            dispatcher_url()

    @override_settings(BACKEND_PUBLIC_URL="https://api.example")
    @patch("integrations.qstash.publisher.get_qstash_client")
    def test_publish_task_sends_default_envelope(self, get_client):
        publish_json = Mock(return_value=SimpleNamespace(message_id="message-1"))
        get_client.return_value = SimpleNamespace(
            message=SimpleNamespace(publish_json=publish_json)
        )

        result = publish_task("example", {"value": 7})

        self.assertEqual(result.message_id, "message-1")
        publish_json.assert_called_once_with(
            url="https://api.example/api/internal/tasks/",
            body={"task": "example", "payload": {"value": 7}},
            delay=None,
            retries=5,
        )

    @override_settings(BACKEND_PUBLIC_URL="https://api.example")
    @patch("integrations.qstash.publisher.get_qstash_client")
    def test_publish_task_forwards_delivery_options(self, get_client):
        publish_json = Mock()
        get_client.return_value = SimpleNamespace(
            message=SimpleNamespace(publish_json=publish_json)
        )

        publish_task(
            "example",
            {"id": "item-id"},
            delay=30,
            retries=3,
            deduplication_id="example-item-id",
        )

        publish_json.assert_called_once_with(
            url="https://api.example/api/internal/tasks/",
            body={"task": "example", "payload": {"id": "item-id"}},
            delay=30,
            retries=3,
            deduplication_id="example-item-id",
        )

    @override_settings(BACKEND_PUBLIC_URL="https://api.example")
    @patch("integrations.qstash.publisher.get_qstash_client")
    def test_publish_task_omits_retries_when_none(self, get_client):
        publish_json = Mock()
        get_client.return_value = SimpleNamespace(
            message=SimpleNamespace(publish_json=publish_json)
        )

        publish_task("example", {}, retries=None)

        self.assertNotIn("retries", publish_json.call_args.kwargs)
        self.assertIsNone(publish_json.call_args.kwargs["delay"])
