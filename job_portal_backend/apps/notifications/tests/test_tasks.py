from unittest.mock import patch

from django.core import mail
from django.test import TestCase

from apps.accounts.models import User
from apps.notifications.models import Notification
from apps.notifications.tasks import send_notification_email


class NotificationEmailTaskTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="notification-email-user",
            email="notification-email@example.com",
            password="password123",
        )
        self.notification = Notification.objects.create(
            recipient=self.user,
            notif_type=Notification.NotifType.APPLICATION_STATUS_CHANGED,
            channel=Notification.Channel.EMAIL,
            title="Application updated",
            message="Your application status changed.",
        )

    def test_send_email_marks_notification_sent(self):
        result = send_notification_email(str(self.notification.id))

        self.assertTrue(result)
        self.notification.refresh_from_db()
        self.assertEqual(self.notification.status, Notification.Status.SENT)
        self.assertIsNotNone(self.notification.sent_at)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user.email])

    @patch("apps.notifications.tasks.schedule_email_retry")
    @patch("apps.notifications.tasks.send_mail", side_effect=RuntimeError("SMTP down"))
    def test_send_failure_is_saved_and_scheduled_for_retry(
        self,
        send_mail,
        schedule_email_retry,
    ):
        result = send_notification_email(str(self.notification.id))

        self.assertFalse(result)
        self.notification.refresh_from_db()
        self.assertEqual(self.notification.status, Notification.Status.FAILED)
        self.assertEqual(self.notification.retry_count, 1)
        self.assertIn("SMTP down", self.notification.error_message)
        schedule_email_retry.assert_called_once()

    def test_sent_notification_is_idempotent(self):
        self.notification.status = Notification.Status.SENT
        self.notification.save()

        result = send_notification_email(str(self.notification.id))

        self.assertFalse(result)
        self.assertEqual(len(mail.outbox), 0)
