from django.db import IntegrityError
from django.test import TestCase

from apps.accounts.models import User
from apps.companies.models import Company
from apps.companies.services import (
    approve_company,
    create_company_from_registration,
    reject_company,
    resubmit_company,
)


class CompanyServiceTests(TestCase):
    def setUp(self):
        self.employer = User.objects.create_user(
            username="employer",
            email="employer@example.com",
            password="password123",
            role=User.Role.EMPLOYER,
        )
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="password123",
            role=User.Role.ADMIN,
        )

    def test_registration_creates_pending_company(self):
        company = create_company_from_registration(self.employer, "  Acme  ")

        self.assertEqual(company.name, "Acme")
        self.assertEqual(company.status, Company.Status.PENDING)
        self.assertEqual(company.owner, self.employer)

    def test_employer_can_only_own_one_company(self):
        create_company_from_registration(self.employer, "Acme")

        with self.assertRaises(IntegrityError):
            create_company_from_registration(self.employer, "Another")

    def test_rejected_company_can_be_resubmitted(self):
        company = create_company_from_registration(self.employer, "Acme")
        reject_company(company, self.admin, "Thiếu mã số thuế")

        resubmit_company(company)

        self.assertEqual(company.status, Company.Status.PENDING)
        self.assertEqual(company.rejection_reason, "")
        self.assertIsNone(company.reviewed_by)
        self.assertIsNone(company.reviewed_at)

    def test_only_pending_company_can_be_approved(self):
        company = create_company_from_registration(self.employer, "Acme")
        reject_company(company, self.admin, "Thông tin không hợp lệ")

        with self.assertRaisesMessage(ValueError, "đang chờ duyệt"):
            approve_company(company, self.admin)

    def test_rejection_requires_reason(self):
        company = create_company_from_registration(self.employer, "Acme")

        with self.assertRaisesMessage(ValueError, "lý do từ chối"):
            reject_company(company, self.admin, "  ")
