from django.db import migrations


def remove_notifications(apps, schema_editor):
    Schedule = apps.get_model("django_q", "Schedule")
    Schedule.objects.filter(func__startswith="apps.notifications.").delete()
    schema_editor.execute('DROP TABLE IF EXISTS "notifications"')


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_enable_pgvector"),
        ("django_q", "0019_alter_task_options_alter_ormq_key_alter_ormq_lock_and_more"),
    ]

    operations = [
        migrations.RunPython(remove_notifications, migrations.RunPython.noop),
    ]
