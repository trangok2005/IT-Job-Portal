from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ai_analysis", "0001_initial"),
        ("applications", "0002_restrict_submitted_resume"),
    ]

    operations = [
        migrations.AddField(
            model_name="aianalysis",
            name="candidate_embedding_version",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="aianalysis",
            name="job_embedding_version",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
