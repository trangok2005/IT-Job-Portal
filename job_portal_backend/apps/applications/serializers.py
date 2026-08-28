"""Input/output shapes của API hồ sơ ứng tuyển."""
from django.core.exceptions import ObjectDoesNotExist

from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from apps.applications.models import ApplicationStatusHistory, JobApplication
from apps.ai_analysis.models import AIAnalysis
from apps.candidates.serializers import CandidateSkillSerializer, ResumeSerializer
from apps.jobs.models import JobPost


class ApplicationStatusHistorySerializer(serializers.ModelSerializer):
    """Audit trail chỉ đọc cho candidate và employer."""

    changed_by_email = serializers.EmailField(source="changed_by.email", read_only=True)

    class Meta:
        model = ApplicationStatusHistory
        fields = [
            "id",
            "from_status",
            "to_status",
            "changed_by_email",
            "note",
            "created_at",
        ]
        read_only_fields = fields


class ApplicationCreateSerializer(serializers.Serializer):
    """Candidate chọn job, thư giới thiệu và có đính kèm CV chính hay không."""

    job = serializers.PrimaryKeyRelatedField(
        queryset=JobPost.objects.filter(is_active=True),
    )
    cover_letter = serializers.CharField(required=False, allow_blank=True)
    attach_current_resume = serializers.BooleanField(required=False, default=False)


class ApplicationListQuerySerializer(serializers.Serializer):
    """Validate bộ lọc danh sách applications."""

    job = serializers.UUIDField(required=False)
    status = serializers.ChoiceField(
        choices=JobApplication.Status.choices,
        required=False,
    )
    ordering = serializers.ChoiceField(
        choices=["created_at", "-created_at", "match_score", "-match_score"],
        required=False,
        default="-created_at",
    )


class ApplicationTransitionSerializer(serializers.Serializer):
    """Input chuyển trạng thái; APPLIED không phải trạng thái đích hợp lệ."""

    status = serializers.ChoiceField(
        choices=[
            JobApplication.Status.SHORTLISTED,
            JobApplication.Status.INTERVIEWED,
            JobApplication.Status.REJECTED,
            JobApplication.Status.HIRED,
        ]
    )
    note = serializers.CharField(required=False, allow_blank=True)


class CandidateApplicationReadSerializer(serializers.ModelSerializer):
    """Response theo dõi trạng thái dành cho candidate."""

    job_id = serializers.UUIDField(source="job.id", read_only=True)
    job_title = serializers.CharField(source="job.title", read_only=True)
    company_name = serializers.CharField(source="job.company.name", read_only=True)
    submitted_resume = ResumeSerializer(source="resume", read_only=True, allow_null=True)
    history = ApplicationStatusHistorySerializer(
        source="status_history",
        many=True,
        read_only=True,
    )

    class Meta:
        model = JobApplication
        fields = [
            "id",
            "job_id",
            "job_title",
            "company_name",
            "submitted_resume",
            "cover_letter",
            "status",
            "history",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class EmployerApplicationReadSerializer(serializers.ModelSerializer):
    """Response xử lý hồ sơ dành cho employer/admin, gồm CV và match score."""

    job_id = serializers.UUIDField(source="job.id", read_only=True)
    job_title = serializers.CharField(source="job.title", read_only=True)
    candidate_id = serializers.UUIDField(source="candidate.id", read_only=True)
    candidate_name = serializers.CharField(source="candidate.full_name", read_only=True)
    candidate_email = serializers.EmailField(source="candidate.user.email", read_only=True)
    candidate_phone = serializers.CharField(source="candidate.phone", read_only=True)
    candidate_headline = serializers.CharField(source="candidate.headline", read_only=True)
    candidate_summary = serializers.CharField(source="candidate.summary", read_only=True)
    candidate_skills = CandidateSkillSerializer(
        source="candidate.candidate_skills",
        many=True,
        read_only=True,
    )
    submitted_resume = ResumeSerializer(source="resume", read_only=True, allow_null=True)
    match_score = serializers.SerializerMethodField()
    history = ApplicationStatusHistorySerializer(
        source="status_history",
        many=True,
        read_only=True,
    )

    class Meta:
        model = JobApplication
        fields = [
            "id",
            "job_id",
            "job_title",
            "candidate_id",
            "candidate_name",
            "candidate_email",
            "candidate_phone",
            "candidate_headline",
            "candidate_summary",
            "candidate_skills",
            "submitted_resume",
            "cover_letter",
            "status",
            "match_score",
            "history",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.FloatField(allow_null=True))
    def get_match_score(self, obj):
        """Trả null trong lúc AI analysis chưa tính xong hoặc bị lỗi."""
        try:
            return obj.ai_analysis.match_score
        except ObjectDoesNotExist:
            return None


class ApplicationAnalysisReadSerializer(serializers.ModelSerializer):
    weight_config_id = serializers.SerializerMethodField()
    weight_config_name = serializers.SerializerMethodField()
    snapshot_created_at = serializers.DateTimeField(
        source="application.snapshot_created_at", read_only=True,
    )

    def get_weight_config_id(self, obj):
        snapshot = obj.application.matching_weight_snapshot or {}
        return snapshot.get("config_id")

    def get_weight_config_name(self, obj):
        snapshot = obj.application.matching_weight_snapshot or {}
        return snapshot.get("config_name")

    class Meta:
        model = AIAnalysis
        fields = [
            "match_score",
            "semantic_similarity_score",
            "skill_overlap_score",
            "experience_score",
            "education_score",
            "matched_skills",
            "missing_skills",
            "weight_config_id",
            "weight_config_name",
            "embedding_model_version",
            "candidate_embedding_version",
            "job_embedding_version",
            "computed_at",
            "snapshot_created_at",
        ]
        read_only_fields = fields


class EmptyApplicationAnalysisSerializer(serializers.Serializer):
    """Stable response shape while no AI analysis has been computed."""

    match_score = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)
    semantic_similarity_score = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)
    skill_overlap_score = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)
    experience_score = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)
    education_score = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)
    matched_skills = serializers.ListField(child=serializers.CharField())
    missing_skills = serializers.ListField(child=serializers.CharField())
    weight_config_id = serializers.UUIDField(allow_null=True)
    weight_config_name = serializers.CharField(allow_null=True)
    embedding_model_version = serializers.CharField(allow_blank=True)
    candidate_embedding_version = serializers.IntegerField(allow_null=True)
    job_embedding_version = serializers.IntegerField(allow_null=True)
    computed_at = serializers.DateTimeField(allow_null=True)
    snapshot_created_at = serializers.DateTimeField(allow_null=True)
