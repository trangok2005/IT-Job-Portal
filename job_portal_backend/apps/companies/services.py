from django.utils import timezone

from apps.companies.models import Company


def create_company_from_registration(user, name: str) -> Company:
    if not user.is_employer:
        raise ValueError("Chỉ tài khoản nhà tuyển dụng mới có hồ sơ công ty.")
    name = name.strip()
    if not name:
        raise ValueError("Tên công ty không được để trống.")
    return Company.objects.create(owner=user, name=name)


def update_company(company: Company, data: dict) -> Company:
    for field, value in data.items():
        setattr(company, field, value)
    company.save()
    return company


def approve_company(company: Company, user) -> Company:
    if company.status == Company.Status.APPROVED:
        return company
    if company.status != Company.Status.PENDING:
        raise ValueError("Chỉ hồ sơ đang chờ duyệt mới được phê duyệt.")
    company.status = Company.Status.APPROVED
    company.reviewed_by = user
    company.reviewed_at = timezone.now()
    company.rejection_reason = ""
    company.save()
    return company


def reject_company(company: Company, user, reason: str = "") -> Company:
    if company.status != Company.Status.PENDING:
        raise ValueError("Chỉ hồ sơ đang chờ duyệt mới được từ chối.")
    reason = reason.strip()
    if not reason:
        raise ValueError("Cần cung cấp lý do từ chối.")
    company.status = Company.Status.REJECTED
    company.reviewed_by = user
    company.reviewed_at = timezone.now()
    company.rejection_reason = reason
    company.save()
    return company


def lock_company(company: Company, user) -> Company:
    if company.status == Company.Status.LOCKED:
        return company
    company.status = Company.Status.LOCKED
    company.reviewed_by = user
    company.reviewed_at = timezone.now()
    company.save()
    return company


def resubmit_company(company: Company) -> Company:
    if company.status != Company.Status.REJECTED:
        raise ValueError("Chỉ hồ sơ đang bị từ chối mới gửi lại được.")
    company.status = Company.Status.PENDING
    company.rejection_reason = ""
    company.reviewed_by = None
    company.reviewed_at = None
    company.save()
    return company
