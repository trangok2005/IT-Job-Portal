"""jobs serializers — only shape input/output, no business logic."""
from pathlib import Path
import re

from django.conf import settings
from django.utils import timezone

from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from apps.jobs.models import JDImport, JobPost, JobSkill
from apps.skills.models import Skill
from apps.skills.services import resolve_savable_skill


class JobSkillSerializer(serializers.ModelSerializer):
    skill_name = serializers.CharField(source="skill.name", read_only=True)

    class Meta:
        model = JobSkill
        fields = ["id", "skill", "skill_name", "is_required", "min_years"]
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
            "workplace_type",
            "job_type",
            "experience_level",
            "salary_min",
            "salary_max",
            "salary_negotiable",
            "status",
            "published_at",
            "expires_at",
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


class RequiredSkillSpecSerializer(serializers.Serializer):
    """Một yêu cầu kỹ năng của tin tuyển dụng — nhất quán với bên Ứng viên:
    nhận UUID hoặc tên thô (tên lạ tự tạo PENDING), kèm yêu cầu số năm."""

    skill = serializers.CharField(max_length=150)
    min_years = serializers.DecimalField(
        max_digits=4,
        decimal_places=1,
        required=False,
        allow_null=True,
        min_value=0,
    )
    is_required = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs):
        attrs["skill"] = resolve_savable_skill(
            attrs["skill"], Skill.Source.JD_PARSING
        )
        return attrs


class JobWriteSerializer(serializers.ModelSerializer):
    """Employer-created fields. ``status`` is managed via service layer."""

    required_skills = RequiredSkillSpecSerializer(many=True, required=False, write_only=True)
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
            "workplace_type",
            "job_type",
            "experience_level",
            "salary_min",
            "salary_max",
            "salary_negotiable",
            "expires_at",
            "required_skills",
            "publish_immediately",
            "jd_import_id",
        ]

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
            skill_ids = [spec["skill"].pk for spec in required_skills]
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
    location = serializers.ChoiceField(
        choices=JobPost.Location.choices,
        required=False,
        allow_blank=True,
    )
    workplace_type = serializers.ChoiceField(
        choices=JobPost.WorkplaceType.choices,
        required=False,
        default=JobPost.WorkplaceType.ONSITE,
    )
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
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class JobListQuerySerializer(serializers.Serializer):
    """Validate query params trước khi truyền xuống selector tìm kiếm."""

    # UC-03 E4: từ khóa chỉ được chứa chữ/số (kể cả tiếng Việt có dấu),
    # khoảng trắng và ký tự kỹ thuật xuất hiện trong tên skill
    # (C++, C#, ASP.NET, Node.js, HTML/CSS).
    KEYWORD_ALLOWED_RE = re.compile(
        r"^[\w\s+\#./\-&'()]+$",
        re.UNICODE,
    )
    # Chuỗi vô nghĩa kiểu "+++", "---", "###" bị loại: phải có ít nhất
    # một chữ cái hoặc chữ số thực sự (underscore không tính).
    KEYWORD_HAS_ALNUM_RE = re.compile(r"[^\W_]+", re.UNICODE)
    KEYWORD_MAX_LENGTH = 100

    keyword = serializers.CharField(required=False, allow_blank=True)
    workplace_type = serializers.ChoiceField(
        choices=JobPost.WorkplaceType.choices,
        required=False,
    )
    job_type = serializers.ChoiceField(choices=JobPost.JobType.choices, required=False)
    location = serializers.ChoiceField(choices=JobPost.Location.choices, required=False)
    experience_level = serializers.ChoiceField(
        choices=JobPost.ExperienceLevel.choices,
        required=False,
    )
    salary_min = serializers.IntegerField(required=False, min_value=0)

    def validate_keyword(self, value: str) -> str:
        """UC-03 E4: từ khóa sai định dạng -> 400, không gọi AI search."""
        # Gộp nhiều khoảng trắng liên tiếp thành một.
        normalized = re.sub(r"\s+", " ", value).strip()
        if not normalized:
            return ""
        if len(normalized) > self.KEYWORD_MAX_LENGTH:
            raise serializers.ValidationError(
                f"Từ khóa tìm kiếm tối đa {self.KEYWORD_MAX_LENGTH} ký tự."
            )
        if not self.KEYWORD_ALLOWED_RE.match(normalized):
            raise serializers.ValidationError(
                "Từ khóa tìm kiếm chỉ được chứa chữ, số, khoảng trắng và các "
                "ký tự kỹ thuật như + # . - / & ' ( )."
            )
        if not self.KEYWORD_HAS_ALNUM_RE.search(normalized):
            raise serializers.ValidationError(
                "Từ khóa tìm kiếm phải chứa ít nhất một chữ cái hoặc chữ số."
            )
        return normalized
