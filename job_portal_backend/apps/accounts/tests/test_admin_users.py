from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User


class AdminUserApiTests(APITestCase):
    def setUp(self):
        self.admin = self.create_user("admin", User.Role.ADMIN)
        self.other_admin = self.create_user("other-admin", User.Role.ADMIN)
        self.candidate = self.create_user("alice", User.Role.CANDIDATE)
        self.inactive_candidate = self.create_user(
            "inactive-alice", User.Role.CANDIDATE, is_active=False
        )
        self.employer = self.create_user("employer", User.Role.EMPLOYER)

    @staticmethod
    def create_user(username, role, is_active=True):
        return User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="password123",
            role=role,
            is_active=is_active,
        )

    def test_only_admin_can_list_users(self):
        url = reverse("admin-users")

        anonymous_response = self.client.get(url)
        self.client.force_authenticate(self.candidate)
        candidate_response = self.client.get(url)

        self.assertEqual(anonymous_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(candidate_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_user_list_is_paginated_and_filters_fields(self):
        self.client.force_authenticate(self.admin)

        response = self.client.get(
            reverse("admin-users"),
            {
                "role": User.Role.CANDIDATE,
                "is_active": "false",
                "search": "alice",
                "page_size": 1,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(self.inactive_candidate.id)
        )

    def test_admin_can_lock_and_unlock_non_admin_user(self):
        self.client.force_authenticate(self.admin)

        lock_response = self.client.post(
            reverse("admin-user-lock", args=[self.candidate.id])
        )
        self.candidate.refresh_from_db()
        unlock_response = self.client.post(
            reverse("admin-user-unlock", args=[self.candidate.id])
        )
        self.candidate.refresh_from_db()

        self.assertEqual(lock_response.status_code, status.HTTP_200_OK)
        self.assertEqual(lock_response.data["is_active"], False)
        self.assertEqual(unlock_response.status_code, status.HTTP_200_OK)
        self.assertTrue(self.candidate.is_active)

    def test_admin_cannot_lock_self(self):
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            reverse("admin-user-lock", args=[self.admin.id])
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_admin_cannot_change_another_admin_lock_state(self):
        self.other_admin.is_active = False
        self.other_admin.save(update_fields=["is_active"])
        self.client.force_authenticate(self.admin)

        lock_response = self.client.post(
            reverse("admin-user-lock", args=[self.other_admin.id])
        )
        unlock_response = self.client.post(
            reverse("admin-user-unlock", args=[self.other_admin.id])
        )

        self.assertEqual(lock_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(unlock_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.other_admin.refresh_from_db()
        self.assertFalse(self.other_admin.is_active)

    def test_non_admin_cannot_lock_user(self):
        self.client.force_authenticate(self.employer)

        response = self.client.post(
            reverse("admin-user-lock", args=[self.candidate.id])
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.candidate.refresh_from_db()
        self.assertTrue(self.candidate.is_active)
