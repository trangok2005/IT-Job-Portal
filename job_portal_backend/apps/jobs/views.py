"""jobs views — ViewSet mỏng: gọi service/selector, trả response.

Không chứa logic nghiệp vụ (xem apps/jobs/services.py, selectors.py, perms.py).
"""
import logging

from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view

from apps.companies.models import Company
from apps.jobs import perms, selectors, serializers, services
from apps.jobs.job_search_service import SearchFilters, search_jobs
from apps.jobs.models import JDImport, JobPost
from common.throttling import (
    JobSearchAnonThrottle,
    JobSearchUserThrottle,
    UploadParseDailyThrottle,
    UploadParseMinuteThrottle,
)


logger = logging.getLogger(__name__)


@extend_schema_view(
    list=extend_schema(parameters=[serializers.JobListQuerySerializer]),
    create=extend_schema(
        request=serializers.JobWriteSerializer,
        responses={201: serializers.JobReadSerializer},
    ),
    update=extend_schema(
        request=serializers.JobWriteSerializer,
        responses=serializers.JobReadSerializer,
    ),
    partial_update=extend_schema(
        request=serializers.JobWriteSerializer,
        responses=serializers.JobReadSerializer,
    ),
)
class JobViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Chỉ expose các endpoint cần thiết theo UC — KHÔNG có destroy.

    Ràng buộc cứng: API dư = sai. Charter không có UC xoá tin tuyển dụng,
    nên không mở `destroy`. Tin đóng/ngừng nhận hồ sơ dùng action `close`.
    """
    serializer_class = serializers.JobReadSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["created_at", "salary_min", "salary_max"]
    ordering = ["-created_at"]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        if self.action in ["create", "parse_jd"]:
            return [IsAuthenticated(), perms.IsApprovedEmployer()]
        if self.action == "jd_import":
            return [IsAuthenticated(), perms.IsEmployer()]
        if self.action in [
            "update",
            "partial_update",
            "publish",
            "close",
            "recommended_candidates",
        ]:
            return [IsAuthenticated(), perms.IsJobOwnerOrAdmin()]
        if self.action == "my_jobs":
            return [IsAuthenticated(), perms.IsEmployer()]
        if self.action == "recommended":
            return [IsAuthenticated(), perms.IsCandidate()]
        return [IsAuthenticated()]

    def get_throttles(self):
        """Throttle có chủ đích theo action:
        - list: tìm kiếm công khai (anon 5/phút, user 10/phút) — UC-03 E3
        - parse_jd: upload JD cho Gemini parse (2/phút, 10/ngày) — UC-02
        """
        if self.action == "list":
            return [JobSearchAnonThrottle(), JobSearchUserThrottle()]
        if self.action == "parse_jd":
            return [UploadParseMinuteThrottle(), UploadParseDailyThrottle()]
        return super().get_throttles()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return JobPost.objects.none()
        if self.action == "list":
            query = serializers.JobListQuerySerializer(data=self.request.query_params)
            query.is_valid(raise_exception=True)
            params = dict(query.validated_data)
            keyword = params.pop("keyword", None)
            result = search_jobs(keyword, SearchFilters(**params))
            self.search_mode = result.mode
            self.search_fallback_used = result.fallback_used
            return result.queryset
        if self.action == "retrieve":
            return selectors.get_job_detail_queryset(self.request.user)
        return selectors.get_manageable_jobs(self.request.user)

    def filter_queryset(self, queryset):
        if self.action == "list" and self.request.query_params.get(
            "keyword", ""
        ).strip():
            return queryset
        return super().filter_queryset(queryset)

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        response["X-Search-Mode"] = getattr(self, "search_mode", "LATEST")
        response["X-Search-Fallback"] = str(
            getattr(self, "search_fallback_used", False)
        ).lower()
        if isinstance(response.data, dict):
            # Cờ trong body để FE đọc dễ hơn header (UC-03 E2).
            response.data["search_mode"] = getattr(self, "search_mode", "LATEST")
            response.data["search_fallback"] = bool(
                getattr(self, "search_fallback_used", False)
            )
        return response

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return serializers.JobWriteSerializer
        if self.action == "my_jobs":
            return serializers.EmployerJobReadSerializer
        if self.action == "recommended":
            return serializers.RecommendedJobSerializer
        if self.action == "recommended_candidates":
            return serializers.RecommendedCandidateSerializer
        return serializers.JobReadSerializer

    def perform_create(self, serializer):
        """Gọi service tạo DRAFT sau khi permission xác nhận công ty hợp lệ."""
        company = Company.objects.get(
            owner=self.request.user,
            status=Company.Status.APPROVED,
        )
        return services.create_job(
            user=self.request.user,
            company=company,
            data={
                key: value
                for key, value in serializer.validated_data.items()
                if key not in ["required_skills", "publish_immediately", "jd_import_id"]
            },
            required_skills=serializer.validated_data.get("required_skills"),
            publish_immediately=serializer.validated_data.get(
                "publish_immediately", False
            ),
            jd_import_id=serializer.validated_data.get("jd_import_id"),
        )

    def create(self, request, *args, **kwargs):
        """Trả read serializer để response gồm company và skill vừa tạo."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            job = self.perform_create(serializer)
        except (Company.DoesNotExist, ValueError) as exc:
            message = str(exc) or "Cần có hồ sơ công ty được duyệt để đăng tin."
            return Response({"detail": message}, status=status.HTTP_400_BAD_REQUEST)
        out = serializers.JobReadSerializer(job, context=self.get_serializer_context())
        return Response(out.data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        """Chuyển toàn bộ mutation sang service và giữ status ngoài input."""
        job = self.get_object()
        services.update_job(
            job,
            data={
                key: value for key, value in serializer.validated_data.items()
                if key not in ["required_skills", "publish_immediately", "jd_import_id"]
            },
            required_skills=serializer.validated_data.get("required_skills"),
        )

    def update(self, request, *args, **kwargs):
        """Cập nhật bằng write serializer nhưng luôn trả response read đầy đủ."""
        partial = kwargs.pop("partial", False)
        job = self.get_object()
        serializer = self.get_serializer(job, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_update(serializer)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        output = serializers.JobReadSerializer(
            job,
            context=self.get_serializer_context(),
        )
        return Response(output.data)

    @extend_schema(responses=serializers.EmployerJobReadSerializer(many=True))
    @action(methods=["get"], detail=False, url_path="my-jobs")
    def my_jobs(self, request):
        """Trả danh sách phân trang các tin thuộc employer hiện tại."""
        qs = selectors.get_employer_jobs(request.user)
        page = self.paginate_queryset(qs)
        if page is not None:
            data = self.get_serializer(page, many=True).data
            return self.get_paginated_response(data)
        return Response(self.get_serializer(qs, many=True).data)

    @extend_schema(
        request=serializers.JobDescriptionUploadSerializer,
        responses={202: serializers.JDImportSerializer},
    )
    @action(
        methods=["post"],
        detail=False,
        url_path="parse-jd",
        parser_classes=[MultiPartParser],
    )
    def parse_jd(self, request):
        """Persist a temporary JD import and enqueue Gemini parsing."""
        upload = serializers.JobDescriptionUploadSerializer(data=request.data)
        upload.is_valid(raise_exception=True)
        try:
            company = Company.objects.get(
                owner=request.user,
                status=Company.Status.APPROVED,
            )
            jd_import = services.create_jd_import(
                request.user,
                company,
                upload.validated_data["file"],
            )
        except Exception as exc:
            logger.exception(
                "JD parsing failed for %s (%s)",
                upload.validated_data["file"].name,
                type(exc).__name__,
            )
            return Response(
                {
                    "detail": (
                        "Không thể đọc thông tin từ file JD. "
                        f"Mã lỗi: {type(exc).__name__}."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            serializers.JDImportSerializer(jd_import).data,
            status=status.HTTP_202_ACCEPTED,
        )

    @extend_schema(responses={200: serializers.JDImportSerializer, 204: None})
    @action(
        methods=["get", "delete"],
        detail=False,
        url_path=r"jd-imports/(?P<import_id>[^/.]+)",
    )
    def jd_import(self, request, import_id=None):
        jd_import = JDImport.objects.filter(
            pk=import_id, created_by=request.user
        ).first()
        if jd_import is None:
            from rest_framework.exceptions import NotFound

            raise NotFound("Không tìm thấy JD import.")
        if request.method == "DELETE":
            try:
                services.cancel_jd_import(jd_import)
            except ValueError as exc:
                return Response(
                    {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
                )
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(serializers.JDImportSerializer(jd_import).data)

    @extend_schema(responses=serializers.RecommendedJobSerializer(many=True))
    @action(methods=["get"], detail=False)
    def recommended(self, request):
        """Rank eligible jobs for the candidate and tolerate unavailable AI."""
        profile = request.user.candidate_profile
        if profile.embedding is None or profile.embedding_is_stale:
            services.enqueue_candidate_embedding_robust(profile)
        qs = selectors.get_recommended_jobs(profile)
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(self.get_serializer(page, many=True).data)
        return Response(self.get_serializer(qs, many=True).data)

    @extend_schema(responses=serializers.RecommendedCandidateSerializer(many=True))
    @action(methods=["get"], detail=True, url_path="recommended-candidates")
    def recommended_candidates(self, request, pk=None):
        """Return safe public candidate summaries ranked for an owned job."""
        job = self.get_object()
        self.check_object_permissions(request, job)
        if job.embedding is None or job.embedding_is_stale:
            services.enqueue_job_embedding_robust(job)
        qs = selectors.get_recommended_candidates(job)
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(self.get_serializer(page, many=True).data)
        return Response(self.get_serializer(qs, many=True).data)

    @extend_schema(request=None, responses=serializers.JobReadSerializer)
    @action(methods=["post"], detail=True)
    def publish(self, request, pk=None):
        """Chuyển tin DRAFT sang ACTIVE qua state rule trong service."""
        job = self.get_object()
        self.check_object_permissions(request, job)
        try:
            services.publish_job(job)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(job).data)

    @extend_schema(request=None, responses=serializers.JobReadSerializer)
    @action(methods=["post"], detail=True)
    def close(self, request, pk=None):
        """Đóng tin ACTIVE qua state rule trong service."""
        job = self.get_object()
        self.check_object_permissions(request, job)
        try:
            services.close_job(job)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(job).data)
