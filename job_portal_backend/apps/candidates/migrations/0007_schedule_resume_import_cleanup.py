from django.db import migrations


SCHEDULE_NAME = "Purge expired resume imports"


def create_cleanup_schedule(apps, schema_editor):
    """Register the recurring Django-Q task deleting stale ResumeImport rows."""
    Schedule = apps.get_model("django_q", "Schedule")
    Schedule.objects.update_or_create(
        name=SCHEDULE_NAME,
        defaults={
            "func": "apps.candidates.tasks.cleanup_expired_resume_imports",
            "schedule_type": "I",
            "minutes": 60,
            "repeats": -1,
        },
    )


def remove_cleanup_schedule(apps, schema_editor):
    Schedule = apps.get_model("django_q", "Schedule")
    Schedule.objects.filter(name=SCHEDULE_NAME).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("django_q", "0019_alter_task_options_alter_ormq_key_alter_ormq_lock_and_more"),
        ("candidates", "0006_resumeimport"),
    ]

    operations = [
        migrations.RunPython(create_cleanup_schedule, remove_cleanup_schedule),
    ]
