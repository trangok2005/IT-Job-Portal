"""ViewSet mỏng cho UC ứng tuyển và xử lý hồ sơ ứng tuyển."""
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from apps.applications import perms, selectors, serializers, services
from apps.applications.models import JobApplication
from apps.ai_analysis import selectors as analysis_selectors


class ApplicationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """Chỉ expose list/create/retrieve/status; không cho sửa hoặc xóa hồ sơ."""

    def get_permissions(self):
        """Phân quyền theo action và role nghiệp vụ."""
        if self.action == "create":
            return [IsAuthenticated(), perms.IsCandidate()]
        if self.action in ["transition", "analysis"]:
            return [IsAuthenticated(), perms.IsEmployerOrAdmin()]
        return [IsAuthenticated(), perms.CanAccessApplications()]

    def get_queryset(self):
        """Giới hạn dữ liệu theo role trước khi DRF tìm object."""
        if getattr(self, "swagger_fake_view", False):
            return JobApplication.objects.none()
        if self.action == "list":
            query = serializers.ApplicationListQuerySerializer(
                data=self.request.query_params
            )
            query.is_valid(raise_exception=True)
            return selectors.get_applications_for_user(
                self.request.user,
                job_id=query.validated_data.get("job"),
                status=query.validated_data.get("status"),
                ordering=query.validated_data["ordering"],
            )
        return selectors.get_application_detail_queryset(self.request.user)

    def get_serializer_class(self):
        """Dùng input serializer riêng và ẩn match score khỏi candidate."""
        if self.action == "create":
            return serializers.ApplicationCreateSerializer
        if self.action == "transition":
            return serializers.ApplicationTransitionSerializer
        if getattr(self, "swagger_fake_view", False):
            return serializers.CandidateApplicationReadSerializer
        if self.request.user.is_employer or self.request.user.is_admin_role:
            return serializers.EmployerApplicationReadSerializer
        return serializers.CandidateApplicationReadSerializer

    @extend_schema(
        request=serializers.ApplicationCreateSerializer,
        responses={201: serializers.CandidateApplicationReadSerializer},
    )
    def create(self, request, *args, **kwargs):
        """Nộp hồ sơ qua service và trả snapshot CV/trạng thái vừa tạo."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            application = services.apply_to_job(
                request.user,
                serializer.validated_data["job"],
                serializer.validated_data.get("cover_letter", ""),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        output = serializers.CandidateApplicationReadSerializer(
            application,
            context=self.get_serializer_context(),
        )
        return Response(output.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        request=serializers.ApplicationTransitionSerializer,
        responses=serializers.EmployerApplicationReadSerializer,
    )
    @action(methods=["post"], detail=True, url_path="status")
    def transition(self, request, pk=None):
        """Chuyển trạng thái bằng state machine và trả hồ sơ đã cập nhật."""
        application = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            application = services.transition_application(
                application,
                request.user,
                serializer.validated_data["status"],
                serializer.validated_data.get("note", ""),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        output = serializers.EmployerApplicationReadSerializer(
            application,
            context=self.get_serializer_context(),
        )
        return Response(output.data)

    @extend_schema(responses=serializers.EmptyApplicationAnalysisSerializer)
    @action(methods=["get"], detail=True)
    def analysis(self, request, pk=None):
        """Return explainable AI details only to the job owner or an admin."""
        application = self.get_object()
        analysis = analysis_selectors.get_application_analysis(application)
        if analysis is not None:
            return Response(serializers.ApplicationAnalysisReadSerializer(analysis).data)
        empty = {
            "match_score": None,
            "semantic_similarity_score": None,
            "skill_overlap_score": None,
            "experience_score": None,
            "education_score": None,
            "matched_skills": [],
            "missing_skills": [],
            "weight_config_id": None,
            "weight_config_name": None,
            "embedding_model_version": "",
            "candidate_embedding_version": None,
            "job_embedding_version": None,
            "computed_at": None,
            "inputs_are_stale": None,
        }
        return Response(serializers.EmptyApplicationAnalysisSerializer(empty).data)
