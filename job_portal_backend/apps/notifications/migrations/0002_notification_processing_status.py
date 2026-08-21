from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0001_initial"),
        ("applications", "0002_restrict_submitted_resume"),
    ]

    operations = [
        migrations.AlterField(
            model_name="notification",
            name="status",
            field=models.CharField(
                choices=[
                    ("PENDING", "Chờ gửi"),
                    ("PROCESSING", "Đang gửi"),
                    ("SENT", "Đã gửi"),
                    ("FAILED", "Thất bại"),
                ],
                default="PENDING",
                max_length=20,
            ),
        ),
    ]
