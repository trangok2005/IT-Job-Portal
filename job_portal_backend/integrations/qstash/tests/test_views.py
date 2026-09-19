from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from django.urls import reverse
from qstash.errors import SignatureError

from apps.core.background_tasks.dispatcher import (
    InvalidTaskPayloadError,
    UnknownTaskError,
)


class QStashWebhookTests(SimpleTestCase):
    def post_raw(self, body: bytes):
        return self.client.post(
            reverse("task-dispatcher"),
            data=body,
            content_type="application/json",
            headers={"Upstash-Signature": "signature"},
        )

    @patch(
        "integrations.qstash.views.dispatcher_url",
        return_value="https://api.example/api/internal/tasks/",
    )
    @patch("integrations.qstash.views.dispatch_task")
    @patch("integrations.qstash.views.get_qstash_receiver")
    def test_valid_signature_dispatches_raw_body(
        self, get_receiver, dispatch_task, dispatcher_url
    ):
        receiver = Mock()
        get_receiver.return_value = receiver
        body = b'{"task":"example","payload":{"value":7}}'

        response = self.post_raw(body)

        self.assertEqual(response.status_code, 200)
        receiver.verify.assert_called_once_with(
            signature="signature",
            body=body.decode("utf-8"),
            url="https://api.example/api/internal/tasks/",
        )
        dispatch_task.assert_called_once_with("example", {"value": 7})

    @patch("integrations.qstash.views.dispatcher_url", return_value="https://callback")
    @patch("integrations.qstash.views.dispatch_task")
    @patch("integrations.qstash.views.get_qstash_receiver")
    def test_invalid_signature_returns_401(
        self, get_receiver, dispatch_task, dispatcher_url
    ):
        get_receiver.return_value.verify.side_effect = SignatureError("invalid")

        response = self.post_raw(b'{"task":"example","payload":{}}')

        self.assertEqual(response.status_code, 401)
        dispatch_task.assert_not_called()

    @patch("integrations.qstash.views.dispatcher_url", return_value="https://callback")
    @patch("integrations.qstash.views.get_qstash_receiver")
    def test_invalid_json_returns_489(self, get_receiver, dispatcher_url):
        response = self.post_raw(b"{invalid")

        self.assertEqual(response.status_code, 489)

    @patch("integrations.qstash.views.dispatcher_url", return_value="https://callback")
    @patch("integrations.qstash.views.dispatch_task")
    @patch("integrations.qstash.views.get_qstash_receiver")
    def test_unknown_task_returns_489(
        self, get_receiver, dispatch_task, dispatcher_url
    ):
        dispatch_task.side_effect = UnknownTaskError("Unknown task.")

        response = self.post_raw(b'{"task":"unknown","payload":{}}')

        self.assertEqual(response.status_code, 489)

    @patch("integrations.qstash.views.dispatcher_url", return_value="https://callback")
    @patch("integrations.qstash.views.dispatch_task")
    @patch("integrations.qstash.views.get_qstash_receiver")
    def test_invalid_payload_returns_489(
        self, get_receiver, dispatch_task, dispatcher_url
    ):
        dispatch_task.side_effect = InvalidTaskPayloadError(
            "Task payload must be an object."
        )

        response = self.post_raw(b'{"task":"example","payload":[]}')

        self.assertEqual(response.status_code, 489)

    @patch("integrations.qstash.views.dispatcher_url", return_value="https://callback")
    @patch("integrations.qstash.views.get_qstash_receiver")
    def test_parameter_mismatch_returns_489_without_running_task(
        self, get_receiver, dispatcher_url
    ):
        task = Mock()

        def registered_task(required_value):
            task(required_value=required_value)

        with patch.dict(
            "apps.core.background_tasks.dispatcher.TASK_REGISTRY",
            {"example": registered_task},
            clear=True,
        ):
            missing = self.post_raw(b'{"task":"example","payload":{}}')
            extra = self.post_raw(
                b'{"task":"example","payload":{"required_value":1,"extra":2}}'
            )

        self.assertEqual(missing.status_code, 489)
        self.assertEqual(extra.status_code, 489)
        task.assert_not_called()

    @patch("integrations.qstash.views.dispatcher_url", return_value="https://callback")
    @patch("integrations.qstash.views.dispatch_task")
    @patch("integrations.qstash.views.get_qstash_receiver")
    def test_task_failure_returns_500_for_retry(
        self, get_receiver, dispatch_task, dispatcher_url
    ):
        dispatch_task.side_effect = RuntimeError("temporary failure")

        response = self.post_raw(b'{"task":"example","payload":{}}')

        self.assertEqual(response.status_code, 500)

    def test_non_post_method_returns_405(self):
        response = self.client.get(reverse("task-dispatcher"))

        self.assertEqual(response.status_code, 405)
