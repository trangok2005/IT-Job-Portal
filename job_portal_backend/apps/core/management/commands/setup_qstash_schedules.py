"""Tạo các QStash schedule định kỳ.

Chạy lệnh này một lần sau mỗi lần deploy. Không được chạy từ luồng
request-response. Các schedule ID hiện có được giữ nguyên.
"""
from django.core.management.base import BaseCommand

from integrations.qstash.client import get_qstash_client
from integrations.qstash.publisher import dispatcher_url


SCHEDULES = (
    ("job-portal-expire-jobs", "expire_jobs", "*/5 * * * *"),
    (
        "job-portal-retry-application-matches",
        "retry_incomplete_application_matches",
        "*/5 * * * *",
    ),
    (
        "job-portal-cleanup-expired-jd-imports",
        "cleanup_expired_jd_imports",
        "0 * * * *",
    ),
    (
        "job-portal-cleanup-expired-resume-imports",
        "cleanup_expired_resume_imports",
        "0 * * * *",
    ),
)


class Command(BaseCommand):
    help = "Create missing recurring QStash schedules after deployment."

    def handle(self, *args, **options):
        client = get_qstash_client()
        existing_ids = {
            schedule.schedule_id for schedule in client.schedule.list()
        }
        destination = dispatcher_url()

        for schedule_id, task_name, cron in SCHEDULES:
            if schedule_id in existing_ids:
                self.stdout.write(f"Schedule {schedule_id} already exists; skipped.")
                continue

            client.schedule.create_json(
                destination=destination,
                cron=cron,
                body={"task": task_name, "payload": {}},
                method="POST",
                schedule_id=schedule_id,
            )
            self.stdout.write(self.style.SUCCESS(f"Created schedule {schedule_id}."))
