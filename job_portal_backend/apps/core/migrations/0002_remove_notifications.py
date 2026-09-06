from django.db import migrations


def remove_notifications(apps, schema_editor):
    schema_editor.execute('DROP TABLE IF EXISTS "notifications"')


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_enable_pgvector"),
    ]

    operations = [
        migrations.RunPython(remove_notifications, migrations.RunPython.noop),
    ]
