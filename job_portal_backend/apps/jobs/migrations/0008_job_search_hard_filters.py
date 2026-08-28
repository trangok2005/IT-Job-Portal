import unicodedata

from django.db import migrations, models


def _plain(value):
    normalized = " ".join(
        "".join(
            char
            for char in unicodedata.normalize("NFD", value or "")
            if unicodedata.category(char) != "Mn"
        ).casefold().split()
    )
    return normalized.replace("đ", "d")


def migrate_job_filters(apps, schema_editor):
    JobPost = apps.get_model("jobs", "JobPost")
    experience_map = {
        "INTERN": "ENTRY",
        "FRESHER": "ENTRY",
        "JUNIOR": "JUNIOR",
        "MIDDLE": "MID_SENIOR",
        "SENIOR": "MID_SENIOR",
        "LEAD": "LEAD",
    }

    for job in JobPost.objects.all().iterator():
        original_job_type = job.job_type
        normalized_location = _plain(job.location)
        if any(value in normalized_location for value in ("ho chi minh", "hcm", "sai gon", "saigon")):
            job.location = "Hồ Chí Minh"
        elif any(value in normalized_location for value in ("ha noi", "hanoi")):
            job.location = "Hà Nội"
        elif "da nang" in normalized_location:
            job.location = "Đà Nẵng"
        else:
            job.location = ""

        job.workplace_type = "REMOTE" if original_job_type == "REMOTE" else "ONSITE"
        if original_job_type in {"REMOTE", "INTERNSHIP"}:
            job.job_type = "FULL_TIME"
        job.experience_level = experience_map.get(job.experience_level, "JUNIOR")
        job.save(
            update_fields=[
                "location",
                "workplace_type",
                "job_type",
                "experience_level",
            ]
        )


class Migration(migrations.Migration):
    dependencies = [("jobs", "0007_jdimport_parse_attempts")]

    operations = [
        migrations.AddField(
            model_name="jobpost",
            name="workplace_type",
            field=models.CharField(
                choices=[
                    ("ONSITE", "Tại văn phòng"),
                    ("HYBRID", "Linh hoạt (Hybrid)"),
                    ("REMOTE", "Từ xa (Remote)"),
                ],
                default="ONSITE",
                max_length=20,
            ),
        ),
        migrations.RunPython(migrate_job_filters, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="jobpost",
            name="experience_level",
            field=models.CharField(
                blank=True,
                choices=[
                    ("ENTRY", "Mới đi làm (Intern / Fresher)"),
                    ("JUNIOR", "Junior (1 - 2 năm)"),
                    ("MID_SENIOR", "Middle - Senior (3+ năm)"),
                    ("LEAD", "Trưởng nhóm / Quản lý"),
                ],
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="jobpost",
            name="job_type",
            field=models.CharField(
                choices=[
                    ("FULL_TIME", "Toàn thời gian"),
                    ("PART_TIME", "Bán thời gian"),
                    ("CONTRACT", "Hợp đồng / Freelance"),
                ],
                default="FULL_TIME",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="jobpost",
            name="location",
            field=models.CharField(
                blank=True,
                choices=[
                    ("Hồ Chí Minh", "Hồ Chí Minh"),
                    ("Hà Nội", "Hà Nội"),
                    ("Đà Nẵng", "Đà Nẵng"),
                ],
                max_length=20,
            ),
        ),
        migrations.AddIndex(
            model_name="jobpost",
            index=models.Index(fields=["workplace_type"], name="job_workplace_idx"),
        ),
        migrations.AddIndex(
            model_name="jobpost",
            index=models.Index(fields=["experience_level"], name="job_experience_idx"),
        ),
        migrations.AddIndex(
            model_name="jobpost",
            index=models.Index(fields=["location"], name="job_location_idx"),
        ),
        migrations.AddIndex(
            model_name="jobpost",
            index=models.Index(fields=["salary_max"], name="job_salary_max_idx"),
        ),
    ]
