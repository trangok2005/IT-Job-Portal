"""Read-only queries cho notification của user hiện tại."""
from apps.notifications.models import Notification


def get_user_notifications(user, unread=None, notif_type=None):
    """Chỉ trả notification in-app thuộc user, mới nhất trước."""
    qs = Notification.objects.filter(
        recipient=user,
        channel=Notification.Channel.IN_APP,
        is_active=True,
    ).select_related("application")
    if unread is not None:
        qs = qs.filter(is_read=not unread)
    if notif_type:
        qs = qs.filter(notif_type=notif_type)
    return qs.order_by("-created_at")
