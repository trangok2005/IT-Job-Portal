from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.companies.models import Company
from apps.jobs.models import JobPost


class CompanyApiTests(APITestCase):
    def setUp(self):
        self.employer = User.objects.create_user(
            username="employer",
            email="employer@example.com",
            password="password123",
            role=User.Role.EMPLOYER,
        )
        self.other_employer = User.objects.create_user(
            username="other",
            email="other@example.com",
            password="password123",
            role=User.Role.EMPLOYER,
        )
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="password123",
            role=User.Role.ADMIN,
        )
        self.company = Company.objects.create(owner=self.employer, name="Acme")

    def test_employer_can_read_and_update_own_company(self):
        self.client.force_authenticate(self.employer)

        response = self.client.patch(
            reverse("companies-me"),
            {"description": "Nền tảng tuyển dụng"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.company.refresh_from_db()
        self.assertEqual(self.company.description, "Nền tảng tuyển dụng")

    def test_employer_cannot_list_companies(self):
        self.client.force_authenticate(self.employer)

        response = self.client.get(reverse("companies-list"))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_filter_pending_companies(self):
        Company.objects.create(
            owner=self.other_employer,
            name="Approved Co",
            status=Company.Status.APPROVED,
        )
        self.client.force_authenticate(self.admin)

        response = self.client.get(
            reverse("companies-list"),
            {"status": Company.Status.PENDING},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], str(self.company.id))

    def test_admin_rejection_requires_reason(self):
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            reverse("companies-reject", args=[self.company.id]),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.company.refresh_from_db()
        self.assertEqual(self.company.status, Company.Status.PENDING)

    def test_employer_cannot_resubmit_another_company(self):
        self.company.status = Company.Status.REJECTED
        self.company.save()
        self.client.force_authenticate(self.other_employer)

        response = self.client.post(
            reverse("companies-resubmit", args=[self.company.id]),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class EmployerRegistrationTests(APITestCase):
    def test_employer_registration_creates_company(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "new-employer",
                "email": "new-employer@example.com",
                "password": "password123",
                "role": User.Role.EMPLOYER,
                "company_name": "Acme Vietnam",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        company = Company.objects.get(owner__email="new-employer@example.com")
        self.assertEqual(company.name, "Acme Vietnam")
        self.assertEqual(company.status, Company.Status.PENDING)

    def test_employer_registration_requires_company_name(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "new-employer",
                "email": "new-employer@example.com",
                "password": "password123",
                "role": User.Role.EMPLOYER,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(email="new-employer@example.com").exists())


class LockedCompanyJobsTests(APITestCase):
    def test_locked_company_jobs_are_not_public(self):
        employer = User.objects.create_user(
            username="locked-employer",
            email="locked@example.com",
            password="password123",
            role=User.Role.EMPLOYER,
        )
        company = Company.objects.create(
            owner=employer,
            name="Locked Co",
            status=Company.Status.LOCKED,
        )
        JobPost.objects.create(
            company=company,
            created_by=employer,
            title="Backend Developer",
            description="Django",
            requirements="Python",
            location="Ha Noi",
            status=JobPost.Status.ACTIVE,
        )

        response = self.client.get(reverse("jobs-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)
