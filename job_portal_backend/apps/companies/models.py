"""
companies/models.py
Nhà tuyển dụng quản lý hồ sơ công ty; Admin duyệt hồ sơ công ty đăng ký
(UC diagram: "Quản lý hồ sơ công ty", "Duyệt hồ sơ công ty đăng ký").
UC-02 precondition depends on Company.status == APPROVED.
"""
from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class Company(BaseModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Chờ duyệt"
        APPROVED = "APPROVED", "Đã duyệt"
        REJECTED = "REJECTED", "Từ chối"
        LOCKED = "LOCKED", "Bị khóa"

    # The employer account that manages this company profile.
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_companies",
        limit_choices_to={"role": "EMPLOYER"},
    )

    name = models.CharField(max_length=255)
    tax_code = models.CharField(max_length=50, unique=True, null=True, blank=True)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    logo_url = models.URLField(blank=True)
    address = models.CharField(max_length=500, blank=True)
    company_size = models.CharField(max_length=50, blank=True)
    industry = models.CharField(max_length=150, blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    # --- Admin approval trail (UC diagram: Admin -> Duyệt hồ sơ công ty) ---
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="reviewed_companies",
        limit_choices_to={"role": "ADMIN"},
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    class Meta:
        db_table = "companies"
        verbose_name_plural = "companies"
        indexes = [models.Index(fields=["status"])]
        constraints = [
            models.UniqueConstraint(fields=["owner"], name="unique_company_owner"),
        ]

    def __str__(self):
        return self.name

    @property
    def is_approved(self):
        return self.status == self.Status.APPROVED
