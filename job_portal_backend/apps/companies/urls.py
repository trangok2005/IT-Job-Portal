from rest_framework.routers import DefaultRouter

from apps.companies.views import CompanyViewSet

router = DefaultRouter()
router.register("companies", CompanyViewSet, basename="companies")

urlpatterns = router.urls