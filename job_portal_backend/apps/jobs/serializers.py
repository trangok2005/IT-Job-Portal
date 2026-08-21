"""jobs serializers — only shape input/output, no business logic."""
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from apps.jobs.models import JDImport, JobPost, JobSkill
from apps.skills.models import Skill


class JobSkillSerializer(serializers.ModelSerializer):
    skill_name = serializers.CharField(source="skill.name", read_only=True)

    class Meta:
        model = JobSkill
        fields = ["id", "skill", "skill_name", "is_required", "weight", "min_years"]
        read_only_fields = fields


class JobReadSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)
    skills = JobSkillSerializer(source="job_skills", many=True, read_only=True)
    match_score = serializers.SerializerMethodField()
    embedding_is_stale = serializers.BooleanField(read_only=True)

    @extend_schema_field(serializers.FloatField(allow_null=True))
    def get_match_score(self, obj):
        return getattr(obj, "match_score", None)

    class Meta:
        model = JobPost
        fields = [
            "id",
            "title",
            "description",
            "requirements",
            "benefits",
            "location",
            "job_type",
            "experience_level",
            "salary_min",
            "salary_max",
            "salary_negotiable",
            "status",
            "published_at",
            "expires_at",
            "view_count",
            "embedding_is_stale",
            "match_score",
            "company_name",
            "skills",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class EmployerJobReadSerializer(JobReadSerializer):
    application_count = serializers.IntegerField(read_only=True)

    class Meta(JobReadSerializer.Meta):
        fields = [*JobReadSerializer.Meta.fields, "application_count"]
        read_only_fields = fields


class RecommendedJobSerializer(JobReadSerializer):
    class Meta(JobReadSerializer.Meta):
        fields = JobReadSerializer.Meta.fields
        read_only_fields = fields


class RecommendedCandidateSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    headline = serializers.CharField(read_only=True)
    desired_position = serializers.CharField(read_only=True)
    skills = serializers.SerializerMethodField()
    match_score = serializers.FloatField(read_only=True, allow_null=True)

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_skills(self, obj):
        """Return only safe canonical skill names from the prefetched profile."""
        return [link.skill.name for link in obj.candidate_skills.all()]


class JobWriteSerializer(serializers.ModelSerializer):
    """Employer-created fields. ``status`` is managed via service layer."""

    required_skills = serializers.PrimaryKeyRelatedField(
        queryset=Skill.objects.filter(status=Skill.Status.APPROVED, is_active=True),
        many=True,
        required=False,
        write_only=True,
    )
    raw_jd_file = serializers.FileField(write_only=True, required=False)
    publish_immediately = serializers.BooleanField(
        write_only=True,
        required=False,
        default=False,
    )
    jd_import_id = serializers.UUIDField(write_only=True, required=False)

    class Meta:
        model = JobPost
        fields = [
            "title",
            "description",
            "requirements",
            "benefits",
            "location",
            "job_type",
            "experience_level",
            "salary_min",
            "salary_max",
            "salary_negotiable",
            "expires_at",
            "required_skills",
            "raw_jd_file",
            "publish_immediately",
            "jd_import_id",
        ]

    def validate_raw_jd_file(self, file):
        return validate_jd_file(file)

    def validate(self, attrs):
        """Kiểm tra lương/ngày hết hạn bằng cả giá trị cũ khi PATCH."""
        salary_min = attrs.get("salary_min", getattr(self.instance, "salary_min", None))
        salary_max = attrs.get("salary_max", getattr(self.instance, "salary_max", None))
        if salary_min is not None and salary_max is not None and salary_min > salary_max:
            raise serializers.ValidationError({"salary_max": "Phải lớn hơn hoặc bằng salary_min."})

        expires_at = attrs.get("expires_at")
        if expires_at is not None and expires_at <= timezone.now():
            raise serializers.ValidationError(
                {"expires_at": "Thời hạn nhận hồ sơ phải ở tương lai."}
            )

        required_skills = attrs.get("required_skills")
        if required_skills is not None:
            skill_ids = [skill.pk for skill in required_skills]
            if len(skill_ids) != len(set(skill_ids)):
                raise serializers.ValidationError(
                    {"required_skills": "Danh sách kỹ năng không được trùng lặp."}
                )
        return attrs


def validate_jd_file(file):
    suffix = Path(file.name).suffix.lower()
    if suffix not in {".pdf", ".doc", ".docx"}:
        raise serializers.ValidationError("JD chỉ hỗ trợ file PDF, DOC hoặc DOCX.")
    if file.size > settings.MAX_JD_SIZE_BYTES:
        max_size_mb = settings.MAX_JD_SIZE_BYTES // (1024 * 1024)
        raise serializers.ValidationError(
            f"Dung lượng JD không được vượt quá {max_size_mb} MB."
        )
    return file


class JobDescriptionUploadSerializer(serializers.Serializer):
    file = serializers.FileField(write_only=True)

    def validate_file(self, file):
        return validate_jd_file(file)


class JobDescriptionParsedDataSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, allow_blank=True, max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    requirements = serializers.CharField(required=False, allow_blank=True)
    benefits = serializers.CharField(required=False, allow_blank=True)
    location = serializers.CharField(required=False, allow_blank=True, max_length=255)
    job_type = serializers.ChoiceField(
        choices=JobPost.JobType.choices,
        required=False,
        default=JobPost.JobType.FULL_TIME,
    )
    experience_level = serializers.ChoiceField(
        choices=JobPost.ExperienceLevel.choices,
        required=False,
        allow_blank=True,
    )
    salary_min = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    salary_max = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    salary_negotiable = serializers.BooleanField(required=False, default=False)
    expires_at = serializers.DateTimeField(required=False, allow_null=True)
    skills = serializers.ListField(
        child=serializers.CharField(max_length=150),
        required=False,
    )

    def validate(self, attrs):
        salary_min = attrs.get("salary_min")
        salary_max = attrs.get("salary_max")
        if salary_min is not None and salary_max is not None and salary_min > salary_max:
            raise serializers.ValidationError(
                {"salary_max": "Phải lớn hơn hoặc bằng salary_min."}
            )
        expires_at = attrs.get("expires_at")
        if expires_at is not None and expires_at <= timezone.now():
            attrs["expires_at"] = None
        return attrs


class JobDescriptionParseResultSerializer(JobDescriptionParsedDataSerializer):
    required_skills = serializers.ListField(
        child=serializers.UUIDField(),
        read_only=True,
    )
    unmatched_skills = serializers.ListField(
        child=serializers.CharField(),
        read_only=True,
    )


class JDImportSerializer(serializers.ModelSerializer):
    parsed_data = JobDescriptionParseResultSerializer(read_only=True)

    class Meta:
        model = JDImport
        fields = [
            "id",
            "original_filename",
            "status",
            "parsed_data",
            "error_message",
            "expires_at",
            "consumed_job",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class JobListQuerySerializer(serializers.Serializer):
    """Validate query params trước khi truyền xuống selector tìm kiếm."""

    keyword = serializers.CharField(required=False, allow_blank=True)
    job_type = serializers.ChoiceField(choices=JobPost.JobType.choices, required=False)
    location = serializers.CharField(required=False, allow_blank=True)
    experience_level = serializers.ChoiceField(
        choices=JobPost.ExperienceLevel.choices,
        required=False,
    )
    salary_min = serializers.IntegerField(required=False, min_value=0)
