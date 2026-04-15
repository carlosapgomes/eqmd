from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from ..models import Patient, PatientAdmission, Ward

User = get_user_model()


class PatientProfileUpdatePreservesLocationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='profile_editor',
            email='profile_editor@example.com',
            password='testpassword',
        )
        cls.user.password_change_required = False
        cls.user.terms_accepted = True
        cls.user.terms_accepted_at = timezone.now()
        cls.user.save(update_fields=['password_change_required', 'terms_accepted', 'terms_accepted_at'])

        content_type = ContentType.objects.get_for_model(Patient)
        permissions = Permission.objects.filter(content_type=content_type)
        cls.user.user_permissions.add(*permissions)

        cls.ward = Ward.objects.create(
            name='Enfermaria Clínica',
            abbreviation='EC',
            created_by=cls.user,
            updated_by=cls.user,
        )

        cls.patient = Patient.objects.create(
            name='Paciente Internado',
            birthday='1980-01-01',
            gender=Patient.GenderChoices.MALE,
            status=Patient.Status.INPATIENT,
            ward=cls.ward,
            bed='101',
            created_by=cls.user,
            updated_by=cls.user,
        )

        cls.admission = PatientAdmission.objects.create(
            patient=cls.patient,
            admission_datetime=timezone.now() - timedelta(hours=4),
            admission_type=PatientAdmission.AdmissionType.SCHEDULED,
            ward=cls.ward,
            initial_bed='101',
            created_by=cls.user,
            updated_by=cls.user,
        )

        cls.patient.current_admission_id = cls.admission.id
        cls.patient.updated_by = cls.user
        cls.patient.save(update_fields=['current_admission_id', 'updated_by', 'updated_at'])

    def setUp(self):
        self.client.login(username='profile_editor', password='testpassword')

    def test_update_personal_data_preserves_inpatient_location(self):
        response = self.client.post(
            reverse('patients:patient_update', kwargs={'pk': self.patient.pk}),
            data={
                'name': 'Paciente Internado Atualizado',
                'birthday': '1980-01-01',
                'gender': Patient.GenderChoices.MALE,
                'phone': '(11) 99999-9999',
                'address': 'Rua das Flores, 123',
                'city': 'São Paulo',
                'state': 'SP',
                'zip_code': '01000-000',
                'id_number': 'RG123',
                'fiscal_number': '123.456.789-00',
                'healthcard_number': 'SUS123',
            },
        )

        self.assertEqual(response.status_code, 302)

        self.patient.refresh_from_db()
        self.admission.refresh_from_db()

        self.assertEqual(self.patient.name, 'Paciente Internado Atualizado')
        self.assertEqual(self.patient.status, Patient.Status.INPATIENT)
        self.assertEqual(self.patient.current_admission_id, self.admission.id)
        self.assertEqual(self.patient.ward, self.ward)
        self.assertEqual(self.patient.bed, '101')
        self.assertTrue(self.admission.is_active)
