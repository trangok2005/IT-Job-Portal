from django.contrib import admin
from apps.companies.models import Company
from apps.companies.services import approve_company, reject_company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "status", "tax_code", "reviewed_by", "reviewed_at")
    list_filter = ("status",)
    search_fields = ("name", "tax_code", "owner__email")
    actions = ["approve_companies", "reject_companies"]

    @admin.action(description="Duyệt hồ sơ công ty đã chọn")
    def approve_companies(self, request, queryset):
        for company in queryset.filter(status=Company.Status.PENDING):
            approve_company(company, request.user)

    @admin.action(description="Từ chối hồ sơ công ty đã chọn")
    def reject_companies(self, request, queryset):
        for company in queryset.filter(status=Company.Status.PENDING):
            reject_company(company, request.user, "Từ chối bởi quản trị viên.")
