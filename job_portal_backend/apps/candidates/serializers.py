from pathlib import Path

from django.conf import settings
from rest_framework import serializers

from apps.candidates.models import CandidateProfile, Education, Experience, Resume, ResumeImport
from apps.skills.models import CandidateSkill, Skill


class EducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Education
        fields = [
            "id", "school_name", "major", "degree",
            "degree_level", "is_completed", "is_verified",
            "start_date", "end_date", "description",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError(
                {"end_date": "end_date phải sau hoặc bằng start_date."}
            )
        is_completed = attrs.get("is_completed", getattr(self.instance, "is_completed", False))
        is_verified = attrs.get("is_verified", getattr(self.instance, "is_verified", False))
        degree_level = attrs.get("degree_level", getattr(self.instance, "degree_level", None))
        if is_verified and not is_completed:
            raise serializers.ValidationError(
                {"is_verified": "Chỉ xác nhận bằng cấp đã hoàn thành."}
            )
        if is_verified and degree_level is None:
            raise serializers.ValidationError(
                {"degree_level": "Cần chọn bậc học vấn trước khi xác nhận."}
            )
        return attrs


class ExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Experience
        fields = [
            "id", "company_name", "position",
            "start_date", "end_date", "is_current", "description",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        from django.utils import timezone

        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
        is_current = attrs.get("is_current", getattr(self.instance, "is_current", False))
        if end_date and is_current:
            raise serializers.ValidationError({"end_date": "Không đặt end_date khi đang làm tại công ty (is_current)."})
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError({"end_date": "end_date phải sau start_date."})
        today = timezone.localdate()
        if start_date and start_date > today:
            raise serializers.ValidationError({"start_date": "Ngày bắt đầu không được ở tương lai."})
        if end_date and end_date > today:
            raise serializers.ValidationError({"end_date": "Ngày kết thúc không được ở tương lai."})
        return attrs


class CandidateSkillSerializer(serializers.ModelSerializer):
    skill_name = serializers.CharField(source="skill.name", read_only=True)
    skill_status = serializers.CharField(source="skill.status", read_only=True)

    class Meta:
        model = CandidateSkill
        fields = [
            "id", "skill", "skill_name", "skill_status", "years_of_experience",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "skill_name", "skill_status",
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

    parsed_data = ResumeParsedDataSerializer(read_only=True, allow_null=True)

    class Meta:
        model = ResumeImport
        fields = [
            "id", "original_filename", "file_size_bytes",
            "parse_status", "parse_error_message", "parsed_data",
            "expires_at",
            "created_at", "updated_at",
        ]
        read_only_fields = fields


class ResumeImportUploadSerializer(serializers.Serializer):

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
    class Meta:
        model = Resume
        fields = [
            "id", "original_filename", "file_size_bytes",
            "is_primary",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "original_filename", "file_size_bytes",
            "is_primary",
            "created_at", "updated_at",
        ]


class PrivateFileURLSerializer(serializers.Serializer):
    url = serializers.URLField()
    expires_at = serializers.DateTimeField()


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
            "desired_position", "is_public",
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
            "desired_position", "is_public",
        ]

    def validate_dob(self, value):
        from django.utils import timezone
        if value and value > timezone.now().date():
            raise serializers.ValidationError("Ngày sinh không được ở tương lai.")
        return value


class CandidateSkillSaveSerializer(serializers.Serializer):

    skill = serializers.CharField(max_length=150)
    years_of_experience = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=0,
    )


class CandidateProfileSaveSerializer(CandidateProfileUpdateSerializer):
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
