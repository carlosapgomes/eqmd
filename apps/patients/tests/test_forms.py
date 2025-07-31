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
            'gender': Patient.GenderChoices.MALE,
        })
        self.assertTrue(form.is_valid())

    def test_patient_form_requires_gender(self):
        """Test that patient form requires gender field"""
        form = PatientForm({
            'name': 'Test Patient',
            'birthday': '1990-01-01',
        })
        # Gender field is required in the form
        self.assertFalse(form.is_valid())
        self.assertIn('gender', form.errors)

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

    def test_patient_form_includes_gender_field(self):
        """Test that gender field is included in patient form"""
        form = PatientForm()
        self.assertIn('gender', form.fields)

    def test_patient_form_gender_choices(self):
        """Test that patient form gender field has correct choices"""
        form = PatientForm()
        gender_field = form.fields['gender']
        
        # Get choices as tuples
        form_choices = list(gender_field.choices)
        model_choices = list(Patient.GenderChoices.choices)
        
        # Should have the same choices as the model
        self.assertEqual(form_choices, model_choices)

    def test_patient_form_gender_validation(self):
        """Test patient form validation with different gender values"""
        # Test all valid gender choices
        valid_genders = [
            Patient.GenderChoices.MALE,
            Patient.GenderChoices.FEMALE,
            Patient.GenderChoices.OTHER,
            Patient.GenderChoices.NOT_INFORMED
        ]
        
        for gender in valid_genders:
            form = PatientForm({
                'name': 'Test Patient',
                'birthday': '1990-01-01',
                'gender': gender,
            })
            self.assertTrue(form.is_valid(), f"Form should be valid with gender={gender}")

    def test_patient_form_invalid_gender(self):
        """Test patient form validation with invalid gender value"""
        form = PatientForm({
            'name': 'Test Patient',
            'birthday': '1990-01-01',
            'gender': 'INVALID_CHOICE',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('gender', form.errors)

    def test_patient_form_no_tag_field(self):
        """Test that PatientForm no longer includes tag_selection field after refactor"""
        form = PatientForm()
        self.assertNotIn('tag_selection', form.fields)
        
    def test_patient_form_save_without_tags(self):
        """Test that PatientForm saves correctly without tag functionality"""
        form_data = {
            'name': 'Test Patient',
            'birthday': '1990-01-01',
            'gender': Patient.GenderChoices.MALE,
        }
        
        form = PatientForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        # Save form without tags
        patient = form.save(commit=False)
        patient.created_by = self.user
        patient.updated_by = self.user
        patient.save()
        
        # Verify patient was created without tags
        self.assertEqual(patient.name, 'Test Patient')
        self.assertEqual(patient.tags.count(), 0)
        self.assertEqual(patient.created_by, self.user)


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
