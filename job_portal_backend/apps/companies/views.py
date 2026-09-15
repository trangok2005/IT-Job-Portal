from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view

from apps.companies import perms, selectors, serializers, services
from apps.companies.models import Company
from common import permissions as common_permissions


@extend_schema_view(
    list=extend_schema(parameters=[serializers.CompanyListQuerySerializer]),
)
class CompanyViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = serializers.CompanyReadSerializer

    def get_permissions(self):
        if self.action == "me":
            return [IsAuthenticated(), common_permissions.IsEmployer()]
        if self.action == "resubmit":
            return [
                IsAuthenticated(),
                common_permissions.IsEmployer(),
                perms.IsCompanyOwner(),
            ]
        return [IsAuthenticated(), common_permissions.IsAdmin()]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Company.objects.none()
        if self.action == "resubmit":
            # Chỉ cho employer gửi lại hồ sơ công ty của mình.
            return Company.objects.filter(owner=self.request.user)
        status_filter = None
        if self.action == "list":
            query = serializers.CompanyListQuerySerializer(
                data=self.request.query_params
            )
            query.is_valid(raise_exception=True)
            status_filter = query.validated_data.get("status")
        return selectors.get_all_companies(status=status_filter)

    @extend_schema(
        request=serializers.CompanyWriteSerializer,
        responses=serializers.CompanyReadSerializer,
    )
    @action(detail=False, methods=["get", "patch"])
    def me(self, request):
        company = selectors.get_company_for_employer(request.user)
        if company is None:
            raise NotFound("Chưa có hồ sơ công ty.")
        if request.method == "PATCH":
            serializer = serializers.CompanyWriteSerializer(
                company, data=request.data, partial=True
            )
            serializer.is_valid(raise_exception=True)
            company = services.update_company(company, serializer.validated_data)
        return Response(serializers.CompanyReadSerializer(company).data)

    @action(methods=["post"], detail=True)
    def approve(self, request, pk=None):
        company = self.get_object()
        try:
            services.approve_company(company, request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializers.CompanyReadSerializer(company).data)

    @extend_schema(
        request=serializers.CompanyRejectSerializer,
        responses=serializers.CompanyReadSerializer,
    )
    @action(methods=["post"], detail=True)
    def reject(self, request, pk=None):
        company = self.get_object()
        serializer = serializers.CompanyRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            services.reject_company(
                company,
                request.user,
                reason=serializer.validated_data["rejection_reason"],
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializers.CompanyReadSerializer(company).data)

    @action(methods=["post"], detail=True)
    def lock(self, request, pk=None):
        company = self.get_object()
        services.lock_company(company, request.user)
        return Response(serializers.CompanyReadSerializer(company).data)

    @action(methods=["post"], detail=True)
    def resubmit(self, request, pk=None):
        company = self.get_object()
        self.check_object_permissions(request, company)
        try:
            services.resubmit_company(company)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializers.CompanyReadSerializer(company).data)
