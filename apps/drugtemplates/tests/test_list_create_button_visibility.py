from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse


User = get_user_model()


class TemplateListCreateButtonVisibilityTest(TestCase):
    """Ensure create button visibility matches doctor/resident backend permissions."""

    @classmethod
    def setUpTestData(cls):
        cls.doctor = User.objects.create_user(
            username="button_doctor",
            email="button_doctor@example.com",
            password="testpass123",
            profession_type=User.MEDICAL_DOCTOR,
            password_change_required=False,
            terms_accepted=True,
        )
        cls.resident = User.objects.create_user(
            username="button_resident",
            email="button_resident@example.com",
            password="testpass123",
            profession_type=User.RESIDENT,
            password_change_required=False,
            terms_accepted=True,
        )
        cls.nurse = User.objects.create_user(
            username="button_nurse",
            email="button_nurse@example.com",
            password="testpass123",
            profession_type=User.NURSE,
            password_change_required=False,
            terms_accepted=True,
        )

    def setUp(self):
        self.client = Client()

    def test_drugtemplate_list_shows_create_button_for_doctor(self):
        self.client.login(username=self.doctor.username, password="testpass123")
        response = self.client.get(reverse("drugtemplates:list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Novo Modelo")

    def test_drugtemplate_list_shows_create_button_for_resident(self):
        self.client.login(username=self.resident.username, password="testpass123")
        response = self.client.get(reverse("drugtemplates:list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Novo Modelo")

    def test_prescriptiontemplate_list_shows_create_button_for_resident(self):
        self.client.login(username=self.resident.username, password="testpass123")
        response = self.client.get(reverse("drugtemplates:prescription_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Novo Modelo")

    def test_prescriptiontemplate_list_denies_nurse(self):
        self.client.login(username=self.nurse.username, password="testpass123")
        response = self.client.get(reverse("drugtemplates:prescription_list"))

        self.assertEqual(response.status_code, 403)
