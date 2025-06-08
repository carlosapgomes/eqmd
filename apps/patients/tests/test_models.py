from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.patients.models import Patient, PatientHospitalRecord
from apps.hospitals.models import Hospital

User = get_user_model()

class PatientModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create a test user
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Create a test hospital
        cls.hospital = Hospital.objects.create(
            name='Test Hospital',
            short_name='TH',
            created_by=cls.user,
            updated_by=cls.user
        )

        # Create a test patient
        cls.patient = Patient.objects.create(
            name='John Doe',
            birthday='1990-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=cls.user,
            updated_by=cls.user
        )

        # Create a test hospital record
        cls.record = PatientHospitalRecord.objects.create(
            patient=cls.patient,
            hospital=cls.hospital,
            record_number='12345',
            created_by=cls.user,
            updated_by=cls.user
        )

    def test_patient_creation(self):
        """Test that a patient can be created with required fields"""
        self.assertEqual(self.patient.name, 'John Doe')
        self.assertEqual(self.patient.status, Patient.Status.OUTPATIENT)
        self.assertEqual(str(self.patient), 'John Doe')


    def test_hospital_record_creation(self):
        """Test that a hospital record can be created for a patient"""
        self.assertEqual(self.record.patient, self.patient)
        self.assertEqual(self.record.hospital, self.hospital)
        self.assertEqual(self.record.record_number, '12345')
        self.assertEqual(str(self.record), 'John Doe - Test Hospital (12345)')

    def test_patient_hospital_relationship(self):
        """Test the relationship between patient and hospital records"""
        self.assertEqual(self.patient.hospital_records.count(), 1)
        self.assertEqual(self.hospital.patient_records.count(), 1)