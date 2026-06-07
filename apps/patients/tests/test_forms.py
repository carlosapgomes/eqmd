from datetime import datetime
from unittest.mock import patch

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from ..models import Patient, AllowedTag, Ward, PatientRecordNumber, PatientAdmission
from ..forms import (
    PatientForm, AdmitPatientForm, DischargePatientForm,
    EmergencyAdmissionForm, TransferPatientForm, DeclareDeathForm,
    SetOutpatientForm
)

User = get_user_model()


VALID_RECORD_NUMBER = "REC001"


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
        """Test that patient form is valid with required fields including initial_record_number"""
        form = PatientForm({
            'name': 'Test Patient',
            'birthday': '1990-01-01',
            'gender': Patient.GenderChoices.MALE,
            'initial_record_number': VALID_RECORD_NUMBER,
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
                'initial_record_number': VALID_RECORD_NUMBER,
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
            'initial_record_number': VALID_RECORD_NUMBER,
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
        self.assertEqual(patient.patient_tags.count(), 0)
        self.assertEqual(patient.created_by, self.user)

    # --- Slice 01: initial_record_number tests ---

    def test_patient_form_requires_initial_record_number(self):
        """Form is invalid when initial_record_number is missing"""
        form = PatientForm({
            'name': 'Test Patient',
            'birthday': '1990-01-01',
            'gender': Patient.GenderChoices.MALE,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('initial_record_number', form.errors)

    def test_patient_form_invalid_initial_record_number_format(self):
        """Form is invalid when initial_record_number violates validate_record_number_format"""
        form = PatientForm({
            'name': 'Test Patient',
            'birthday': '1990-01-01',
            'gender': Patient.GenderChoices.MALE,
            'initial_record_number': 'AB',  # fewer than 3 chars
        })
        self.assertFalse(form.is_valid())
        self.assertIn('initial_record_number', form.errors)

    def test_patient_form_save_creates_patient_record_number(self):
        """Saving a valid PatientForm creates exactly one current PatientRecordNumber"""
        form = PatientForm({
            'name': 'Test Patient',
            'birthday': '1990-01-01',
            'gender': Patient.GenderChoices.MALE,
            'initial_record_number': VALID_RECORD_NUMBER,
        })
        self.assertTrue(form.is_valid())

        form.instance.created_by = self.user
        form.instance.updated_by = self.user
        form.current_user = self.user
        patient = form.save(commit=True)

        record_numbers = PatientRecordNumber.objects.filter(patient=patient)
        self.assertEqual(record_numbers.count(), 1)
        record = record_numbers.first()
        self.assertTrue(record.is_current)
        self.assertEqual(record.record_number, VALID_RECORD_NUMBER)

    def test_patient_form_save_updates_current_record_number(self):
        """Saving a valid PatientForm updates patient.current_record_number"""
        form = PatientForm({
            'name': 'Test Patient',
            'birthday': '1990-01-01',
            'gender': Patient.GenderChoices.MALE,
            'initial_record_number': VALID_RECORD_NUMBER,
        })
        self.assertTrue(form.is_valid())

        form.instance.created_by = self.user
        form.instance.updated_by = self.user
        form.current_user = self.user
        patient = form.save(commit=True)

        patient.refresh_from_db()
        self.assertEqual(patient.current_record_number, VALID_RECORD_NUMBER)

    def test_patient_form_save_rollback_on_record_number_failure(self):
        """If PatientRecordNumber creation fails, no partial Patient remains"""
        form = PatientForm({
            'name': 'Rollback Patient',
            'birthday': '1990-01-01',
            'gender': Patient.GenderChoices.MALE,
            'initial_record_number': VALID_RECORD_NUMBER,
        })
        self.assertTrue(form.is_valid())

        form.instance.created_by = self.user
        form.instance.updated_by = self.user
        form.current_user = self.user

        patient_count_before = Patient.objects.count()
        record_count_before = PatientRecordNumber.objects.count()

        with patch(
            'apps.patients.models.PatientRecordNumber.objects.create',
            side_effect=Exception("DB failure"),
        ):
            with self.assertRaises(Exception):
                form.save(commit=True)

        self.assertEqual(Patient.objects.count(), patient_count_before)
        self.assertEqual(PatientRecordNumber.objects.count(), record_count_before)


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
        now_str = timezone.now().strftime('%Y-%m-%dT%H:%M')
        form = AdmitPatientForm({
            'admission_datetime': now_str,
            'admission_type': PatientAdmission.AdmissionType.EMERGENCY,
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
        now_str = timezone.now().strftime('%Y-%m-%dT%H:%M')
        form = DischargePatientForm({
            'discharge_datetime': now_str,
            'discharge_type': PatientAdmission.DischargeType.MEDICAL,
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
