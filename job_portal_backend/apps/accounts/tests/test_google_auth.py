from unittest.mock import ANY, patch

from django.test import override_settings
from django.urls import reverse
from google.auth.exceptions import TransportError
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.candidates.models import CandidateProfile
from apps.companies.models import Company


@override_settings(GOOGLE_CLIENT_ID="web-client-id.apps.googleusercontent.com")
class GoogleAuthApiTests(APITestCase):
    def google_claims(self, **overrides):
        claims = {
            "sub": "google-sub-123",
            "email": "candidate@example.com",
            "email_verified": True,
            "aud": "web-client-id.apps.googleusercontent.com",
            "given_name": "An",
            "family_name": "Nguyen",
        }
        claims.update(overrides)
        return claims

    @patch("google.oauth2.id_token.verify_oauth2_token")
    def test_google_login_creates_candidate_and_returns_tokens(self, verify_token):
        verify_token.return_value = self.google_claims()

        response = self.client.post(
            reverse("accounts-google-auth"),
            {"id_token": "valid-google-token"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        verify_token.assert_called_once_with(
            "valid-google-token",
            ANY,
            "web-client-id.apps.googleusercontent.com",
        )
        user = User.objects.get(email="candidate@example.com")
        self.assertEqual(user.auth_provider, "GOOGLE")
        self.assertEqual(user.google_sub, "google-sub-123")
        self.assertFalse(user.has_usable_password())
        self.assertTrue(CandidateProfile.objects.filter(user=user).exists())
        self.assertEqual(response.data["user"]["id"], str(user.id))
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    @patch("google.oauth2.id_token.verify_oauth2_token")
    def test_google_login_creates_employer_company(self, verify_token):
        verify_token.return_value = self.google_claims(
            sub="employer-sub", email="employer@example.com"
        )

        response = self.client.post(
            reverse("accounts-google-auth"),
            {
                "id_token": "valid-google-token",
                "role": User.Role.EMPLOYER,
                "company_name": "Google Employer Co",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user = User.objects.get(email="employer@example.com")
        self.assertEqual(user.role, User.Role.EMPLOYER)
        self.assertTrue(
            Company.objects.filter(owner=user, name="Google Employer Co").exists()
        )

    @patch("google.oauth2.id_token.verify_oauth2_token")
    def test_new_google_employer_requires_company_name(self, verify_token):
        verify_token.return_value = self.google_claims()

        response = self.client.post(
            reverse("accounts-google-auth"),
            {"id_token": "token", "role": User.Role.EMPLOYER},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(email="candidate@example.com").exists())

    @patch("google.oauth2.id_token.verify_oauth2_token")
    def test_google_login_does_not_take_over_password_email(self, verify_token):
        password_user = User.objects.create_user(
            username="password-user",
            email="candidate@example.com",
            password="password123",
        )
        verify_token.return_value = self.google_claims()

        response = self.client.post(
            reverse("accounts-google-auth"),
            {"id_token": "token"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        password_user.refresh_from_db()
        self.assertEqual(password_user.auth_provider, "PASSWORD")
        self.assertIsNone(password_user.google_sub)
        self.assertEqual(User.objects.count(), 1)

    @patch("google.oauth2.id_token.verify_oauth2_token")
    def test_google_login_rejects_unverified_email(self, verify_token):
        verify_token.return_value = self.google_claims(email_verified=False)

        response = self.client.post(
            reverse("accounts-google-auth"),
            {"id_token": "token"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(User.objects.count(), 0)

    @patch("google.oauth2.id_token.verify_oauth2_token")
    def test_google_login_handles_google_transport_error(self, verify_token):
        verify_token.side_effect = TransportError("Google unavailable")

        response = self.client.post(
            reverse("accounts-google-auth"),
            {"id_token": "token"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(User.objects.count(), 0)

    @patch("google.oauth2.id_token.verify_oauth2_token")
    def test_existing_google_user_ignores_new_user_fields(self, verify_token):
        user = User.objects.create_user(
            username="existing-google-user",
            email="candidate@example.com",
            role=User.Role.CANDIDATE,
            auth_provider="GOOGLE",
            google_sub="google-sub-123",
        )
        verify_token.return_value = self.google_claims()

        response = self.client.post(
            reverse("accounts-google-auth"),
            {"id_token": "token", "role": User.Role.EMPLOYER},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.role, User.Role.CANDIDATE)
        self.assertFalse(Company.objects.filter(owner=user).exists())
