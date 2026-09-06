"""View dashboard gọn, điều phối theo role."""
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import PolymorphicProxySerializer, extend_schema

from apps.dashboard import selectors, serializers
from apps.jobs import services as job_services
from common import permissions as common_permissions


class DashboardView(APIView):
    permission_classes = [IsAuthenticated, common_permissions.HasBusinessRole]

    @extend_schema(
        responses=PolymorphicProxySerializer(
            component_name="Dashboard",
            serializers=[
                serializers.CandidateDashboardSerializer,
                serializers.EmployerDashboardSerializer,
                serializers.AdminDashboardSerializer,
            ],
            resource_type_field_name=None,
        )
    )
    def get(self, request):
        """Chỉ chọn và serialize dashboard thuộc role hiện tại."""
        if request.user.is_candidate:
            data = selectors.get_candidate_dashboard(request.user)
            profile = data.pop("profile")
            if profile.embedding is None or profile.embedding_is_stale:
                job_services.enqueue_candidate_embedding_robust(profile)
            serializer = serializers.CandidateDashboardSerializer(data)
        elif request.user.is_employer:
            serializer = serializers.EmployerDashboardSerializer(
                selectors.get_employer_dashboard(request.user)
            )
        else:
            serializer = serializers.AdminDashboardSerializer(
                selectors.get_admin_dashboard()
            )
        return Response(serializer.data)
