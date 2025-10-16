from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from ..models import Patient, PatientRecordNumber, PatientAdmission
from apps.events.models import Event, RecordNumberChangeEvent, AdmissionEvent, DischargeEvent

User = get_user_model()

class SignalTests(TestCase):
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
    
    def test_record_number_creates_event(self):
        """Test that creating record number creates timeline event"""
        record = PatientRecordNumber.objects.create(
            patient=self.patient,
            record_number='REC001',
            change_reason='Initial setup',
            created_by=self.user,
            updated_by=self.user
        )
        
        # Check that event was created
        event = RecordNumberChangeEvent.objects.filter(record_change=record).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.patient, self.patient)
        self.assertEqual(event.new_record_number, 'REC001')
        self.assertEqual(event.change_reason, 'Initial setup')
    
    def test_admission_creates_events(self):
        """Test that admission creates timeline events"""
        admission_time = timezone.now() - timedelta(days=2)
        discharge_time = timezone.now()
        
        # Create admission
        admission = PatientAdmission.objects.create(
            patient=self.patient,
            admission_datetime=admission_time,
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Check admission event was created
        admission_event = AdmissionEvent.objects.filter(admission=admission).first()
        self.assertIsNotNone(admission_event)
        self.assertEqual(admission_event.patient, self.patient)
        self.assertEqual(admission_event.event_datetime, admission_time)
        
        # Now discharge patient
        admission.discharge_datetime = discharge_time
        admission.discharge_type = PatientAdmission.DischargeType.MEDICAL
        admission.save()
        
        # Check discharge event was created
        discharge_event = DischargeEvent.objects.filter(admission=admission).first()
        self.assertIsNotNone(discharge_event)
        self.assertEqual(discharge_event.patient, self.patient)
        self.assertEqual(discharge_event.event_datetime, discharge_time)
    
    def test_patient_denormalization_updates(self):
        """Test that patient denormalized fields are updated via signals"""
        # Create record number
        record = PatientRecordNumber.objects.create(
            patient=self.patient,
            record_number='REC001',
            created_by=self.user,
            updated_by=self.user
        )
        
        # Check patient was updated
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.current_record_number, 'REC001')
        
        # Create admission
        admission = PatientAdmission.objects.create(
            patient=self.patient,
            admission_datetime=timezone.now(),
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            initial_bed='A101',
            created_by=self.user,
            updated_by=self.user
        )
        
        # Check patient status was updated
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.status, Patient.Status.INPATIENT)
        self.assertEqual(self.patient.current_admission_id, admission.id)
        self.assertEqual(self.patient.bed, 'A101')
        self.assertEqual(self.patient.total_admissions_count, 1)
    
    def test_record_deletion_cleanup(self):
        """Test cleanup when record number is deleted"""
        # Create record and event
        record = PatientRecordNumber.objects.create(
            patient=self.patient,
            record_number='REC001',
            is_current=False,  # Make it deletable
            created_by=self.user,
            updated_by=self.user
        )
        
        # Verify event exists
        event = RecordNumberChangeEvent.objects.filter(record_change=record).first()
        self.assertIsNotNone(event)
        
        # Delete record
        record.delete()
        
        # Verify event was also deleted
        event_exists = RecordNumberChangeEvent.objects.filter(pk=event.pk).exists()
        self.assertFalse(event_exists)
    
    def test_admission_deletion_cleanup(self):
        """Test cleanup when admission is deleted"""
        # Create admission
        admission = PatientAdmission.objects.create(
            patient=self.patient,
            admission_datetime=timezone.now() - timedelta(days=1),
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Update patient to reflect admission
        self.patient.refresh_from_db()
        original_admission_id = self.patient.current_admission_id
        
        # Verify events exist
        admission_event = AdmissionEvent.objects.filter(admission=admission).first()
        self.assertIsNotNone(admission_event)
        
        # Delete admission
        admission.delete()
        
        # Verify events were deleted
        admission_event_exists = AdmissionEvent.objects.filter(pk=admission_event.pk).exists()
        self.assertFalse(admission_event_exists)
        
        # Verify patient was updated
        self.patient.refresh_from_db()
        self.assertIsNone(self.patient.current_admission_id)
    
    def test_record_number_update_deactivates_previous(self):
        """Test that creating new current record deactivates previous one"""
        # Create first record
        record1 = PatientRecordNumber.objects.create(
            patient=self.patient,
            record_number='REC001',
            is_current=True,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Create second record
        record2 = PatientRecordNumber.objects.create(
            patient=self.patient,
            record_number='REC002',
            is_current=True,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Check that first record is no longer current
        record1.refresh_from_db()
        self.assertFalse(record1.is_current)
        
        # Check that second record is current
        self.assertTrue(record2.is_current)
        
        # Check patient denormalized field
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.current_record_number, 'REC002')
    
    def test_discharge_updates_patient_status(self):
        """Test that discharge updates patient status via signals"""
        # Admit patient
        admission = PatientAdmission.objects.create(
            patient=self.patient,
            admission_datetime=timezone.now(),
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Check patient is admitted
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.status, Patient.Status.INPATIENT)
        
        # Discharge patient
        admission.discharge_datetime = timezone.now()
        admission.discharge_type = PatientAdmission.DischargeType.MEDICAL
        admission.save()
        
        # Check patient is discharged
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.status, Patient.Status.OUTPATIENT)
        self.assertIsNone(self.patient.current_admission_id)
        self.assertEqual(self.patient.bed, '')
        self.assertIsNone(self.patient.ward)
    
    def test_admission_denormalized_fields_calculation(self):
        """Test that admission denormalized fields are calculated correctly"""
        # Create multiple admissions
        admission1 = PatientAdmission.objects.create(
            patient=self.patient,
            admission_datetime=timezone.now() - timedelta(days=10),
            discharge_datetime=timezone.now() - timedelta(days=5),
            discharge_type=PatientAdmission.DischargeType.MEDICAL,
            created_by=self.user,
            updated_by=self.user
        )
        
        admission2 = PatientAdmission.objects.create(
            patient=self.patient,
            admission_datetime=timezone.now() - timedelta(days=3),
            discharge_datetime=timezone.now() - timedelta(days=1),
            discharge_type=PatientAdmission.DischargeType.MEDICAL,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Check denormalized fields
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.total_admissions_count, 2)
        self.assertEqual(self.patient.total_inpatient_days, 7)  # 5 + 2 days
    
    def test_multiple_events_creation(self):
        """Test that multiple events are created correctly"""
        # Create record number
        record = PatientRecordNumber.objects.create(
            patient=self.patient,
            record_number='REC001',
            change_reason='Initial setup',
            created_by=self.user,
            updated_by=self.user
        )
        
        # Admit patient
        admission = PatientAdmission.objects.create(
            patient=self.patient,
            admission_datetime=timezone.now() - timedelta(days=2),
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Discharge patient
        admission.discharge_datetime = timezone.now()
        admission.discharge_type = PatientAdmission.DischargeType.MEDICAL
        admission.save()
        
        # Update record number
        record2 = PatientRecordNumber.objects.create(
            patient=self.patient,
            record_number='REC002',
            change_reason='Updated',
            created_by=self.user,
            updated_by=self.user
        )
        
        # Check all events were created
        record_events = RecordNumberChangeEvent.objects.filter(patient=self.patient)
        self.assertEqual(record_events.count(), 2)
        
        admission_events = AdmissionEvent.objects.filter(patient=self.patient)
        self.assertEqual(admission_events.count(), 1)
        
        discharge_events = DischargeEvent.objects.filter(patient=self.patient)
        self.assertEqual(discharge_events.count(), 1)
        
        # Check event ordering
        all_events = Event.objects.filter(patient=self.patient).order_by('event_datetime')
        self.assertEqual(all_events.count(), 4)
    
    def test_signal_error_handling(self):
        """Test that signals handle errors gracefully"""
        # Create record number
        record = PatientRecordNumber.objects.create(
            patient=self.patient,
            record_number='REC001',
            created_by=self.user,
            updated_by=self.user
        )
        
        # Manually delete the event to test error handling
        RecordNumberChangeEvent.objects.filter(record_change=record).delete()
        
        # Update record - should not fail
        record.record_number = 'REC001_UPDATED'
        record.save()
        
        # Should still work
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.current_record_number, 'REC001_UPDATED')