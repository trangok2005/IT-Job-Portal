from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("candidates", "0012_education_education_valid_date_range_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="resumeimport",
            name="parse_status",
            field=models.CharField(
                choices=[
                    ("PENDING", "Đang xử lý"),
                    ("PROCESSING", "Đang phân tích"),
                    ("SUCCESS", "Thành công"),
                    ("FAILED", "Thất bại"),
                    ("CONSUMED", "Đã dùng để cập nhật hồ sơ"),
                ],
                default="PENDING",
                max_length=20,
            ),
        ),
    ]
