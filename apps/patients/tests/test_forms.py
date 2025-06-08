from django.test import TestCase
from django.contrib.auth import get_user_model
from ..models import Patient, PatientHospitalRecord
from ..forms import PatientForm, PatientHospitalRecordForm
from apps.hospitals.models import Hospital

User = get_user_model()


class PatientFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )

    def test_patient_form_valid(self):
        form = PatientForm({
            'name': 'Test Patient',
            'birthday': '1990-01-01',
            'status': Patient.Status.OUTPATIENT,
        })
        self.assertTrue(form.is_valid())

    def test_patient_form_invalid(self):
        # Missing required field (name)
        form = PatientForm({
            'birthday': '1990-01-01',
            'status': Patient.Status.OUTPATIENT,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)

    def test_patient_form_layout(self):
        form = PatientForm()
        self.assertIsNotNone(form.helper)
        self.assertEqual(form.helper.form_method, 'post')
        # Just verify that the layout exists and has content
        self.assertTrue(len(form.helper.layout.fields) > 0)


class HospitalRecordFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )

        cls.hospital = Hospital.objects.create(
            name='Test Hospital',
            created_by=cls.user,
            updated_by=cls.user
        )

        cls.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1980-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=cls.user,
            updated_by=cls.user
        )

    def test_hospital_record_form_valid(self):
        form = PatientHospitalRecordForm({
            'patient': self.patient.id,
            'hospital': self.hospital.id,
            'record_number': 'REC123',
            'first_admission_date': '2023-01-01',
        })
        self.assertTrue(form.is_valid())

    def test_hospital_record_form_invalid(self):
        # Missing required field (patient)
        form = PatientHospitalRecordForm({
            'record_number': 'REC123',
            'first_admission_date': '2023-01-01',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('patient', form.errors)

