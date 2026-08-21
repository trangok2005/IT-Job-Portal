"""Read/query serializers cho notification API."""
from rest_framework import serializers

from apps.notifications.models import Notification


class NotificationReadSerializer(serializers.ModelSerializer):
    """Thông tin in-app an toàn dành cho chính recipient."""

    class Meta:
        model = Notification
        fields = [
            "id",
            "application",
            "notif_type",
            "title",
            "message",
            "payload",
            "is_read",
            "sent_at",
            "created_at",
        ]
        read_only_fields = fields


class NotificationListQuerySerializer(serializers.Serializer):
    """Validate bộ lọc polling notification."""

    unread = serializers.BooleanField(required=False)
    notif_type = serializers.ChoiceField(
        choices=Notification.NotifType.choices,
        required=False,
    )
