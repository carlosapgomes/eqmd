from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.patients.models import Patient


User = get_user_model()


class PatientSearchAccentInsensitiveTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="search-user",
            email="search-user@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            terms_accepted_at=timezone.now(),
        )

        content_type = ContentType.objects.get_for_model(Patient)
        view_permission = Permission.objects.get(
            content_type=content_type,
            codename="view_patient",
        )
        self.user.user_permissions.add(view_permission)

        self.client = Client()
        self.client.login(username="search-user", password="testpass123")

        self.patient = Patient.objects.create(
            name="João da Silva",
            birthday="1980-01-01",
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user,
        )

    def test_patient_list_search_matches_without_diacritics(self):
        response = self.client.get(reverse("patients:patient_list"), {"q": "joao"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "João da Silva")

    def test_patient_search_api_matches_without_diacritics(self):
        response = self.client.get(reverse("patients:api_patient_search"), {"q": "joao"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        returned_ids = {item["id"] for item in payload["results"]}
        self.assertIn(str(self.patient.pk), returned_ids)
