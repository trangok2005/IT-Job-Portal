import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.core.management import call_command
from django.test import SimpleTestCase
from django.urls import reverse
from qstash.errors import SignatureError

from apps.core import qstash_client


class TaskDispatcherTests(SimpleTestCase):
    def post(self, body):
        return self.client.post(
            reverse("task-dispatcher"),
            data=json.dumps(body),
            content_type="application/json",
            headers={"Upstash-Signature": "signature"},
        )

    @patch("apps.core.task_dispatcher.receiver.verify")
    def test_dispatches_registered_task_with_keyword_payload(self, verify):
        task = Mock()
        with patch.dict(
            "apps.core.task_dispatcher.TASK_REGISTRY",
            {"example": task},
            clear=True,
        ):
            response = self.post({"task": "example", "payload": {"value": 7}})

        self.assertEqual(response.status_code, 200)
        verify.assert_called_once()
        task.assert_called_once_with(value=7)

    @patch(
        "apps.core.task_dispatcher.receiver.verify",
        side_effect=SignatureError("invalid"),
    )
    def test_rejects_invalid_signature_before_dispatch(self, verify):
        task = Mock()
        with patch.dict(
            "apps.core.task_dispatcher.TASK_REGISTRY",
            {"example": task},
            clear=True,
        ):
            response = self.post({"task": "example", "payload": {}})

        self.assertEqual(response.status_code, 401)
        task.assert_not_called()

    @patch("apps.core.task_dispatcher.receiver.verify")
    def test_rejects_unknown_task(self, verify):
        response = self.post({"task": "unknown", "payload": {}})

        self.assertEqual(response.status_code, 489)

    @patch("apps.core.task_dispatcher.receiver.verify")
    def test_returns_500_so_qstash_retries_failed_task(self, verify):
        task = Mock(side_effect=RuntimeError("failed"))
        with patch.dict(
            "apps.core.task_dispatcher.TASK_REGISTRY",
            {"example": task},
            clear=True,
        ):
            response = self.post({"task": "example", "payload": {}})

        self.assertEqual(response.status_code, 500)


class QStashClientTests(SimpleTestCase):
    def test_publish_task_uses_shared_dispatcher_and_delay(self):
        with (
            patch.object(qstash_client, "BACKEND_PUBLIC_URL", "https://api.example"),
            patch.object(
                qstash_client.client.message,
                "publish_json",
            ) as publish_json,
        ):
            qstash_client.publish_task("example", {"value": 7}, delay=30)

        publish_json.assert_called_once_with(
            url="https://api.example/api/internal/tasks/",
            body={"task": "example", "payload": {"value": 7}},
            delay=30,
            retries=5,
        )


class SetupQStashSchedulesTests(SimpleTestCase):
    @patch(
        "apps.core.management.commands.setup_qstash_schedules.dispatcher_url",
        return_value="https://api.example/api/internal/tasks/",
    )
    @patch("apps.core.management.commands.setup_qstash_schedules.client")
    def test_creates_only_missing_schedules(self, client, dispatcher_url):
        client.schedule.list.return_value = [
            SimpleNamespace(schedule_id="job-portal-expire-jobs")
        ]

        call_command("setup_qstash_schedules")

        self.assertEqual(client.schedule.create_json.call_count, 3)
        created_ids = {
            call.kwargs["schedule_id"]
            for call in client.schedule.create_json.call_args_list
        }
        self.assertEqual(
            created_ids,
            {
                "job-portal-cleanup-expired-jd-imports",
                "job-portal-cleanup-expired-resume-imports",
                "job-portal-retry-application-matches",
            },
        )
        for call in client.schedule.create_json.call_args_list:
            self.assertEqual(
                call.kwargs["destination"],
                "https://api.example/api/internal/tasks/",
            )
            self.assertEqual(call.kwargs["method"], "POST")
            self.assertEqual(call.kwargs["body"]["payload"], {})

    @patch(
        "apps.core.management.commands.setup_qstash_schedules.dispatcher_url",
        return_value="https://api.example/api/internal/tasks/",
    )
    @patch("apps.core.management.commands.setup_qstash_schedules.client")
    def test_second_run_does_not_duplicate_schedules(self, client, dispatcher_url):
        client.schedule.list.return_value = [
            SimpleNamespace(schedule_id=schedule_id)
            for schedule_id in (
                "job-portal-expire-jobs",
                "job-portal-retry-application-matches",
                "job-portal-cleanup-expired-jd-imports",
                "job-portal-cleanup-expired-resume-imports",
            )
        ]

        call_command("setup_qstash_schedules")

        client.schedule.create_json.assert_not_called()
