"""skills serializers — only shape input/output, no business logic."""
from rest_framework import serializers

from apps.skills.models import MatchingWeightConfig, Skill, SkillAlias, SkillCategory


class SkillCategorySerializer(serializers.ModelSerializer):
    skill_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = SkillCategory
        fields = ["id", "name", "skill_count"]


class SkillAliasReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = SkillAlias
        fields = ["id", "alias_text", "normalized_text"]


class SkillReadSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True, default="")
    merged_into_name = serializers.CharField(source="merged_into.name", read_only=True, default="")
    aliases = SkillAliasReadSerializer(many=True, read_only=True)

    class Meta:
        model = Skill
        fields = [
            "id", "name", "slug", "category", "category_name",
            "status", "source", "merged_into", "merged_into_name",
            "is_active", "reviewed_by", "reviewed_at",
            "aliases", "created_at", "updated_at",
        ]
        read_only_fields = fields


class SkillWriteSerializer(serializers.ModelSerializer):
    aliases = serializers.ListField(
        child=serializers.CharField(max_length=150), required=False, write_only=True,
    )

    class Meta:
        model = Skill
        fields = ["name", "category", "is_active", "aliases"]


class SkillListQuerySerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Skill.Status.choices, required=False)


class SkillMergeSerializer(serializers.Serializer):
    source_ids = serializers.ListField(
        child=serializers.UUIDField(), min_length=1, allow_empty=False,
    )
    target_id = serializers.UUIDField()


class SkillHotSerializer(serializers.ModelSerializer):
    job_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Skill
        fields = ["id", "name", "slug", "job_count"]


class MatchingWeightConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = MatchingWeightConfig
        fields = [
            "id", "name", "is_active",
            "weight_semantic_similarity",
            "weight_skill_overlap",
            "weight_experience_match",
            "weight_education_match",
            "updated_by", "updated_at", "created_at",
        ]
        read_only_fields = ["id", "updated_by", "updated_at", "created_at"]

    def validate(self, attrs):
        total = sum(
            float(attrs.get(field, getattr(self.instance, field, 0)))
            for field in (
                "weight_semantic_similarity",
                "weight_skill_overlap",
                "weight_experience_match",
                "weight_education_match",
            )
        )
        if abs(total - 1.0) > 0.001:
            raise serializers.ValidationError("Tổng các trọng số phải bằng 1.0.")
        return attrs
