from django.db import migrations


def create_default_weight_config(apps, schema_editor):
    MatchingWeightConfig = apps.get_model("skills", "MatchingWeightConfig")
    if MatchingWeightConfig.objects.exists():
        return
    MatchingWeightConfig.objects.create(
        name="Cấu hình mặc định",
        is_active=True,
        weight_semantic_similarity="0.600",
        weight_skill_overlap="0.250",
        weight_experience_match="0.100",
        weight_education_match="0.050",
    )


def remove_default_weight_config(apps, schema_editor):
    MatchingWeightConfig = apps.get_model("skills", "MatchingWeightConfig")
    MatchingWeightConfig.objects.filter(
        name="Cấu hình mặc định", is_active=True
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("skills", "0002_skill_merged_into_skill_reviewed_at_and_more"),
    ]

    operations = [
        migrations.RunPython(
            create_default_weight_config, remove_default_weight_config
        ),
    ]