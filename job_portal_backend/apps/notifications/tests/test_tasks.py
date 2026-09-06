from unittest.mock import patch

from django.core import mail
from django.test import TestCase

from apps.accounts.models import User
from apps.applications.models import ApplicationStatusHistory, JobApplication
from apps.candidates.models import CandidateProfile
from apps.companies.models import Company
from apps.jobs.models import JobPost
from apps.notifications.tasks import send_application_status_email


class ApplicationStatusEmailTaskTests(TestCase):
    def setUp(self):
        employer = User.objects.create_user(
            username="mail-employer",
            email="mail-employer@example.com",
            password="password123",
            role=User.Role.EMPLOYER,
        )
        company = Company.objects.create(
            owner=employer,
            name="Mail Company",
            status=Company.Status.APPROVED,
        )
        candidate_user = User.objects.create_user(
            username="mail-candidate",
            email="mail-candidate@example.com",
            password="password123",
            role=User.Role.CANDIDATE,
        )
        profile = CandidateProfile.objects.create(
            user=candidate_user,
            full_name="Mail Candidate",
        )
        job = JobPost.objects.create(
            company=company,
            created_by=employer,
            title="Backend Developer",
            description="Build APIs",
            status=JobPost.Status.ACTIVE,
        )
        application = JobApplication.objects.create(
            job=job,
            candidate=profile,
            status=JobApplication.Status.SHORTLISTED,
        )
        self.history = ApplicationStatusHistory.objects.create(
            application=application,
            from_status=JobApplication.Status.APPLIED,
            to_status=JobApplication.Status.SHORTLISTED,
            changed_by=employer,
            candidate_message="Mời bạn theo dõi bước tiếp theo.",
            notification_status=ApplicationStatusHistory.NotificationStatus.PENDING,
        )

    def test_sends_status_email_and_marks_history_sent(self):
        self.assertTrue(send_application_status_email(str(self.history.pk)))

        self.history.refresh_from_db()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["mail-candidate@example.com"])
        self.assertIn("Đã qua vòng xem xét", mail.outbox[0].subject)
        self.assertIn("Mời bạn theo dõi", mail.outbox[0].body)
        self.assertEqual(
            self.history.notification_status,
            ApplicationStatusHistory.NotificationStatus.SENT,
        )
        self.assertEqual(self.history.notification_attempts, 1)
        self.assertIsNotNone(self.history.notification_sent_at)

    @patch(
        "apps.notifications.tasks.send_text_email",
        side_effect=RuntimeError("SMTP down"),
    )
    def test_failure_is_recorded_and_reraised_for_qstash_retry(self, send_email):
        with self.assertRaisesMessage(RuntimeError, "SMTP down"):
            send_application_status_email(str(self.history.pk))

        self.history.refresh_from_db()
        self.assertEqual(
            self.history.notification_status,
            ApplicationStatusHistory.NotificationStatus.FAILED,
        )
        self.assertEqual(self.history.notification_attempts, 1)
        self.assertIn("SMTP down", self.history.notification_error)

    def test_retry_after_success_is_idempotent(self):
        send_application_status_email(str(self.history.pk))
        send_application_status_email(str(self.history.pk))

        self.history.refresh_from_db()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(self.history.notification_attempts, 1)
