from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse


class HealthViewTests(TestCase):
    @patch("apps.core.views.connection.cursor", side_effect=RuntimeError("database down"))
    def test_returns_503_when_database_is_unavailable(self, cursor):
        response = self.client.get(reverse("health"))

        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.json()["success"])
        self.assertEqual(response.json()["data"]["database"], "error")
