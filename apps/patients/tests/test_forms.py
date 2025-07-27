from django.test import TestCase
from django.contrib.auth import get_user_model
from ..models import Patient, AllowedTag, Ward
from ..forms import (
    PatientForm, AdmitPatientForm, DischargePatientForm,
    EmergencyAdmissionForm, TransferPatientForm, DeclareDeathForm, 
    SetOutpatientForm
)

User = get_user_model()


class PatientFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        cls.ward = Ward.objects.create(
            name='Test Ward',
            abbreviation='TW',
            created_by=cls.user,
            updated_by=cls.user
        )

    def test_patient_form_valid(self):
        """Test that patient form is valid without status field"""
        form = PatientForm({
            'name': 'Test Patient',
            'birthday': '1990-01-01',
        })
        self.assertTrue(form.is_valid())

    def test_patient_form_invalid(self):
        # Missing required field (name)
        form = PatientForm({
            'birthday': '1990-01-01',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)

    def test_patient_form_excludes_status_field(self):
        """Test that status field is excluded from patient form"""
        form = PatientForm()
        self.assertNotIn('status', form.fields)


class StatusChangeFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        cls.ward = Ward.objects.create(
            name='Test Ward',
            abbreviation='TW',
            created_by=cls.user,
            updated_by=cls.user
        )

    def test_admit_patient_form_valid(self):
        """Test admit patient form validation"""
        form = AdmitPatientForm({
            'ward': self.ward.id,
            'bed': 'A101',
            'reason': 'Patient needs inpatient care',
        })
        self.assertTrue(form.is_valid())

    def test_admit_patient_form_requires_ward(self):
        """Test that ward is required for admission"""
        form = AdmitPatientForm({
            'bed': 'A101',
            'reason': 'Patient needs inpatient care',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('ward', form.errors)

    def test_discharge_patient_form_valid(self):
        """Test discharge patient form validation"""
        form = DischargePatientForm({
            'discharge_reason': 'Patient recovered fully',
            'reason': 'Medical discharge',
        })
        self.assertTrue(form.is_valid())

    def test_discharge_patient_form_requires_discharge_reason(self):
        """Test that discharge reason is required"""
        form = DischargePatientForm({
            'reason': 'Medical discharge',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('discharge_reason', form.errors)

    def test_emergency_admission_form_valid(self):
        """Test emergency admission form validation"""
        form = EmergencyAdmissionForm({
            'ward': self.ward.id,
            'bed': 'ER-01',
            'reason': 'Emergency situation',
        })
        self.assertTrue(form.is_valid())

    def test_emergency_admission_form_ward_optional(self):
        """Test that ward is optional for emergency admission"""
        form = EmergencyAdmissionForm({
            'bed': 'ER-01',
            'reason': 'Emergency situation',
        })
        self.assertTrue(form.is_valid())

    def test_transfer_patient_form_valid(self):
        """Test transfer patient form validation"""
        form = TransferPatientForm({
            'destination': 'Another Hospital',
            'reason': 'Specialized care required',
        })
        self.assertTrue(form.is_valid())

    def test_transfer_patient_form_requires_destination(self):
        """Test that destination is required for transfer"""
        form = TransferPatientForm({
            'reason': 'Specialized care required',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('destination', form.errors)

    def test_declare_death_form_valid(self):
        """Test declare death form validation"""
        form = DeclareDeathForm({
            'death_time': '2023-01-01T10:00:00',
            'reason': 'Heart failure',
        })
        self.assertTrue(form.is_valid())

    def test_declare_death_form_requires_fields(self):
        """Test that death time and reason are required"""
        form = DeclareDeathForm({})
        self.assertFalse(form.is_valid())
        self.assertIn('death_time', form.errors)
        self.assertIn('reason', form.errors)

    def test_set_outpatient_form_valid(self):
        """Test set outpatient form validation"""
        form = SetOutpatientForm({
            'follow_up_date': '2023-02-01',
            'follow_up_notes': 'Return in 2 weeks',
            'reason': 'Stable for outpatient care',
        })
        self.assertTrue(form.is_valid())

    def test_set_outpatient_form_all_fields_optional(self):
        """Test that all fields are optional for outpatient status"""
        form = SetOutpatientForm({})
        self.assertTrue(form.is_valid())
