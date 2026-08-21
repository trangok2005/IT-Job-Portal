from django.db import migrations, models
from django.db.models import Q


def normalize_primary_resumes(apps, schema_editor):
    """Keep the newest primary resume before adding the unique constraint."""
    Resume = apps.get_model("candidates", "Resume")
    duplicate_candidate_ids = (
        Resume.objects.filter(is_primary=True)
        .values_list("candidate_id", flat=True)
        .order_by()
        .distinct()
    )
    for candidate_id in duplicate_candidate_ids:
        primary_resumes = Resume.objects.filter(
            candidate_id=candidate_id,
            is_primary=True,
        ).order_by("-created_at")
        keep_id = primary_resumes.values_list("id", flat=True).first()
        primary_resumes.exclude(id=keep_id).update(is_primary=False)


class Migration(migrations.Migration):
    dependencies = [
        ("candidates", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(normalize_primary_resumes, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="resume",
            constraint=models.UniqueConstraint(
                fields=("candidate",),
                condition=Q(is_primary=True),
                name="unique_primary_resume_per_candidate",
            ),
        ),
    ]
