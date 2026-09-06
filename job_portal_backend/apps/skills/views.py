"""skills views — ViewSet mỏng: gọi service/selector, trả response.

UC diagram: Admin "Quản trị Skill và tiêu chí phù hợp". List công khai chỉ
trả skill APPROVED + active; admin (role ADMIN) xem toàn bộ + duyệt/gộp.
"""
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.db import transaction
from drf_spectacular.utils import extend_schema, extend_schema_view

from apps.skills import selectors, serializers, services
from apps.skills.models import MatchingWeightConfig, Skill, SkillCategory
from common import permissions as common_permissions


@extend_schema_view(
    list=extend_schema(parameters=[serializers.SkillListQuerySerializer]),
    create=extend_schema(
        request=serializers.SkillWriteSerializer,
        responses={201: serializers.SkillReadSerializer},
    ),
    update=extend_schema(
        request=serializers.SkillWriteSerializer,
        responses=serializers.SkillReadSerializer,
    ),
    partial_update=extend_schema(
        request=serializers.SkillWriteSerializer,
        responses=serializers.SkillReadSerializer,
    ),
)
class SkillViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = serializers.SkillReadSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve", "hot"]:
            return [AllowAny()]
        return [IsAuthenticated(), common_permissions.IsAdmin()]

    def get_queryset(self):
        if self.action == "hot":
            return selectors.get_hot_skills()
        is_admin = self.request.user.is_authenticated and self.request.user.is_admin_role
        if is_admin:
            query = serializers.SkillListQuerySerializer(data=self.request.query_params)
            query.is_valid(raise_exception=True)
            return selectors.get_skills_for_review(
                status=query.validated_data.get("status"),
            )
        return selectors.get_public_skills()

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return serializers.SkillWriteSerializer
        return serializers.SkillReadSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            skill = services.create_skill(
                user=request.user,
                name=serializer.validated_data["name"],
                category=serializer.validated_data.get("category"),
                is_active=serializer.validated_data.get("is_active", True),
                aliases=serializer.validated_data.get("aliases"),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializers.SkillReadSerializer(skill).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        try:
            skill = services.update_skill(
                skill=instance,
                user=request.user,
                name=serializer.validated_data.get("name"),
                category=serializer.validated_data.get("category"),
                is_active=serializer.validated_data.get("is_active"),
                aliases=serializer.validated_data.get("aliases"),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializers.SkillReadSerializer(skill).data)

    @action(methods=["post"], detail=True)
    def approve(self, request, pk=None):
        skill = self.get_object()
        services.approve_skill(skill, request.user)
        return Response(serializers.SkillReadSerializer(skill).data)

    @action(methods=["post"], detail=True)
    def reject(self, request, pk=None):
        skill = self.get_object()
        services.reject_skill(skill, request.user)
        return Response(serializers.SkillReadSerializer(skill).data)

    @extend_schema(
        request=serializers.SkillMergeSerializer,
        responses=serializers.SkillReadSerializer,
    )
    @action(methods=["post"], detail=False)
    def merge(self, request):
        serializer = serializers.SkillMergeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            target = services.merge_skills(
                request.user,
                serializer.validated_data["source_ids"],
                serializer.validated_data["target_id"],
            )
        except (Skill.DoesNotExist, ValueError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializers.SkillReadSerializer(target).data)

    @action(methods=["get"], detail=False)
    def hot(self, request):
        limit = request.query_params.get("limit", 6)
        try:
            limit = int(limit)
        except ValueError:
            limit = 6
        qs = selectors.get_hot_skills(limit=max(1, min(limit, 20)))
        return Response(serializers.SkillHotSerializer(qs, many=True).data)


class SkillCategoryViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = selectors.get_skill_categories()
    serializer_class = serializers.SkillCategorySerializer

    def get_permissions(self):
        if self.action == "list":
            return [AllowAny()]
        return [IsAuthenticated(), common_permissions.IsAdmin()]


class MatchingWeightConfigViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = MatchingWeightConfig.objects.order_by("-updated_at")
    serializer_class = serializers.MatchingWeightConfigSerializer

    def get_permissions(self):
        if self.action == "active":
            return [AllowAny()]
        return [IsAuthenticated(), common_permissions.IsAdmin()]

    @action(methods=["get"], detail=False)
    def active(self, request):
        config = selectors.get_active_weight_config()
        if config is None:
            return Response(
                {"detail": "Chưa có cấu hình trọng số nào."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(serializers.MatchingWeightConfigSerializer(config).data)

    def perform_create(self, serializer):
        serializer.instance = services.create_weight_config(
            self.request.user,
            serializer.validated_data,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        config = services.update_weight_config(
            instance, request.user, serializer.validated_data,
        )
        return Response(serializers.MatchingWeightConfigSerializer(config).data)
