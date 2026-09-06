"""Các thao tác ghi và quy tắc nghiệp vụ xác thực tài khoản."""
from django.conf import settings
from django.db import transaction
from django.utils.text import slugify
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User


def _unique_username(email: str, google_sub: str) -> str:
    base = slugify(email.split("@", 1)[0]) or "google-user"
    candidate = base[:130]
    if not User.objects.filter(username=candidate).exists():
        return candidate
    return f"{base[:120]}-{google_sub[-8:]}"


@transaction.atomic
def create_registered_user(validated_data: dict) -> User:
    """Tạo user mật khẩu cùng hồ sơ candidate hoặc công ty bắt buộc."""
    data = dict(validated_data)
    company_name = data.pop("company_name", "")
    role = data.pop("role", User.Role.CANDIDATE)
    password = data.pop("password")
    user = User(**data, role=role, auth_provider="PASSWORD")
    user.set_password(password)
    user.save()
    _create_role_profile(user, company_name)
    return user


def _create_role_profile(user: User, company_name: str = "") -> None:
    """Tạo hồ sơ bắt buộc cho role nghiệp vụ vừa đăng ký."""
    if user.is_employer:
        from apps.companies.services import create_company_from_registration

        create_company_from_registration(user, company_name)
        return
    from apps.candidates.models import CandidateProfile

    full_name = " ".join(filter(None, [user.first_name, user.last_name])).strip()
    CandidateProfile.objects.create(
        user=user,
        full_name=full_name or user.username,
    )


def verify_google_token(raw_token: str) -> dict:
    """Xác minh Google ID token và các claim định danh bắt buộc."""
    if not settings.GOOGLE_CLIENT_ID:
        raise AuthenticationFailed("Google OAuth chưa được cấu hình.")
    from google.auth.exceptions import GoogleAuthError
    from google.auth.transport.requests import Request
    from google.oauth2 import id_token

    try:
        claims = id_token.verify_oauth2_token(
            raw_token,
            Request(),
            settings.GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=60,
        )
    except (GoogleAuthError, ValueError, TypeError) as exc:
        import logging

        logging.getLogger(__name__).error(
            "Google ID token verification failed: %s", exc, exc_info=True
        )
        raise AuthenticationFailed("Google ID token không hợp lệ.") from exc
    if claims.get("aud") != settings.GOOGLE_CLIENT_ID:
        raise AuthenticationFailed("Google ID token không đúng audience.")
    if claims.get("email_verified") is not True:
        raise AuthenticationFailed("Email Google chưa được xác minh.")
    if not isinstance(claims.get("sub"), str) or not claims["sub"].strip():
        raise AuthenticationFailed("Google ID token thiếu thông tin định danh.")
    if not isinstance(claims.get("email"), str) or not claims["email"].strip():
        raise AuthenticationFailed("Google ID token thiếu thông tin định danh.")
    return claims


@transaction.atomic
def login_or_register_google(claims: dict, role: str, company_name: str = "") -> User:
    """Đăng nhập Google subject hiện có hoặc tạo user mới trong giao dịch nguyên tử."""
    google_sub = claims["sub"]
    email = claims["email"].strip().lower()
    user = User.objects.select_for_update().filter(google_sub=google_sub).first()
    if user is not None:
        if not user.is_active:
            raise AuthenticationFailed("Tài khoản đã bị khóa.")
        return user

    email_owner = User.objects.select_for_update().filter(email__iexact=email).first()
    if email_owner is not None:
        if email_owner.auth_provider == "PASSWORD":
            raise ValidationError({"email": "Email đã thuộc tài khoản mật khẩu."})
        raise ValidationError({"email": "Email đã liên kết với tài khoản Google khác."})

    if role == User.Role.EMPLOYER and not company_name.strip():
        raise ValidationError({"company_name": "Nhà tuyển dụng phải nhập tên công ty."})
    user = User(
        email=email,
        username=_unique_username(email, google_sub),
        first_name=claims.get("given_name", ""),
        last_name=claims.get("family_name", ""),
        role=role,
        google_sub=google_sub,
        auth_provider="GOOGLE",
    )
    user.set_unusable_password()
    user.save()
    _create_role_profile(user, company_name.strip())
    return user


def issue_token_pair(user: User) -> dict:
    """Cấp cặp access/refresh SimpleJWT cho user đang hoạt động."""
    if not user.is_active:
        raise AuthenticationFailed("Tài khoản đã bị khóa.")
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


def set_user_lock(actor: User, target: User, locked: bool) -> User:
    """Khóa hoặc mở khóa tài khoản không phải admin và bảo vệ tài khoản admin."""
    if target.pk == actor.pk and locked:
        raise ValidationError({"detail": "Admin không thể tự khóa tài khoản."})
    if target.role == User.Role.ADMIN:
        raise ValidationError({"detail": "Không thể khóa hoặc mở khóa tài khoản ADMIN."})
    target.is_active = not locked
    target.save(update_fields=["is_active", "updated_at"])
    return target
