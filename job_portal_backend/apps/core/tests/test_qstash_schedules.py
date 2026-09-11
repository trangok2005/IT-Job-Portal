from types import SimpleNamespace
from unittest.mock import patch

from django.core.management import call_command
from django.test import SimpleTestCase


class SetupQStashSchedulesTests(SimpleTestCase):
    @patch(
        "apps.core.management.commands.setup_qstash_schedules.dispatcher_url",
        return_value="https://api.example/api/internal/tasks/",
    )
    @patch("apps.core.management.commands.setup_qstash_schedules.get_qstash_client")
    def test_creates_only_missing_schedules(self, get_client, dispatcher_url):
        client = get_client.return_value
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
    @patch("apps.core.management.commands.setup_qstash_schedules.get_qstash_client")
    def test_second_run_does_not_duplicate_schedules(
        self, get_client, dispatcher_url
    ):
        client = get_client.return_value
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
