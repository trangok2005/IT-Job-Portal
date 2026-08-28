from django.db import migrations, models
import pgvector.django.vector


class Migration(migrations.Migration):
    dependencies = [
        ("applications", "0003_remove_applicationstatushistory_is_active_and_more"),
        ("core", "0001_enable_pgvector"),
    ]

    operations = [
        migrations.AddField(
            model_name="jobapplication",
            name="candidate_embedding_snapshot",
            field=pgvector.django.vector.VectorField(
                blank=True, dimensions=768, editable=False, null=True,
            ),
        ),
        migrations.AddField(
            model_name="jobapplication",
            name="job_embedding_snapshot",
            field=pgvector.django.vector.VectorField(
                blank=True, dimensions=768, editable=False, null=True,
            ),
        ),
        migrations.AddField(
            model_name="jobapplication",
            name="job_snapshot",
            field=models.JSONField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name="jobapplication",
            name="matching_weight_snapshot",
            field=models.JSONField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name="jobapplication",
            name="profile_snapshot",
            field=models.JSONField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name="jobapplication",
            name="snapshot_created_at",
            field=models.DateTimeField(blank=True, editable=False, null=True),
        ),
    ]
