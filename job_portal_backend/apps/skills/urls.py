from rest_framework.routers import DefaultRouter

from apps.skills.views import (
    MatchingWeightConfigViewSet,
    SkillCategoryViewSet,
    SkillViewSet,
)

router = DefaultRouter()
router.register("skills", SkillViewSet, basename="skills")
router.register("skill-categories", SkillCategoryViewSet, basename="skill-categories")
router.register("weight-configs", MatchingWeightConfigViewSet, basename="weight-configs")

urlpatterns = router.urls