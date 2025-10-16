from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from ..models import Patient, PatientRecordNumber, PatientAdmission

User = get_user_model()

class PatientBusinessLogicTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', email='test@example.com')
        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday=timezone.now().date() - timedelta(days=365*30),
            created_by=self.user,
            updated_by=self.user
        )
    
    def test_update_record_number_creates_history(self):
        """Test that updating record number creates proper history"""
        # Set initial record number
        self.patient.update_current_record_number('REC001', self.user, 'Initial setup')
        
        # Update to new record number
        self.patient.update_current_record_number('REC002', self.user, 'Hospital transfer')
        
        # Check history
        records = self.patient.record_numbers.order_by('-effective_date')
        self.assertEqual(records.count(), 2)
        
        current_record = records.first()
        old_record = records.last()
        
        self.assertEqual(current_record.record_number, 'REC002')
        self.assertTrue(current_record.is_current)
        self.assertEqual(current_record.previous_record_number, 'REC001')
        
        self.assertEqual(old_record.record_number, 'REC001')
        self.assertFalse(old_record.is_current)
    
    def test_admit_discharge_cycle(self):
        """Test complete admission and discharge cycle"""
        admission_time = timezone.now() - timedelta(hours=48)
        discharge_time = timezone.now()
        
        # Admit patient
        admission = self.patient.admit_patient(
            admission_datetime=admission_time,
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            user=self.user,
            initial_bed='A101',
            admission_diagnosis='Chest pain'
        )
        
        # Check patient status after admission
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.status, Patient.Status.INPATIENT)
        self.assertEqual(self.patient.current_admission_id, admission.id)
        self.assertEqual(self.patient.bed, 'A101')
        self.assertTrue(self.patient.is_currently_admitted())
        
        # Discharge patient
        self.patient.discharge_patient(
            discharge_datetime=discharge_time,
            discharge_type=PatientAdmission.DischargeType.MEDICAL,
            user=self.user,
            final_bed='A101',
            discharge_diagnosis='Stable, discharged home'
        )
        
        # Check patient status after discharge
        self.patient.refresh_from_db()
        admission.refresh_from_db()

        self.assertEqual(self.patient.status, Patient.Status.OUTPATIENT)
        self.assertIsNone(self.patient.current_admission_id)
        self.assertEqual(self.patient.bed, "")
        self.assertIsNone(self.patient.ward)
        self.assertFalse(self.patient.is_currently_admitted())
        
        # Check admission record
        self.assertFalse(admission.is_active)
        self.assertEqual(admission.stay_duration_days, 2)
        self.assertGreater(admission.stay_duration_hours, 47)
    
    def test_cannot_admit_already_admitted_patient(self):
        """Test that cannot admit patient who is already admitted"""
        # Admit patient
        self.patient.admit_patient(
            admission_datetime=timezone.now(),
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            user=self.user
        )
        
        # Try to admit again
        with self.assertRaises(ValidationError):
            self.patient.admit_patient(
                admission_datetime=timezone.now(),
                admission_type=PatientAdmission.AdmissionType.SCHEDULED,
                user=self.user
            )
    
    def test_denormalized_field_consistency(self):
        """Test that denormalized fields stay consistent"""
        # Create multiple admissions and record changes
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
        self.assertEqual(self.patient.total_inpatient_days, 5)  # First admission was 5 days
        self.assertEqual(self.patient.current_admission_id, admission2.id)
        self.assertEqual(self.patient.current_record_number, 'REC001')

    def test_cannot_discharge_non_admitted_patient(self):
        """Test that cannot discharge patient who is not admitted"""
        with self.assertRaises(ValidationError):
            self.patient.discharge_patient(
                discharge_datetime=timezone.now(),
                discharge_type=PatientAdmission.DischargeType.MEDICAL,
                user=self.user
            )
    
    def test_admission_duration_calculation(self):
        """Test that admission duration is calculated correctly"""
        admission_time = timezone.now() - timedelta(hours=25)  # Just over 1 day
        
        admission = self.patient.admit_patient(
            admission_datetime=admission_time,
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            user=self.user
        )
        
        # Test current duration for active admission
        duration = admission.calculate_current_duration()
        self.assertIsNotNone(duration)
        self.assertGreater(duration['hours'], 24)
        self.assertEqual(duration['days'], 1)
        
        # Discharge and check final duration
        discharge_time = timezone.now()
        self.patient.discharge_patient(
            discharge_datetime=discharge_time,
            discharge_type=PatientAdmission.DischargeType.MEDICAL,
            user=self.user
        )
        
        admission.refresh_from_db()
        self.assertEqual(admission.stay_duration_days, 1)
        self.assertGreater(admission.stay_duration_hours, 24)
    
    def test_refresh_denormalized_fields(self):
        """Test that refresh_denormalized_fields works correctly"""
        # Create data
        self.patient.update_current_record_number('REC001', self.user)
        admission = self.patient.admit_patient(
            admission_datetime=timezone.now() - timedelta(days=3),
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            user=self.user,
            initial_bed='A101'
        )
        
        # Manually corrupt denormalized fields
        Patient.objects.filter(pk=self.patient.pk).update(
            current_record_number='WRONG',
            total_admissions_count=999,
            current_admission_id=None,
            status=Patient.Status.OUTPATIENT,
            bed=''
        )
        
        # Refresh and verify correction
        self.patient.refresh_from_db()
        self.patient.refresh_denormalized_fields()
        
        self.assertEqual(self.patient.current_record_number, 'REC001')
        self.assertEqual(self.patient.total_admissions_count, 1)
        self.assertEqual(self.patient.current_admission_id, admission.id)
        self.assertEqual(self.patient.status, Patient.Status.INPATIENT)
        self.assertEqual(self.patient.bed, 'A101')
    
    def test_cancel_discharge(self):
        """Test that discharge can be cancelled"""
        # Admit and discharge patient
        admission = self.patient.admit_patient(
            admission_datetime=timezone.now() - timedelta(days=2),
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            user=self.user,
            initial_bed='A101'
        )
        
        self.patient.discharge_patient(
            discharge_datetime=timezone.now(),
            discharge_type=PatientAdmission.DischargeType.MEDICAL,
            user=self.user
        )
        
        # Verify discharge
        admission.refresh_from_db()
        self.assertFalse(admission.is_active)
        self.assertIsNotNone(admission.discharge_datetime)
        
        # Cancel discharge
        admission.cancel_discharge(self.user)
        
        # Verify cancellation
        admission.refresh_from_db()
        self.patient.refresh_from_db()
        
        self.assertTrue(admission.is_active)
        self.assertIsNone(admission.discharge_datetime)
        self.assertEqual(self.patient.status, Patient.Status.INPATIENT)
        self.assertEqual(self.patient.current_admission_id, admission.id)
    
    def test_get_admission_and_record_history(self):
        """Test history retrieval methods"""
        # Create multiple records and admissions
        self.patient.update_current_record_number('REC001', self.user)
        self.patient.update_current_record_number('REC002', self.user)
        
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
        
        admission2 = self.patient.admit_patient(
            admission_datetime=timezone.now() - timedelta(days=3),
            admission_type=PatientAdmission.AdmissionType.SCHEDULED,
            user=self.user
        )
        
        # Test history methods
        admission_history = self.patient.get_admission_history()
        self.assertEqual(admission_history.count(), 2)
        self.assertEqual(admission_history.first(), admission2)  # Most recent first
        
        record_history = self.patient.get_record_number_history()
        self.assertEqual(record_history.count(), 2)
        self.assertEqual(record_history.first().record_number, 'REC002')  # Most recent first
    
    def test_total_hospital_days_calculation(self):
        """Test total hospital days calculation across multiple admissions"""
        # First admission: 3 days
        admission1 = self.patient.admit_patient(
            admission_datetime=timezone.now() - timedelta(days=10),
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            user=self.user
        )
        self.patient.discharge_patient(
            discharge_datetime=timezone.now() - timedelta(days=7),
            discharge_type=PatientAdmission.DischargeType.MEDICAL,
            user=self.user
        )
        
        # Second admission: 2 days
        admission2 = self.patient.admit_patient(
            admission_datetime=timezone.now() - timedelta(days=5),
            admission_type=PatientAdmission.AdmissionType.SCHEDULED,
            user=self.user
        )
        self.patient.discharge_patient(
            discharge_datetime=timezone.now() - timedelta(days=3),
            discharge_type=PatientAdmission.DischargeType.MEDICAL,
            user=self.user
        )
        
        # Check total
        total_days = self.patient.calculate_total_hospital_days()
        self.assertEqual(total_days, 5)  # 3 + 2 days
        
        # Check denormalized field
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.total_inpatient_days, 5)