import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("applications", "0001_initial"),
        ("candidates", "0002_unique_primary_resume"),
        ("jobs", "0003_schedule_job_expiration"),
    ]

    operations = [
        migrations.AlterField(
            model_name="jobapplication",
            name="resume",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.RESTRICT,
                related_name="applications",
                to="candidates.resume",
            ),
        ),
    ]
