from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("jobs", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="jobpost",
            name="content_version",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name="jobpost",
            name="embedding_version",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
