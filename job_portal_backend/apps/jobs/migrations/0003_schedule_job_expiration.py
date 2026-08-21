from django.db import migrations


SCHEDULE_NAME = "Expire outdated job posts"


def create_expiration_schedule(apps, schema_editor):
    """Register the recurring Django-Q task that expires outdated jobs."""
    Schedule = apps.get_model("django_q", "Schedule")
    Schedule.objects.update_or_create(
        name=SCHEDULE_NAME,
        defaults={
            "func": "apps.jobs.tasks.expire_jobs",
            "schedule_type": "I",
            "minutes": 5,
            "repeats": -1,
        },
    )


def remove_expiration_schedule(apps, schema_editor):
    """Remove only the schedule created by this migration."""
    Schedule = apps.get_model("django_q", "Schedule")
    Schedule.objects.filter(name=SCHEDULE_NAME).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("django_q", "0019_alter_task_options_alter_ormq_key_alter_ormq_lock_and_more"),
        ("jobs", "0002_job_embedding_version"),
    ]

    operations = [
        migrations.RunPython(create_expiration_schedule, remove_expiration_schedule),
    ]
