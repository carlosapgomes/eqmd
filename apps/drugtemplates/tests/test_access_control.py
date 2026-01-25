from django.test import TestCase, Client
from django.urls import reverse
from apps.accounts.tests.factories import DoctorFactory, ResidentFactory, NurseFactory
from apps.drugtemplates.models import DrugTemplate, PrescriptionTemplate


class DrugTemplatesAccessControlTest(TestCase):
    """Permission enforcement for template views."""

    @classmethod
    def setUpTestData(cls):
        cls.doctor = DoctorFactory(password='testpass123')
        cls.resident = ResidentFactory(password='testpass123')
        cls.nurse = NurseFactory(password='testpass123')

        cls.drug_template = DrugTemplate.objects.create(
            name='Dipirona',
            concentration='500 mg',
            pharmaceutical_form='comprimido',
            usage_instructions='1 comprimido via oral a cada 6-8 horas.',
            creator=cls.doctor,
            is_public=True,
        )

        cls.prescription_template = PrescriptionTemplate.objects.create(
            name='Hipertensao - Basico',
            creator=cls.doctor,
            is_public=True,
        )

    def setUp(self):
        self.client = Client()

    def test_drugtemplate_list_access_doctor(self):
        self.client.login(username=self.doctor.username, password='testpass123')
        response = self.client.get(reverse('drugtemplates:list'))
        self.assertEqual(response.status_code, 200)

    def test_drugtemplate_list_access_resident(self):
        self.client.login(username=self.resident.username, password='testpass123')
        response = self.client.get(reverse('drugtemplates:list'))
        self.assertEqual(response.status_code, 200)

    def test_drugtemplate_list_access_denied_for_nurse(self):
        self.client.login(username=self.nurse.username, password='testpass123')
        response = self.client.get(reverse('drugtemplates:list'))
        self.assertEqual(response.status_code, 403)

    def test_drugtemplate_detail_access_resident(self):
        self.client.login(username=self.resident.username, password='testpass123')
        response = self.client.get(
            reverse('drugtemplates:detail', kwargs={'pk': self.drug_template.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_drugtemplate_detail_access_denied_for_nurse(self):
        self.client.login(username=self.nurse.username, password='testpass123')
        response = self.client.get(
            reverse('drugtemplates:detail', kwargs={'pk': self.drug_template.pk})
        )
        self.assertEqual(response.status_code, 403)

    def test_prescriptiontemplate_list_access_resident(self):
        self.client.login(username=self.resident.username, password='testpass123')
        response = self.client.get(reverse('drugtemplates:prescription_list'))
        self.assertEqual(response.status_code, 200)

    def test_prescriptiontemplate_list_access_denied_for_nurse(self):
        self.client.login(username=self.nurse.username, password='testpass123')
        response = self.client.get(reverse('drugtemplates:prescription_list'))
        self.assertEqual(response.status_code, 403)
