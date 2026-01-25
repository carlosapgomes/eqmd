from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.drugtemplates.models import DrugTemplate

User = get_user_model()


class DrugTemplateSearchTest(TestCase):
    """Tests for accent-insensitive drug template autocomplete search."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="doctor",
            email="doctor@example.com",
            password="testpass123",
            profession=1,
        )
        self.client = Client()
        self.client.login(username="doctor", password="testpass123")

        DrugTemplate.objects.create(
            name="Dipirona Sódica",
            concentration="500 mg",
            pharmaceutical_form="comprimido",
            usage_instructions="Tomar 1 comprimido a cada 8 horas.",
            creator=self.user,
            is_public=True,
        )

    def test_autocomplete_matches_without_accents(self):
        url = reverse("outpatientprescriptions:search_drug_templates")
        response = self.client.get(url, {"q": "sodica"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        names = [result.get("name") for result in payload.get("results", [])]
        self.assertIn("Dipirona Sódica", names)
