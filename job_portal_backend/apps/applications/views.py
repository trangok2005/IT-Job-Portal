from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from apps.applications import selectors, serializers, services
from apps.applications.models import JobApplication
from apps.ai_analysis import selectors as match_result_selectors
from common import permissions as common_permissions
from integrations.storage import create_private_file_url


class ApplicationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), common_permissions.IsCandidate()]
        if self.action == "transition":
            return [IsAuthenticated(), common_permissions.IsEmployer()]
        if self.action == "match_result":
            return [IsAuthenticated(), common_permissions.IsEmployerOrAdmin()]
        return [IsAuthenticated(), common_permissions.HasBusinessRole()]

    def get_queryset(self):
        """Scope dữ liệu trước khi DRF tìm object."""
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
        """Ẩn điểm phù hợp khỏi candidate."""
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
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            application = services.apply_to_job(
                request.user,
                serializer.validated_data["job"],
                serializer.validated_data.get("cover_letter", ""),
                serializer.validated_data["attach_current_resume"],
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
        application = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            application = services.transition_application(
                application,
                request.user,
                serializer.validated_data["status"],
                serializer.validated_data.get("note", ""),
                serializer.validated_data.get("candidate_message", ""),
                serializer.validated_data["expected_status"],
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        output = serializers.EmployerApplicationReadSerializer(
            application,
            context=self.get_serializer_context(),
        )
        return Response(output.data)

    @extend_schema(responses=serializers.EmptyApplicationMatchResultSerializer)
    @action(methods=["get"], detail=True, url_path="match-result")
    def match_result(self, request, pk=None):
        application = self.get_object()
        result = match_result_selectors.get_application_match_result(application)
        if result is not None:
            return Response(serializers.ApplicationMatchResultReadSerializer(result).data)
        empty = {
            "match_score": None,
            "status": application.match_status,
            "semantic_similarity_score": None,
            "skill_overlap_score": None,
            "experience_score": None,
            "education_score": None,
            "matched_skills": [],
            "missing_skills": [],
            "criteria_applicability": {},
            "original_weights": application.matching_weight_snapshot or {},
            "normalized_weights": {},
            "missing_information": (
                {"processing": application.match_error} if application.match_error else {}
            ),
            "rule_version": (application.matching_weight_snapshot or {}).get("rule_version", ""),
            "embedding_metadata": {},
            "weight_config_id": None,
            "weight_config_name": None,
            "embedding_model_version": "",
            "created_at": None,
            "snapshot_created_at": application.snapshot_created_at,
        }
        return Response(serializers.EmptyApplicationMatchResultSerializer(empty).data)

    @extend_schema(responses=serializers.PrivateFileURLSerializer)
    @action(methods=["get"], detail=True, url_path="resume-download-url")
    def resume_download_url(self, request, pk=None):
        """Chỉ cấp URL sau khi `get_object` đã kiểm tra phạm vi truy cập."""
        application = self.get_object()
        if application.resume is None:
            raise NotFound("Hồ sơ ứng tuyển không đính kèm CV.")
        data = create_private_file_url(application.resume.file)
        data["url"] = request.build_absolute_uri(data["url"])
        return Response(serializers.PrivateFileURLSerializer(data).data)
