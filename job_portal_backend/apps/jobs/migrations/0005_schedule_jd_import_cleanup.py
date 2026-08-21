from django.db import migrations


SCHEDULE_NAME = "Cleanup expired JD imports"


def create_schedule(apps, schema_editor):
    Schedule = apps.get_model("django_q", "Schedule")
    Schedule.objects.update_or_create(
        name=SCHEDULE_NAME,
        defaults={
            "func": "apps.jobs.tasks.cleanup_expired_jd_imports",
            "schedule_type": "I",
            "minutes": 60,
            "repeats": -1,
        },
    )


def remove_schedule(apps, schema_editor):
    apps.get_model("django_q", "Schedule").objects.filter(name=SCHEDULE_NAME).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("django_q", "0019_alter_task_options_alter_ormq_key_alter_ormq_lock_and_more"),
        ("jobs", "0004_jdimport"),
    ]
    operations = [migrations.RunPython(create_schedule, remove_schedule)]
