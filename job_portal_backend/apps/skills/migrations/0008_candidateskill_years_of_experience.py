from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("skills", "0007_remove_skill_source"),
    ]

    operations = [
        migrations.AddField(
            model_name="candidateskill",
            name="years_of_experience",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
    ]
