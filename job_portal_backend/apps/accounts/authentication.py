"""Xác thực JWT vô hiệu hóa access token sau khi tài khoản bị khóa."""
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from drf_spectacular.extensions import OpenApiAuthenticationExtension


class ActiveUserJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "apps.accounts.authentication.ActiveUserJWTAuthentication"
    name = "jwtAuth"

    def get_security_definition(self, auto_schema):
        return {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}


class ActiveUserJWTAuthentication(JWTAuthentication):
    """Từ chối JWT hợp lệ nếu user tương ứng trong cơ sở dữ liệu đã ngừng hoạt động."""

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if not user.is_active:
            raise AuthenticationFailed("Tài khoản đã bị khóa.", code="user_inactive")
        return user
