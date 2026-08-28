"""candidates serializers — chỉ định hình input/output, không chứa logic nghiệp vụ."""
from pathlib import Path

from django.conf import settings
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from apps.candidates.models import CandidateProfile, Education, Experience, Resume, ResumeImport
from apps.skills.models import CandidateSkill, Skill


class EducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Education
        fields = [
            "id", "school_name", "major", "degree",
            "start_date", "end_date", "description", "source",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "source", "created_at", "updated_at"]

    def validate(self, attrs):
        """Kiểm tra khoảng thời gian bằng cả dữ liệu cũ khi PATCH."""
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError(
                {"end_date": "end_date phải sau hoặc bằng start_date."}
            )
        return attrs


class ExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Experience
        fields = [
            "id", "company_name", "position",
            "start_date", "end_date", "is_current", "description", "source",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "source", "created_at", "updated_at"]

    def validate(self, attrs):
        """Giữ ngày làm việc nhất quán khi tạo mới và cập nhật một phần."""
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
        is_current = attrs.get("is_current", getattr(self.instance, "is_current", False))
        if end_date and is_current:
            raise serializers.ValidationError({"end_date": "Không đặt end_date khi đang làm tại công ty (is_current)."})
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError({"end_date": "end_date phải sau start_date."})
        return attrs


class CandidateSkillSerializer(serializers.ModelSerializer):
    skill_name = serializers.CharField(source="skill.name", read_only=True)
    # UC-01 bước 11: FE hiển thị nhãn vàng cho skill chưa được Admin duyệt.
    skill_status = serializers.CharField(source="skill.status", read_only=True)

    class Meta:
        model = CandidateSkill
        fields = [
            "id", "skill", "skill_name", "skill_status", "level",
            "years_of_experience", "source",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "skill_name", "skill_status", "source",
            "created_at", "updated_at",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["skill"] = serializers.PrimaryKeyRelatedField(
            queryset=Skill.objects.filter(
                status=Skill.Status.APPROVED, is_active=True
            ),
        )


class ResumeParsedDataSerializer(serializers.Serializer):
    """Validated CV data exposed for user review before profile save."""

    full_name = serializers.CharField(required=False, allow_blank=True, max_length=255)
    phone = serializers.CharField(required=False, allow_blank=True, max_length=20)
    headline = serializers.CharField(required=False, allow_blank=True, max_length=255)
    summary = serializers.CharField(required=False, allow_blank=True)
    educations = EducationSerializer(many=True, required=False)
    experiences = ExperienceSerializer(many=True, required=False)
    skills = serializers.ListField(
        child=serializers.CharField(max_length=150),
        required=False,
    )


class ResumeImportSerializer(serializers.ModelSerializer):
    """Serializer for ResumeImport - read-only preview after AI parsing."""

    file_url = serializers.SerializerMethodField()
    parsed_data = ResumeParsedDataSerializer(read_only=True, allow_null=True)

    class Meta:
        model = ResumeImport
        fields = [
            "id", "original_filename", "file_size_bytes",
            "parse_status", "parse_error_message", "parsed_data",
            "expires_at", "file_url",
            "created_at", "updated_at",
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.URLField())
    def get_file_url(self, obj):
        request = self.context.get("request")
        url = obj.file.url
        if request is not None:
            return request.build_absolute_uri(url)
        return url


class ResumeImportUploadSerializer(serializers.Serializer):
    """Serializer for uploading a CV to be parsed asynchronously (ResumeImport)."""

    file = serializers.FileField(write_only=True)

    def validate_file(self, file):
        suffix = Path(file.name).suffix.lower()
        allowed_extensions = {".pdf", ".doc", ".docx"}
        if suffix not in allowed_extensions:
            raise serializers.ValidationError("CV chỉ hỗ trợ file PDF, DOC hoặc DOCX.")

        max_size = settings.MAX_RESUME_SIZE_BYTES
        if file.size > max_size:
            max_size_mb = max_size // (1024 * 1024)
            raise serializers.ValidationError(
                f"Dung lượng CV không được vượt quá {max_size_mb} MB."
            )
        return file


class ResumeSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    parsed_data = ResumeParsedDataSerializer(read_only=True, allow_null=True)

    class Meta:
        model = Resume
        fields = [
            "id", "original_filename", "file_size_bytes",
            "parse_status", "parsed_data", "is_primary", "file_url",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "original_filename", "file_size_bytes",
            "parse_status", "parsed_data", "is_primary", "file_url",
            "created_at", "updated_at",
        ]

    @extend_schema_field(serializers.URLField())
    def get_file_url(self, obj):
        """Trả URL tuyệt đối khi serializer được gọi trong request API."""
        request = self.context.get("request")
        url = obj.file.url
        if request is not None:
            return request.build_absolute_uri(url)
        return url


class CandidateProfileReadSerializer(serializers.ModelSerializer):
    educations = EducationSerializer(many=True, read_only=True)
    experiences = ExperienceSerializer(many=True, read_only=True)
    skills = CandidateSkillSerializer(source="candidate_skills", many=True, read_only=True)
    resumes = ResumeSerializer(many=True, read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    embedding_is_stale = serializers.BooleanField(read_only=True)

    class Meta:
        model = CandidateProfile
        fields = [
            "id", "email", "full_name", "phone", "dob", "gender",
            "address", "avatar_url", "headline", "summary",
            "desired_position", "desired_salary_min", "is_public",
            "profile_version", "embedding_version", "embedding_is_stale",
            "embedding_updated_at",
            "educations", "experiences", "skills", "resumes",
            "created_at", "updated_at",
        ]
        read_only_fields = fields


class CandidateProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateProfile
        fields = [
            "full_name", "phone", "dob", "gender", "address",
            "avatar_url", "headline", "summary",
            "desired_position", "desired_salary_min", "is_public",
        ]

    def validate_dob(self, value):
        """Không chấp nhận ngày sinh trong tương lai."""
        from django.utils import timezone
        if value and value > timezone.now().date():
            raise serializers.ValidationError("Ngày sinh không được ở tương lai.")
        return value


class CandidateSkillSaveSerializer(serializers.Serializer):
    """Skill input for the reviewed snapshot: accepts an approved skill id OR a
    new raw name that will be normalized through the taxonomy on save."""

    skill = serializers.CharField(max_length=150)
    level = serializers.ChoiceField(
        choices=CandidateSkill.Level.choices,
        required=False,
        allow_blank=True,
        default="",
    )
    years_of_experience = serializers.DecimalField(
        max_digits=4, decimal_places=1, required=False, allow_null=True
    )


class CandidateProfileSaveSerializer(CandidateProfileUpdateSerializer):
    """A complete user-reviewed profile snapshot saved atomically."""

    educations = EducationSerializer(many=True)
    experiences = ExperienceSerializer(many=True)
    skills = CandidateSkillSaveSerializer(many=True)
    resume_import_id = serializers.UUIDField(required=False, allow_null=True, write_only=True)

    class Meta(CandidateProfileUpdateSerializer.Meta):
        fields = [
            *CandidateProfileUpdateSerializer.Meta.fields,
            "educations",
            "experiences",
            "skills",
            "resume_import_id",
        ]

    def validate_skills(self, value):
        keys = [item["skill"].strip().lower() for item in value]
        if len(keys) != len(set(keys)):
            raise serializers.ValidationError("Danh sách kỹ năng không được trùng.")
        return value
