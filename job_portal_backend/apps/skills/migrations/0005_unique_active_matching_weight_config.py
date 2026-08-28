from django.db import migrations, models


def normalize_active_configs(apps, schema_editor):
    config_model = apps.get_model("skills", "MatchingWeightConfig")
    active_ids = list(
        config_model.objects.filter(is_active=True)
        .order_by("-updated_at", "-pk")
        .values_list("pk", flat=True)
    )
    if len(active_ids) > 1:
        config_model.objects.filter(pk__in=active_ids[1:]).update(is_active=False)


class Migration(migrations.Migration):
    dependencies = [
        ("skills", "0004_remove_candidateskill_ai_confidence_and_more"),
    ]

    operations = [
        migrations.RunPython(normalize_active_configs, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="matchingweightconfig",
            constraint=models.UniqueConstraint(
                condition=models.Q(("is_active", True)),
                fields=("is_active",),
                name="unique_active_matching_weight_config",
            ),
        ),
    ]
