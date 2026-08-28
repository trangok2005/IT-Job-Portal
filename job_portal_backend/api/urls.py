from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenVerifyView

from apps.accounts.views import ActiveUserTokenRefreshView, GoogleAuthView
from apps.core.views import HealthView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", ActiveUserTokenRefreshView.as_view(), name="token_refresh"),
    path("auth/token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("auth/google/", GoogleAuthView.as_view(), name="google-auth"),
    path("accounts/", include("apps.accounts.urls")),
    path("", include("apps.dashboard.urls")),
    path("candidates/", include("apps.candidates.urls")),
    path("", include("apps.companies.urls")),
    path("", include("apps.skills.urls")),
    path("", include("apps.jobs.urls")),
    path("", include("apps.applications.urls")),
]
