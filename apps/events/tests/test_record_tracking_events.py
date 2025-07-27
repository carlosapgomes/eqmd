from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from apps.patients.models import Patient, PatientRecordNumber, PatientAdmission
from ..models import RecordNumberChangeEvent, AdmissionEvent, DischargeEvent

User = get_user_model()

class EventIntegrationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', email='test@example.com')
        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday=timezone.now().date() - timedelta(days=365*30),
            created_by=self.user,
            updated_by=self.user
        )
    
    def test_record_number_creates_event(self):
        """Test that creating a record number creates a timeline event"""
        record = PatientRecordNumber.objects.create(
            patient=self.patient,
            record_number='REC001',
            created_by=self.user,
            updated_by=self.user
        )
        
        # Check that event was created
        event = RecordNumberChangeEvent.objects.filter(record_change=record).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.patient, self.patient)
        self.assertEqual(event.new_record_number, 'REC001')
    
    def test_admission_creates_events(self):
        """Test that admission and discharge create timeline events"""
        admission_time = timezone.now() - timedelta(days=2)
        discharge_time = timezone.now()
        
        admission = PatientAdmission.objects.create(
            patient=self.patient,
            admission_datetime=admission_time,
            discharge_datetime=discharge_time,
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            discharge_type=PatientAdmission.DischargeType.MEDICAL,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Check admission event
        admission_event = AdmissionEvent.objects.filter(admission=admission).first()
        self.assertIsNotNone(admission_event)
        self.assertEqual(admission_event.patient, self.patient)
        
        # Check discharge event
        discharge_event = DischargeEvent.objects.filter(admission=admission).first()
        self.assertIsNotNone(discharge_event)
        self.assertEqual(discharge_event.patient, self.patient)
        self.assertEqual(discharge_event.stay_duration_days, 2)
    
    def test_record_number_event_sync(self):
        """Test that record number changes sync with event data"""
        record = PatientRecordNumber.objects.create(
            patient=self.patient,
            record_number='REC001',
            previous_record_number='OLD001',
            change_reason='Testing sync',
            created_by=self.user,
            updated_by=self.user
        )
        
        event = RecordNumberChangeEvent.objects.filter(record_change=record).first()
        self.assertEqual(event.old_record_number, 'OLD001')
        self.assertEqual(event.new_record_number, 'REC001')
        self.assertEqual(event.change_reason, 'Testing sync')
    
    def test_admission_event_sync(self):
        """Test that admission changes sync with event data"""
        admission_time = timezone.now() - timedelta(days=1)
        
        admission = PatientAdmission.objects.create(
            patient=self.patient,
            admission_datetime=admission_time,
            admission_type=PatientAdmission.AdmissionType.SCHEDULED,
            initial_bed='Room 101',
            admission_diagnosis='Test diagnosis',
            created_by=self.user,
            updated_by=self.user
        )
        
        event = AdmissionEvent.objects.filter(admission=admission).first()
        self.assertEqual(event.admission_type, admission.get_admission_type_display())
        self.assertEqual(event.initial_bed, 'Room 101')
        self.assertEqual(event.admission_diagnosis, 'Test diagnosis')
    
    def test_discharge_event_sync(self):
        """Test that discharge changes sync with event data"""
        admission_time = timezone.now() - timedelta(days=3)
        discharge_time = timezone.now()
        
        admission = PatientAdmission.objects.create(
            patient=self.patient,
            admission_datetime=admission_time,
            discharge_datetime=discharge_time,
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            discharge_type=PatientAdmission.DischargeType.MEDICAL,
            final_bed='Room 205',
            discharge_diagnosis='Recovered',
            created_by=self.user,
            updated_by=self.user
        )
        
        event = DischargeEvent.objects.filter(admission=admission).first()
        self.assertEqual(event.discharge_type, admission.get_discharge_type_display())
        self.assertEqual(event.final_bed, 'Room 205')
        self.assertEqual(event.discharge_diagnosis, 'Recovered')
        self.assertEqual(event.stay_duration_days, 3)
    
    def test_record_number_deletion_removes_event(self):
        """Test that deleting record number removes timeline event"""
        record = PatientRecordNumber.objects.create(
            patient=self.patient,
            record_number='REC001',
            created_by=self.user,
            updated_by=self.user
        )
        
        # Verify event exists
        event = RecordNumberChangeEvent.objects.filter(record_change=record).first()
        self.assertIsNotNone(event)
        
        # Get record ID before deletion
        record_id = record.id
        
        # Delete record and verify event is removed
        record.delete()
        event_count = RecordNumberChangeEvent.objects.filter(record_change_id=record_id).count()
        self.assertEqual(event_count, 0)
    
    def test_admission_deletion_removes_events(self):
        """Test that deleting admission removes timeline events"""
        admission = PatientAdmission.objects.create(
            patient=self.patient,
            admission_datetime=timezone.now() - timedelta(days=1),
            discharge_datetime=timezone.now(),
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            discharge_type=PatientAdmission.DischargeType.MEDICAL,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Verify events exist
        admission_event = AdmissionEvent.objects.filter(admission=admission).first()
        discharge_event = DischargeEvent.objects.filter(admission=admission).first()
        self.assertIsNotNone(admission_event)
        self.assertIsNotNone(discharge_event)
        
        # Get admission ID before deletion
        admission_id = admission.id
        
        # Delete admission and verify events are removed
        admission.delete()
        admission_event_count = AdmissionEvent.objects.filter(admission_id=admission_id).count()
        discharge_event_count = DischargeEvent.objects.filter(admission_id=admission_id).count()
        self.assertEqual(admission_event_count, 0)
        self.assertEqual(discharge_event_count, 0)
    
    def test_discharge_cancellation_removes_discharge_event(self):
        """Test that cancelling discharge removes discharge event but keeps admission event"""
        admission = PatientAdmission.objects.create(
            patient=self.patient,
            admission_datetime=timezone.now() - timedelta(days=1),
            discharge_datetime=timezone.now(),
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            discharge_type=PatientAdmission.DischargeType.MEDICAL,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Verify both events exist
        admission_event = AdmissionEvent.objects.filter(admission=admission).first()
        discharge_event = DischargeEvent.objects.filter(admission=admission).first()
        self.assertIsNotNone(admission_event)
        self.assertIsNotNone(discharge_event)
        
        # Cancel discharge - set datetime to None and clear type 
        admission.discharge_datetime = None
        admission.discharge_type = ''  # Use empty string instead of None since field is not nullable
        admission.save()
        
        # Verify admission event still exists but discharge event is removed
        admission_event_after = AdmissionEvent.objects.filter(admission=admission).first()
        discharge_event_after = DischargeEvent.objects.filter(admission=admission).first()
        self.assertIsNotNone(admission_event_after)
        self.assertIsNone(discharge_event_after)