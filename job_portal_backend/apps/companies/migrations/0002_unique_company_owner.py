from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("companies", "0001_initial"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="company",
            constraint=models.UniqueConstraint(
                fields=("owner",),
                name="unique_company_owner",
            ),
        ),
    ]
