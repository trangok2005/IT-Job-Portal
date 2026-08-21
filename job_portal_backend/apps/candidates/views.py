"""candidates views — mỏng: lấy dữ liệu, gọi service/selector, trả response.

Không chứa logic nghiệp vụ (xem apps/candidates/services.py, selectors.py, perms.py).
Chỉ cho phép ứng viên thao tác HỒ SƠ CỦA CHÍNH MÌNH (request.user).
"""
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from apps.candidates import perms, selectors, serializers, services
from apps.candidates.models import CandidateProfile, Education, Experience, Resume, ResumeImport
from apps.skills.models import CandidateSkill


def _get_my_profile(user) -> CandidateProfile:
    """Lấy hồ sơ của user hiện tại hoặc trả lỗi API 404 rõ ràng."""
    profile = selectors.get_my_profile(user)
    if profile is None:
        raise NotFound("Chưa có hồ sơ ứng viên.")
    return profile


def _get_own(profile: CandidateProfile, model, pk):
    """Chỉ tìm object con trong phạm vi hồ sơ đang đăng nhập."""
    return get_object_or_404(model.objects.filter(candidate=profile), pk=pk)


class CandidateMeView(APIView):
    permission_classes = [IsAuthenticated, perms.IsCandidate]

    @extend_schema(responses=serializers.CandidateProfileReadSerializer)
    def get(self, request):
        profile = _get_my_profile(request.user)
        data = serializers.CandidateProfileReadSerializer(
            profile, context={"request": request}
        ).data
        return Response(data)

    @extend_schema(
        request=serializers.CandidateProfileUpdateSerializer,
        responses=serializers.CandidateProfileReadSerializer,
    )
    def patch(self, request):
        profile = _get_my_profile(request.user)
        serializer = serializers.CandidateProfileUpdateSerializer(
            profile, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        profile = services.update_profile(profile, serializer.validated_data)
        data = serializers.CandidateProfileReadSerializer(
            profile, context={"request": request}
        ).data
        return Response(data)

    @extend_schema(
        request=serializers.CandidateProfileSaveSerializer,
        responses=serializers.CandidateProfileReadSerializer,
    )
    def put(self, request):
        profile = _get_my_profile(request.user)
        serializer = serializers.CandidateProfileSaveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            services.save_full_profile(profile, dict(serializer.validated_data))
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        profile = selectors.get_my_profile(request.user)
        return Response(
            serializers.CandidateProfileReadSerializer(
                profile, context={"request": request}
            ).data
        )


class CandidateEducationCreateView(APIView):
    permission_classes = [IsAuthenticated, perms.IsCandidate]

    @extend_schema(
        request=serializers.EducationSerializer,
        responses={201: serializers.EducationSerializer},
    )
    def post(self, request):
        profile = _get_my_profile(request.user)
        serializer = serializers.EducationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        education = services.create_education(profile, serializer.validated_data)
        return Response(
            serializers.EducationSerializer(education).data,
            status=status.HTTP_201_CREATED,
        )


class CandidateEducationDetailView(APIView):
    permission_classes = [IsAuthenticated, perms.IsCandidate]

    def _get_education(self, request, pk) -> Education:
        profile = _get_my_profile(request.user)
        return _get_own(profile, Education, pk)

    @extend_schema(
        request=serializers.EducationSerializer,
        responses=serializers.EducationSerializer,
    )
    def patch(self, request, pk):
        education = self._get_education(request, pk)
        serializer = serializers.EducationSerializer(
            education, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        education = services.update_education(education, serializer.validated_data)
        return Response(serializers.EducationSerializer(education).data)

    @extend_schema(responses={204: None})
    def delete(self, request, pk):
        education = self._get_education(request, pk)
        services.delete_education(education)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CandidateExperienceCreateView(APIView):
    permission_classes = [IsAuthenticated, perms.IsCandidate]

    @extend_schema(
        request=serializers.ExperienceSerializer,
        responses={201: serializers.ExperienceSerializer},
    )
    def post(self, request):
        profile = _get_my_profile(request.user)
        serializer = serializers.ExperienceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        experience = services.create_experience(profile, serializer.validated_data)
        return Response(
            serializers.ExperienceSerializer(experience).data,
            status=status.HTTP_201_CREATED,
        )


class CandidateExperienceDetailView(APIView):
    permission_classes = [IsAuthenticated, perms.IsCandidate]

    def _get_experience(self, request, pk) -> Experience:
        profile = _get_my_profile(request.user)
        return _get_own(profile, Experience, pk)

    @extend_schema(
        request=serializers.ExperienceSerializer,
        responses=serializers.ExperienceSerializer,
    )
    def patch(self, request, pk):
        experience = self._get_experience(request, pk)
        serializer = serializers.ExperienceSerializer(
            experience, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        experience = services.update_experience(experience, serializer.validated_data)
        return Response(serializers.ExperienceSerializer(experience).data)

    @extend_schema(responses={204: None})
    def delete(self, request, pk):
        experience = self._get_experience(request, pk)
        services.delete_experience(experience)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CandidateSkillCreateView(APIView):
    permission_classes = [IsAuthenticated, perms.IsCandidate]

    @extend_schema(
        request=serializers.CandidateSkillSerializer,
        responses={201: serializers.CandidateSkillSerializer},
    )
    def post(self, request):
        profile = _get_my_profile(request.user)
        serializer = serializers.CandidateSkillSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            candidate_skill = services.create_candidate_skill(
                profile,
                skill=serializer.validated_data["skill"],
                level=serializer.validated_data.get("level", ""),
                years_of_experience=serializer.validated_data.get(
                    "years_of_experience"
                ),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            serializers.CandidateSkillSerializer(candidate_skill).data,
            status=status.HTTP_201_CREATED,
        )


class CandidateSkillDetailView(APIView):
    permission_classes = [IsAuthenticated, perms.IsCandidate]

    def _get_candidate_skill(self, request, pk) -> CandidateSkill:
        profile = _get_my_profile(request.user)
        return _get_own(profile, CandidateSkill, pk)

    @extend_schema(
        request=serializers.CandidateSkillSerializer,
        responses=serializers.CandidateSkillSerializer,
    )
    def patch(self, request, pk):
        candidate_skill = self._get_candidate_skill(request, pk)
        serializer = serializers.CandidateSkillSerializer(
            candidate_skill, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        try:
            candidate_skill = services.update_candidate_skill(
                candidate_skill, serializer.validated_data
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializers.CandidateSkillSerializer(candidate_skill).data)

    @extend_schema(responses={204: None})
    def delete(self, request, pk):
        candidate_skill = self._get_candidate_skill(request, pk)
        services.delete_candidate_skill(candidate_skill)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CandidateResumeView(APIView):
    permission_classes = [IsAuthenticated, perms.IsCandidate]

    @extend_schema(responses=serializers.ResumeSerializer(many=True))
    def get(self, request):
        profile = _get_my_profile(request.user)
        resumes = selectors.get_resumes(profile)
        return Response(
            serializers.ResumeSerializer(
                resumes, many=True, context={"request": request}
            ).data
        )

    @extend_schema(
        request=serializers.ResumeUploadSerializer,
        responses={201: serializers.ResumeSerializer},
    )
    def post(self, request):
        profile = _get_my_profile(request.user)
        serializer = serializers.ResumeUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        resume = services.upload_resume(
            profile,
            serializer.validated_data["file"],
            is_primary=serializer.validated_data["is_primary"],
        )
        return Response(
            serializers.ResumeSerializer(
                resume, context={"request": request}
            ).data,
            status=status.HTTP_201_CREATED,
        )


class CandidateResumeDetailView(APIView):
    permission_classes = [IsAuthenticated, perms.IsCandidate]

    @extend_schema(responses={204: None})
    def delete(self, request, pk):
        profile = _get_my_profile(request.user)
        resume = _get_own(profile, Resume, pk)
        try:
            services.delete_resume(resume)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SetPrimaryResumeView(APIView):
    permission_classes = [IsAuthenticated, perms.IsCandidate]

    @extend_schema(request=None, responses=serializers.ResumeSerializer)
    def post(self, request, pk):
        profile = _get_my_profile(request.user)
        resume = _get_own(profile, Resume, pk)
        resume = services.set_primary_resume(resume)
        return Response(
            serializers.ResumeSerializer(
                resume, context={"request": request}
            ).data
        )


class CandidateResumeImportView(APIView):
    """Upload CV để AI parse bất đồng bộ (không block UI). Trả về import_id để polling."""

    permission_classes = [IsAuthenticated, perms.IsCandidate]

    @extend_schema(
        request=serializers.ResumeImportUploadSerializer,
        responses={201: serializers.ResumeImportSerializer},
    )
    def post(self, request):
        profile = _get_my_profile(request.user)
        serializer = serializers.ResumeImportUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        resume_import = services.create_resume_import(
            profile, serializer.validated_data["file"]
        )
        return Response(
            serializers.ResumeImportSerializer(
                resume_import, context={"request": request}
            ).data,
            status=status.HTTP_201_CREATED,
        )


class CandidateResumeImportDetailView(APIView):
    """Polling endpoint để kiểm tra trạng thái parse ResumeImport."""

    permission_classes = [IsAuthenticated, perms.IsCandidate]

    @extend_schema(responses=serializers.ResumeImportSerializer)
    def get(self, request, pk):
        profile = _get_my_profile(request.user)
        resume_import = _get_own(profile, ResumeImport, pk)
        return Response(
            serializers.ResumeImportSerializer(
                resume_import, context={"request": request}
            ).data
        )

    @extend_schema(responses={204: None})
    def delete(self, request, pk):
        """Hủy ResumeImport (khi user hủy chỉnh sửa hồ sơ)."""
        profile = _get_my_profile(request.user)
        resume_import = _get_own(profile, ResumeImport, pk)
        if resume_import.parse_status == ResumeImport.ParseStatus.CONSUMED:
            return Response(
                {"detail": "CV này đã được dùng để cập nhật hồ sơ, không thể xóa."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        services.delete_resume_import(resume_import)
        return Response(status=status.HTTP_204_NO_CONTENT)
