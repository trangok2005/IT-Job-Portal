from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.notifications.models import Notification


class NotificationApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="notification-api-user",
            email="notification-api@example.com",
            password="password123",
        )
        self.other = User.objects.create_user(
            username="notification-other-user",
            email="notification-other@example.com",
            password="password123",
        )
        self.notification = Notification.objects.create(
            recipient=self.user,
            notif_type=Notification.NotifType.APPLICATION_STATUS_CHANGED,
            channel=Notification.Channel.IN_APP,
            status=Notification.Status.SENT,
            title="Status changed",
        )
        Notification.objects.create(
            recipient=self.user,
            notif_type=Notification.NotifType.APPLICATION_STATUS_CHANGED,
            channel=Notification.Channel.EMAIL,
            title="Email copy",
        )
        self.other_notification = Notification.objects.create(
            recipient=self.other,
            notif_type=Notification.NotifType.APPLICATION_RECEIVED,
            channel=Notification.Channel.IN_APP,
            status=Notification.Status.SENT,
            title="Other user notification",
        )
        self.client.force_authenticate(self.user)

    def test_list_only_returns_current_users_in_app_notifications(self):
        response = self.client.get(reverse("notifications-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], str(self.notification.id))

    def test_unread_filter_and_mark_read(self):
        unread_response = self.client.get(
            reverse("notifications-list"),
            {"unread": "true"},
        )
        read_response = self.client.post(
            reverse("notifications-read", args=[self.notification.id])
        )

        self.assertEqual(unread_response.data["count"], 1)
        self.assertEqual(read_response.status_code, status.HTTP_200_OK)
        self.assertTrue(read_response.data["is_read"])

    def test_cannot_mark_another_users_notification_read(self):
        response = self.client.post(
            reverse("notifications-read", args=[self.other_notification.id])
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
