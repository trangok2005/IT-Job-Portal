import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("companies", "0002_unique_company_owner"),
        ("jobs", "0003_schedule_job_expiration"),
    ]

    operations = [
        migrations.CreateModel(
            name="JDImport",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_active", models.BooleanField(default=True)),
                ("file", models.FileField(upload_to="job_description_imports/%Y/%m/")),
                ("original_filename", models.CharField(max_length=255)),
                ("file_size_bytes", models.PositiveBigIntegerField(blank=True, null=True)),
                ("status", models.CharField(choices=[("PENDING", "Đang chờ"), ("PROCESSING", "Đang phân tích"), ("SUCCESS", "Hoàn tất"), ("FAILED", "Thất bại"), ("CONSUMED", "Đã tạo tin")], default="PENDING", max_length=20)),
                ("raw_extracted_json", models.JSONField(blank=True, null=True)),
                ("parsed_data", models.JSONField(blank=True, null=True)),
                ("error_message", models.TextField(blank=True)),
                ("expires_at", models.DateTimeField()),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="jd_imports", to="companies.company")),
                ("consumed_job", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="source_jd_import", to="jobs.jobpost")),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="jd_imports", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "jd_imports",
                "indexes": [models.Index(fields=["created_by", "status"], name="jd_imports_created_7f3574_idx")],
            },
        ),
    ]
