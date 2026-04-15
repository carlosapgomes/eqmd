from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from ..models import Patient, PatientAdmission, Ward

User = get_user_model()


class AdmissionSignalSyncsPatientLocationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='signal_user',
            email='signal_user@example.com',
            password='testpassword',
        )
        self.patient = Patient.objects.create(
            name='Paciente Sinal',
            birthday='1980-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user,
        )
        self.ward = Ward.objects.create(
            name='UTI Sinais',
            abbreviation='UTIS',
            created_by=self.user,
            updated_by=self.user,
        )

    def test_active_admission_updates_patient_ward_and_bed(self):
        admission = PatientAdmission.objects.create(
            patient=self.patient,
            admission_datetime=timezone.now() - timedelta(hours=1),
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            ward=self.ward,
            initial_bed='A101',
            created_by=self.user,
            updated_by=self.user,
        )

        self.patient.refresh_from_db()

        self.assertEqual(self.patient.status, Patient.Status.INPATIENT)
        self.assertEqual(self.patient.current_admission_id, admission.id)
        self.assertEqual(self.patient.ward, self.ward)
        self.assertEqual(self.patient.bed, 'A101')
