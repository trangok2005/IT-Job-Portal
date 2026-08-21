"""API polling và đánh dấu đã đọc cho notification in-app."""
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.notifications import selectors, serializers, services
from apps.notifications.models import Notification


class NotificationViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """Chỉ expose list và read; không có create/update/delete công khai."""

    permission_classes = [IsAuthenticated]
    serializer_class = serializers.NotificationReadSerializer

    def get_queryset(self):
        """Scope queryset theo recipient trước khi tìm notification."""
        if getattr(self, "swagger_fake_view", False):
            return Notification.objects.none()
        query = serializers.NotificationListQuerySerializer(
            data=self.request.query_params
        )
        query.is_valid(raise_exception=True)
        return selectors.get_user_notifications(
            self.request.user,
            unread=(
                query.validated_data.get("unread")
                if "unread" in self.request.query_params
                else None
            ),
            notif_type=query.validated_data.get("notif_type"),
        )

    @action(methods=["post"], detail=True)
    def read(self, request, pk=None):
        """Đánh dấu một notification thuộc user hiện tại là đã đọc."""
        notification = self.get_object()
        services.mark_notification_read(notification, request.user)
        return Response(self.get_serializer(notification).data)
