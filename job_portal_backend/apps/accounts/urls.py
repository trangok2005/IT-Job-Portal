from django.urls import path

from apps.accounts.views import (
    AdminUserListView,
    AdminUserLockView,
    AdminUserUnlockView,
    GoogleAuthView,
    MeView,
    RegisterView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("google/", GoogleAuthView.as_view(), name="accounts-google-auth"),
    path("me/", MeView.as_view(), name="me"),
    path("users/", AdminUserListView.as_view(), name="admin-users"),
    path("users/<uuid:user_id>/lock/", AdminUserLockView.as_view(), name="admin-user-lock"),
    path("users/<uuid:user_id>/unlock/", AdminUserUnlockView.as_view(), name="admin-user-unlock"),
]
