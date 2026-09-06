"""Input/output shapes của API hồ sơ ứng tuyển."""
from django.core.exceptions import ObjectDoesNotExist

from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from apps.applications.models import ApplicationStatusHistory, JobApplication
from apps.ai_analysis.models import ApplicationMatchResult
from apps.candidates.serializers import (
    CandidateSkillSerializer,
    PrivateFileURLSerializer,
    ResumeSerializer,
)
from apps.jobs.models import JobPost


class ApplicationStatusHistorySerializer(serializers.ModelSerializer):
    """Full audit trail for employers; internal notes stay private."""

    changed_by_email = serializers.EmailField(source="changed_by.email", read_only=True)

    class Meta:
        model = ApplicationStatusHistory
        fields = [
            "id",
            "from_status",
            "to_status",
            "changed_by_email",
            "note",
            "candidate_message",
            "notification_status",
            "notification_attempts",
            "notification_error",
            "notification_sent_at",
            "created_at",
        ]
        read_only_fields = fields


class CandidateApplicationStatusHistorySerializer(serializers.ModelSerializer):
    """Candidate-facing history without internal notes or actor email."""

    class Meta:
        model = ApplicationStatusHistory
        fields = [
            "id",
            "from_status",
            "to_status",
            "candidate_message",
            "created_at",
        ]
        read_only_fields = fields


class ApplicationCreateSerializer(serializers.Serializer):
    """Candidate chọn job, thư giới thiệu và có đính kèm CV chính hay không."""

    job = serializers.PrimaryKeyRelatedField(
        queryset=JobPost.objects.all(),
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
    expected_status = serializers.ChoiceField(choices=JobApplication.Status.choices)
    note = serializers.CharField(required=False, allow_blank=True, max_length=5000)
    candidate_message = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=5000,
    )


class CandidateApplicationReadSerializer(serializers.ModelSerializer):
    """Response theo dõi trạng thái dành cho candidate."""

    job_id = serializers.UUIDField(source="job.id", read_only=True)
    job_title = serializers.CharField(source="job.title", read_only=True)
    company_name = serializers.CharField(source="job.company.name", read_only=True)
    submitted_resume = ResumeSerializer(source="resume", read_only=True, allow_null=True)
    history = CandidateApplicationStatusHistorySerializer(
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
            "match_status",
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
            "match_status",
            "match_error",
            "history",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.FloatField(allow_null=True))
    def get_match_score(self, obj):
        """Return null while the application match result is unavailable."""
        try:
            return obj.match_result.match_score
        except ObjectDoesNotExist:
            return None


class ApplicationMatchResultReadSerializer(serializers.ModelSerializer):
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
        model = ApplicationMatchResult
        fields = [
            "match_score",
            "status",
            "semantic_similarity_score",
            "skill_overlap_score",
            "experience_score",
            "education_score",
            "matched_skills",
            "missing_skills",
            "criteria_applicability",
            "original_weights",
            "normalized_weights",
            "missing_information",
            "rule_version",
            "embedding_metadata",
            "weight_config_id",
            "weight_config_name",
            "embedding_model_version",
            "created_at",
            "snapshot_created_at",
        ]
        read_only_fields = fields


class EmptyApplicationMatchResultSerializer(serializers.Serializer):
    """Stable response shape while no match result has been computed."""

    match_score = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)
    status = serializers.CharField(allow_null=True)
    semantic_similarity_score = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)
    skill_overlap_score = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)
    experience_score = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)
    education_score = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)
    matched_skills = serializers.ListField(child=serializers.CharField())
    missing_skills = serializers.ListField(child=serializers.CharField())
    criteria_applicability = serializers.DictField()
    original_weights = serializers.DictField()
    normalized_weights = serializers.DictField()
    missing_information = serializers.DictField()
    rule_version = serializers.CharField(allow_blank=True)
    embedding_metadata = serializers.DictField()
    weight_config_id = serializers.UUIDField(allow_null=True)
    weight_config_name = serializers.CharField(allow_null=True)
    embedding_model_version = serializers.CharField(allow_blank=True)
    created_at = serializers.DateTimeField(allow_null=True)
    snapshot_created_at = serializers.DateTimeField(allow_null=True)
