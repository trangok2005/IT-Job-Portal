from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("applications", "0005_remove_jobapplication_is_active"),
    ]

    operations = [
        migrations.AlterField(
            model_name="jobapplication",
            name="status",
            field=models.CharField(
                choices=[
                    ("APPLIED", "Chờ xem xét"),
                    ("SHORTLISTED", "Đã qua vòng xem xét"),
                    ("INTERVIEWED", "Phỏng vấn"),
                    ("REJECTED", "Từ chối"),
                    ("HIRED", "Đã tuyển dụng"),
                ],
                default="APPLIED",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="applicationstatushistory",
            name="from_status",
            field=models.CharField(
                blank=True,
                choices=[
                    ("APPLIED", "Chờ xem xét"),
                    ("SHORTLISTED", "Đã qua vòng xem xét"),
                    ("INTERVIEWED", "Phỏng vấn"),
                    ("REJECTED", "Từ chối"),
                    ("HIRED", "Đã tuyển dụng"),
                ],
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="applicationstatushistory",
            name="to_status",
            field=models.CharField(
                choices=[
                    ("APPLIED", "Chờ xem xét"),
                    ("SHORTLISTED", "Đã qua vòng xem xét"),
                    ("INTERVIEWED", "Phỏng vấn"),
                    ("REJECTED", "Từ chối"),
                    ("HIRED", "Đã tuyển dụng"),
                ],
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="applicationstatushistory",
            name="note",
            field=models.TextField(
                blank=True,
                help_text="Ghi chú nội bộ, không hiển thị cho ứng viên.",
            ),
        ),
        migrations.AddField(
            model_name="applicationstatushistory",
            name="candidate_message",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="applicationstatushistory",
            name="notification_attempts",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="applicationstatushistory",
            name="notification_error",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="applicationstatushistory",
            name="notification_sent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="applicationstatushistory",
            name="notification_status",
            field=models.CharField(
                choices=[
                    ("NOT_REQUESTED", "Không yêu cầu"),
                    ("PENDING", "Đang chờ gửi"),
                    ("SENT", "Đã gửi"),
                    ("FAILED", "Gửi thất bại"),
                ],
                default="NOT_REQUESTED",
                max_length=20,
            ),
        ),
    ]
