from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import IntegrityError
from datetime import timedelta

from ..models import Patient, PatientRecordNumber, PatientAdmission

User = get_user_model()


class PatientRecordNumberModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', 
            email='test@example.com',
            profession='doctor'
        )
        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday=timezone.now().date() - timedelta(days=365*30),
            created_by=self.user,
            updated_by=self.user
        )
    
    def test_create_record_number(self):
        """Test creating a new record number"""
        record = PatientRecordNumber.objects.create(
            patient=self.patient,
            record_number='REC001',
            created_by=self.user,
            updated_by=self.user
        )
        
        self.assertEqual(record.record_number, 'REC001')
        self.assertTrue(record.is_current)
        self.assertEqual(record.patient, self.patient)
        self.assertIsNotNone(record.id)
    
    def test_unique_current_record_constraint(self):
        """Test that only one current record can exist per patient"""
        # Create first current record
        PatientRecordNumber.objects.create(
            patient=self.patient,
            record_number='REC001',
            is_current=True,
            created_by=self.user,
            updated_by=self.user
        )
        
        # This should work (will auto-deactivate the previous one via signals)
        record2 = PatientRecordNumber.objects.create(
            patient=self.patient,
            record_number='REC002',
            is_current=True,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Check that only one current record exists
        current_records = PatientRecordNumber.objects.filter(
            patient=self.patient,
            is_current=True
        )
        self.assertEqual(current_records.count(), 1)
        self.assertEqual(current_records.first().record_number, 'REC002')
    
    def test_record_number_validation(self):
        """Test record number validation"""
        # Empty record number should fail
        with self.assertRaises(ValidationError):
            record = PatientRecordNumber(
                patient=self.patient,
                record_number='',
                created_by=self.user,
                updated_by=self.user
            )
            record.full_clean()
        
        # Very short record number should fail
        with self.assertRaises(ValidationError):
            record = PatientRecordNumber(
                patient=self.patient,
                record_number='AB',
                created_by=self.user,
                updated_by=self.user
            )
            record.full_clean()
    
    def test_effective_date_validation(self):
        """Test effective date validation"""
        future_date = timezone.now() + timedelta(days=1)
        
        with self.assertRaises(ValidationError):
            record = PatientRecordNumber(
                patient=self.patient,
                record_number='REC001',
                effective_date=future_date,
                created_by=self.user,
                updated_by=self.user
            )
            record.full_clean()
    
    def test_record_number_history(self):
        """Test record number change history"""
        # Create initial record
        record1 = PatientRecordNumber.objects.create(
            patient=self.patient,
            record_number='REC001',
            change_reason='Initial setup',
            created_by=self.user,
            updated_by=self.user
        )
        
        # Create updated record
        record2 = PatientRecordNumber.objects.create(
            patient=self.patient,
            record_number='REC002',
            previous_record_number='REC001',
            change_reason='Hospital transfer',
            created_by=self.user,
            updated_by=self.user
        )
        
        # Check history
        history = self.patient.record_numbers.order_by('-effective_date')
        self.assertEqual(history.count(), 2)
        
        current = history.first()
        self.assertEqual(current.record_number, 'REC002')
        self.assertEqual(current.previous_record_number, 'REC001')
        self.assertTrue(current.is_current)
        
        previous = history.last()
        self.assertEqual(previous.record_number, 'REC001')
        self.assertFalse(previous.is_current)


class PatientAdmissionModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', 
            email='test@example.com',
            profession='doctor'
        )
        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday=timezone.now().date() - timedelta(days=365*30),
            created_by=self.user,
            updated_by=self.user
        )
    
    def test_create_admission(self):
        """Test creating a new admission"""
        admission_time = timezone.now()
        admission = PatientAdmission.objects.create(
            patient=self.patient,
            admission_datetime=admission_time,
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            created_by=self.user,
            updated_by=self.user
        )
        self.assertEqual(admission.admission_type, 'emergency')
        self.assertTrue(admission.is_active)
        self.assertIsNone(admission.discharge_datetime)
    
    def test_discharge_patient(self):
        """Test discharging a patient and duration calculation"""
        admission_time = timezone.now() - timedelta(days=3)
        discharge_time = timezone.now()
        
        admission = PatientAdmission.objects.create(
            patient=self.patient,
            admission_datetime=admission_time,
            discharge_datetime=discharge_time,
            discharge_type=PatientAdmission.DischargeType.MEDICAL,
            created_by=self.user,
            updated_by=self.user
        )
        
        self.assertFalse(admission.is_active)
        self.assertEqual(admission.stay_duration_days, 3)
        self.assertGreaterEqual(admission.stay_duration_hours, 72)

    def test_admission_str_method(self):
        """Test string representation of admission"""
        admission_time = timezone.now()
        admission = PatientAdmission.objects.create(
            patient=self.patient,
            admission_datetime=admission_time,
            admission_type=PatientAdmission.AdmissionType.SCHEDULED,
            created_by=self.user,
            updated_by=self.user
        )
        expected = f"{self.patient.name} - {admission_time.strftime('%d/%m/%Y')} - Ativa"
        self.assertEqual(str(admission), expected)

    def test_discharge_datetime_validation(self):
        """Test that discharge datetime must be after admission datetime"""
        admission_time = timezone.now()
        discharge_time = admission_time - timedelta(hours=1)  # Before admission
        
        with self.assertRaises(ValidationError):
            admission = PatientAdmission(
                patient=self.patient,
                admission_datetime=admission_time,
                discharge_datetime=discharge_time,
                discharge_type=PatientAdmission.DischargeType.MEDICAL,
                created_by=self.user,
                updated_by=self.user
            )
            admission.full_clean()

    def test_discharge_type_required_when_discharged(self):
        """Test that discharge type is required when discharge datetime is set"""
        admission_time = timezone.now() - timedelta(days=1)
        discharge_time = timezone.now()
        
        with self.assertRaises(ValidationError):
            admission = PatientAdmission(
                patient=self.patient,
                admission_datetime=admission_time,
                discharge_datetime=discharge_time,
                # discharge_type not set
                created_by=self.user,
                updated_by=self.user
            )
            admission.full_clean()

    def test_active_status_consistency(self):
        """Test that active status is consistent with discharge datetime"""
        admission_time = timezone.now() - timedelta(days=1)
        discharge_time = timezone.now()
        
        with self.assertRaises(ValidationError):
            admission = PatientAdmission(
                patient=self.patient,
                admission_datetime=admission_time,
                discharge_datetime=discharge_time,
                discharge_type=PatientAdmission.DischargeType.MEDICAL,
                is_active=True,  # Should be False when discharged
                created_by=self.user,
                updated_by=self.user
            )
            admission.full_clean()

    def test_calculate_current_duration(self):
        """Test calculating current duration for active admissions"""
        admission_time = timezone.now() - timedelta(days=2, hours=3)
        admission = PatientAdmission.objects.create(
            patient=self.patient,
            admission_datetime=admission_time,
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            created_by=self.user,
            updated_by=self.user
        )
        
        duration = admission.calculate_current_duration()
        self.assertIsNotNone(duration)
        self.assertGreaterEqual(duration['days'], 2)
        self.assertGreaterEqual(duration['hours'], 48)

    def test_unique_active_admission_constraint(self):
        """Test that only one active admission can exist per patient"""
        admission_time = timezone.now()
        
        # Create first active admission
        PatientAdmission.objects.create(
            patient=self.patient,
            admission_datetime=admission_time,
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            is_active=True,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Try to create second active admission - should raise integrity error
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            PatientAdmission.objects.create(
                patient=self.patient,
                admission_datetime=admission_time,
                admission_type=PatientAdmission.AdmissionType.SCHEDULED,
                is_active=True,
                created_by=self.user,
                updated_by=self.user
            )


class PatientIntegrationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', 
            email='test@example.com',
            profession='doctor'
        )
        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday=timezone.now().date() - timedelta(days=365*30),
            created_by=self.user,
            updated_by=self.user
        )
    
    def test_patient_record_number_methods(self):
        """Test patient record number management methods"""
        # Update record number
        record = self.patient.update_current_record_number(
            'REC001', self.user, 'Initial setup'
        )
        
        self.assertEqual(self.patient.current_record_number, 'REC001')
        self.assertEqual(record.record_number, 'REC001')
        self.assertTrue(record.is_current)
        
        # Update to new record number
        record2 = self.patient.update_current_record_number(
            'REC002', self.user, 'System migration'
        )
        
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.current_record_number, 'REC002')
        self.assertEqual(record2.previous_record_number, 'REC001')
        
        # Check old record was deactivated
        record.refresh_from_db()
        self.assertFalse(record.is_current)
    
    def test_patient_admission_methods(self):
        """Test patient admission management methods"""
        admission_time = timezone.now()
        
        # Admit patient
        admission = self.patient.admit_patient(
            admission_datetime=admission_time,
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            user=self.user,
            initial_bed='A101',
            admission_diagnosis='Emergency condition'
        )
        
        # Check patient status
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.status, Patient.Status.INPATIENT)
        self.assertEqual(self.patient.current_admission_id, admission.id)
        self.assertEqual(self.patient.bed, 'A101')
        self.assertTrue(self.patient.is_currently_admitted())
        
        # Discharge patient
        discharge_time = timezone.now() + timedelta(days=2)
        self.patient.discharge_patient(
            discharge_datetime=discharge_time,
            discharge_type=PatientAdmission.DischargeType.MEDICAL,
            user=self.user,
            final_bed='A101',
            discharge_diagnosis='Condition resolved'
        )
        
        # Check patient status after discharge
        self.patient.refresh_from_db()
        admission.refresh_from_db()

        self.assertEqual(self.patient.status, Patient.Status.OUTPATIENT)
        self.assertIsNone(self.patient.current_admission_id)
        self.assertEqual(self.patient.bed, '')
        self.assertIsNone(self.patient.ward)
        self.assertFalse(self.patient.is_currently_admitted())
        
        # Check admission record
        self.assertFalse(admission.is_active)
        self.assertEqual(admission.stay_duration_days, 2)
    
    def test_denormalized_field_consistency(self):
        """Test that denormalized fields stay consistent"""
        # Create multiple record numbers and admissions
        self.patient.update_current_record_number('REC001', self.user)
        
        # First admission
        admission1 = self.patient.admit_patient(
            admission_datetime=timezone.now() - timedelta(days=10),
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            user=self.user
        )
        self.patient.discharge_patient(
            discharge_datetime=timezone.now() - timedelta(days=5),
            discharge_type=PatientAdmission.DischargeType.MEDICAL,
            user=self.user
        )
        
        # Second admission
        admission2 = self.patient.admit_patient(
            admission_datetime=timezone.now() - timedelta(days=3),
            admission_type=PatientAdmission.AdmissionType.SCHEDULED,
            user=self.user
        )
        
        # Check denormalized fields
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.total_admissions_count, 2)
        self.assertEqual(self.patient.total_inpatient_days, 5)
        self.assertEqual(self.patient.current_admission_id, admission2.id)
        self.assertEqual(self.patient.current_record_number, 'REC001')
        
        # Test refresh method
        self.patient.refresh_denormalized_fields()
        self.patient.refresh_from_db()
        
        # Values should remain consistent
        self.assertEqual(self.patient.total_admissions_count, 2)
        self.assertEqual(self.patient.current_admission_id, admission2.id)
    
    def test_cannot_admit_already_admitted_patient(self):
        """Test business rule: cannot admit already admitted patient"""
        # Admit patient
        self.patient.admit_patient(
            admission_datetime=timezone.now(),
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            user=self.user
        )
        
        # Try to admit again
        with self.assertRaises(ValidationError) as cm:
            self.patient.admit_patient(
                admission_datetime=timezone.now(),
                admission_type=PatientAdmission.AdmissionType.SCHEDULED,
                user=self.user
            )
        
        self.assertIn('já está internado', str(cm.exception))
    
    def test_cannot_discharge_non_admitted_patient(self):
        """Test business rule: cannot discharge non-admitted patient"""
        with self.assertRaises(ValidationError) as cm:
            self.patient.discharge_patient(
                discharge_datetime=timezone.now(),
                discharge_type=PatientAdmission.DischargeType.MEDICAL,
                user=self.user
            )
        
        self.assertIn('não está internado', str(cm.exception))