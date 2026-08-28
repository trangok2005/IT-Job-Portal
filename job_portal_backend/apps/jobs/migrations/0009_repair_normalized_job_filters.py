import unicodedata

from django.db import migrations


def _plain(value):
    normalized = " ".join(
        "".join(
            char
            for char in unicodedata.normalize("NFD", value or "")
            if unicodedata.category(char) != "Mn"
        ).casefold().split()
    )
    return normalized.replace("đ", "d")


def repair_normalized_filters(apps, schema_editor):
    JobPost = apps.get_model("jobs", "JobPost")
    for job in JobPost.objects.select_related("company").all().iterator():
        changed = []
        if not job.experience_level:
            job.experience_level = "JUNIOR"
            changed.append("experience_level")
        if not job.location:
            source = _plain(job.company.address)
            if "da nang" in source:
                job.location = "Đà Nẵng"
                changed.append("location")
        if changed:
            job.save(update_fields=changed)


class Migration(migrations.Migration):
    dependencies = [("jobs", "0008_job_search_hard_filters")]

    operations = [
        migrations.RunPython(repair_normalized_filters, migrations.RunPython.noop),
    ]
