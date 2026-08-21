"""companies serializers — chỉ định hình input/output, không chứa logic nghiệp vụ."""
from rest_framework import serializers

from apps.companies.models import Company


class CompanyReadSerializer(serializers.ModelSerializer):
    owner_email = serializers.EmailField(source="owner.email", read_only=True)

    class Meta:
        model = Company
        fields = [
            "id", "name", "tax_code", "description", "website",
            "logo_url", "address", "company_size", "industry",
            "status", "rejection_reason", "reviewed_at",
            "owner_email", "created_at", "updated_at",
        ]
        read_only_fields = fields


class CompanyWriteSerializer(serializers.ModelSerializer):
    """Các field employer được phép tự cập nhật. status do service/admin quản lý."""

    class Meta:
        model = Company
        fields = [
            "name", "tax_code", "description", "website",
            "logo_url", "address", "company_size", "industry",
        ]

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Tên công ty không được để trống.")
        return value.strip()


class CompanyListQuerySerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=Company.Status.choices,
        required=False,
    )


class CompanyRejectSerializer(serializers.Serializer):
    rejection_reason = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
    )
