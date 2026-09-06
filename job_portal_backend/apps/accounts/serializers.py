"""accounts serializers — shape input/output only."""
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id", "email", "username", "role", "auth_provider",
            "first_name", "last_name", "is_active", "created_at",
        ]
        read_only_fields = fields


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    role = serializers.ChoiceField(
        choices=[User.Role.CANDIDATE, User.Role.EMPLOYER], default=User.Role.CANDIDATE
    )
    # Chỉ dành cho EMPLOYER: tạo luôn hồ sơ công ty PENDING để admin duyệt.
    company_name = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            "email", "username", "password", "role",
            "first_name", "last_name", "company_name",
        ]
        extra_kwargs = {
            "first_name": {"required": False, "allow_blank": True},
            "last_name": {"required": False, "allow_blank": True},
        }

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Email đã được sử dụng.")
        return value.lower()

    def validate(self, attrs):
        if attrs.get("role") == User.Role.EMPLOYER:
            company_name = attrs.get("company_name", "").strip()
            if not company_name:
                raise serializers.ValidationError(
                    {"company_name": "Nhà tuyển dụng phải nhập tên công ty."}
                )
            attrs["company_name"] = company_name
        return attrs



class GoogleAuthSerializer(serializers.Serializer):
    id_token = serializers.CharField(trim_whitespace=True)
    role = serializers.ChoiceField(
        choices=[User.Role.CANDIDATE, User.Role.EMPLOYER],
        required=False,
        default=User.Role.CANDIDATE,
    )
    company_name = serializers.CharField(required=False, allow_blank=True)


class GoogleAuthResponseSerializer(serializers.Serializer):
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)
    user = UserSerializer(read_only=True)


class AdminUserListQuerySerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=User.Role.choices, required=False)
    is_active = serializers.BooleanField(required=False)
    search = serializers.CharField(required=False, allow_blank=True)


class ActiveUserTokenRefreshSerializer(TokenRefreshSerializer):
    """Refresh only when the token's user still exists and is active."""

    def validate(self, attrs):
        try:
            refresh = RefreshToken(attrs["refresh"])
        except Exception as exc:
            raise InvalidToken("Refresh token không hợp lệ.") from exc
        user_id = refresh.payload.get(api_settings.USER_ID_CLAIM)
        user = User.objects.filter(**{api_settings.USER_ID_FIELD: user_id}).first()
        if user is None or not user.is_active:
            raise AuthenticationFailed("Tài khoản đã bị khóa.", code="user_inactive")
        return super().validate(attrs)
