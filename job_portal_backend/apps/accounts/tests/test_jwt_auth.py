from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User


class JwtAuthApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="jwt-candidate",
            email="jwt-candidate@example.com",
            password="password123",
            role=User.Role.CANDIDATE,
        )

    def obtain_tokens(self):
        response = self.client.post(
            reverse("token_obtain_pair"),
            {"email": self.user.email, "password": "password123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response.data

    def test_access_verification_me_and_refresh_flow(self):
        tokens = self.obtain_tokens()

        verify_response = self.client.post(
            reverse("token_verify"),
            {"token": tokens["access"]},
            format="json",
        )
        self.assertEqual(verify_response.status_code, status.HTTP_200_OK)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        me_response = self.client.get(reverse("me"))
        self.assertEqual(me_response.status_code, status.HTTP_200_OK)
        self.assertEqual(me_response.data["role"], User.Role.CANDIDATE)

        self.client.credentials()
        refresh_response = self.client.post(
            reverse("token_refresh"),
            {"refresh": tokens["refresh"]},
            format="json",
        )
        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", refresh_response.data)

        new_verify_response = self.client.post(
            reverse("token_verify"),
            {"token": refresh_response.data["access"]},
            format="json",
        )
        self.assertEqual(new_verify_response.status_code, status.HTTP_200_OK)

    def test_inactive_user_cannot_use_access_or_refresh(self):
        tokens = self.obtain_tokens()
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        self.assertEqual(
            self.client.get(reverse("me")).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.client.credentials()
        self.assertEqual(
            self.client.post(
                reverse("token_refresh"),
                {"refresh": tokens["refresh"]},
                format="json",
            ).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
