"""
accounts/models.py
Custom User model. Supports 3 roles per Project Charter: Ứng viên, Nhà tuyển
dụng, Admin. Also supports Google OAuth sign-in (UC diagram: Google OAuth ->
Đăng nhập) alongside classic email/password + JWT.
"""
import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Auth is handled by JWT (SimpleJWT) + Google OAuth per Project Charter
    section 7 (Kiến trúc và công nghệ dự kiến).
    """

    class Role(models.TextChoices):
        CANDIDATE = "CANDIDATE", "Ứng viên"
        EMPLOYER = "EMPLOYER", "Nhà tuyển dụng"
        ADMIN = "ADMIN", "Admin"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Email is the real login identifier; username kept only for Django admin.
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CANDIDATE)

    # --- Google OAuth (UC diagram: actor "Google OAuth" -> "Đăng nhập") ---
    google_sub = models.CharField(
        max_length=255, unique=True, null=True, blank=True,
        help_text="Google account 'sub' claim, set on first Google sign-in.",
    )
    auth_provider = models.CharField(
        max_length=20,
        choices=[("PASSWORD", "Password"), ("GOOGLE", "Google OAuth")],
        default="PASSWORD",
    )

    # is_active reused by UC-04/E2 ("Ứng viên đã xóa hoặc khóa tài khoản")
    # inherited from AbstractUser: self.is_active

    phone = models.CharField(max_length=20, blank=True, help_text="Số điện thoại liên hệ.")
    phone_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        db_table = "users"
        indexes = [
            models.Index(fields=["role"]),
            models.Index(fields=["email"]),
        ]

    def __str__(self):
        return f"{self.email} ({self.role})"

    @property
    def is_candidate(self):
        return self.role == self.Role.CANDIDATE

    @property
    def is_employer(self):
        return self.role == self.Role.EMPLOYER

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN
