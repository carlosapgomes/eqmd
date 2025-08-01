from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.events.models import Event
from apps.patients.models import Patient
from datetime import datetime, timedelta

User = get_user_model()


class TestEventHistory(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='doctor',
            email='doctor@example.com',
            profession_type='doctor'
        )
        self.patient = Patient.objects.create(
            name='Test Patient',
            created_by=self.user
        )
        
    def test_event_creation_history(self):
        """Test that event creation is tracked."""
        event = Event.objects.create(
            patient=self.patient,
            event_type=Event.HISTORY_PHYSICAL_EVENT,
            description='Initial history and physical examination',
            created_by=self.user
        )
        
        # Check history record created
        history = event.history.first()
        self.assertEqual(history.history_type, '+')
        self.assertEqual(history.history_user, self.user)
        self.assertEqual(history.description, 'Initial history and physical examination')
        self.assertEqual(history.event_type, Event.HISTORY_PHYSICAL_EVENT)
        
    def test_event_modification_history(self):
        """Test that event modifications are tracked."""
        event = Event.objects.create(
            patient=self.patient,
            event_type=Event.HISTORY_PHYSICAL_EVENT,
            description='Original description',
            created_by=self.user
        )
        
        # Modify event
        event.description = 'Updated description with additional findings'
        event.event_type = Event.DAILY_NOTE_EVENT
        event._change_reason = 'Updated description and changed event type'
        event.save()
        
        # Check history records
        history_records = list(event.history.all())
        self.assertEqual(len(history_records), 2)
        
        # Latest change
        latest = history_records[0]
        self.assertEqual(latest.history_type, '~')
        self.assertEqual(latest.description, 'Updated description with additional findings')
        self.assertEqual(latest.event_type, Event.DAILY_NOTE_EVENT)
        self.assertEqual(latest.history_change_reason, 'Updated description and changed event type')
        
    def test_event_deletion_attempt_tracking(self):
        """Test tracking of event deletion attempts."""
        event = Event.objects.create(
            patient=self.patient,
            event_type=Event.DAILY_NOTE_EVENT,
            description='Daily note to be deleted',
            created_by=self.user
        )
        
        event_id = event.id
        
        # Delete event (this should be tracked)
        event._change_reason = 'Event deleted by user request'
        event.delete()
        
        # Check deletion is tracked in history
        deletion_history = Event.history.filter(
            id=event_id,
            history_type='-'
        ).first()
        
        self.assertIsNotNone(deletion_history)
        self.assertEqual(deletion_history.history_change_reason, 'Event deleted by user request')
        
    def test_critical_event_modifications(self):
        """Test tracking of critical medical event modifications."""
        # Create a critical medical event
        event = Event.objects.create(
            patient=self.patient,
            event_type=Event.PHOTO_EVENT,
            description='Critical medical imaging',
            created_by=self.user
        )
        
        # Simulate unauthorized modification
        event.description = 'Modified medical imaging description'
        event._change_reason = 'Unauthorized modification detected'
        event.save()
        
        # Check modification is tracked
        modification = event.history.filter(history_type='~').first()
        self.assertIsNotNone(modification)
        self.assertEqual(modification.description, 'Modified medical imaging description')
        self.assertEqual(modification.history_change_reason, 'Unauthorized modification detected')
        
    def test_event_audit_trail_integrity(self):
        """Test that complete audit trail is maintained for events."""
        event = Event.objects.create(
            patient=self.patient,
            event_type=Event.DAILY_NOTE_EVENT,
            description='Initial daily note',
            created_by=self.user
        )
        
        # Multiple modifications to test audit trail
        modifications = [
            ('Updated with morning observations', 'Morning update'),
            ('Added afternoon findings', 'Afternoon update'),
            ('Final notes added', 'End of day update')
        ]
        
        for description, reason in modifications:
            event.description = description
            event._change_reason = reason
            event.save()
            
        # Verify complete audit trail
        history_records = list(event.history.all().order_by('-history_date'))
        self.assertEqual(len(history_records), 4)  # 1 creation + 3 modifications
        
        # Check each modification is tracked
        for i, (expected_desc, expected_reason) in enumerate(modifications):
            record = history_records[i]
            self.assertEqual(record.description, expected_desc)
            self.assertEqual(record.history_change_reason, expected_reason)
            self.assertEqual(record.history_type, '~')
            
        # Verify original creation
        creation_record = history_records[-1]
        self.assertEqual(creation_record.history_type, '+')
        self.assertEqual(creation_record.description, 'Initial daily note')
        
    def test_bulk_event_changes_detection(self):
        """Test detection of bulk event changes by same user."""
        # Create multiple events and modify them
        events = []
        for i in range(12):  # Create more than suspicious threshold
            event = Event.objects.create(
                patient=self.patient,
                event_type=Event.DAILY_NOTE_EVENT,
                description=f'Daily note {i}',
                created_by=self.user
            )
            # Modify each event
            event.description = f'Modified daily note {i}'
            event._change_reason = f'Bulk modification {i}'
            event.save()
            events.append(event)
            
        # Count modifications by user in last day
        yesterday = datetime.now() - timedelta(days=1)
        modification_count = Event.history.filter(
            history_date__gte=yesterday,
            history_user=self.user,
            history_type='~'  # Only modifications
        ).count()
        
        # Should detect bulk modifications
        self.assertGreaterEqual(modification_count, 10)
        
    def test_event_history_patient_association(self):
        """Test that event history maintains patient association."""
        event = Event.objects.create(
            patient=self.patient,
            event_type=Event.HISTORY_PHYSICAL_EVENT,
            description='History and physical',
            created_by=self.user
        )
        
        # Modify event
        event.description = 'Updated history and physical'
        event.save()
        
        # Check patient association in history
        history_records = list(event.history.all())
        for record in history_records:
            self.assertEqual(record.patient, self.patient)
            
    def test_event_type_change_tracking(self):
        """Test tracking of event type changes (critical for medical records)."""
        event = Event.objects.create(
            patient=self.patient,
            event_type=Event.DAILY_NOTE_EVENT,
            description='Daily evolution note',
            created_by=self.user
        )
        
        # Change event type (this should be tracked carefully)
        original_type = event.event_type
        event.event_type = Event.PHOTO_EVENT
        event._change_reason = 'Event type changed from daily note to photo'
        event.save()
        
        # Verify type change is tracked
        history_records = list(event.history.all().order_by('-history_date'))
        
        # Latest record should have new type
        latest = history_records[0]
        self.assertEqual(latest.event_type, Event.PHOTO_EVENT)
        self.assertEqual(latest.history_change_reason, 'Event type changed from daily note to photo')
        
        # Original record should have original type
        original = history_records[1]
        self.assertEqual(original.event_type, Event.DAILY_NOTE_EVENT)


class TestEventHistoryQueries(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username='doctor1',
            email='doctor1@example.com',
            profession_type='doctor'
        )
        self.user2 = User.objects.create_user(
            username='nurse1',
            email='nurse1@example.com',
            profession_type='nurse'
        )
        self.patient = Patient.objects.create(
            name='Test Patient',
            created_by=self.user1
        )
        
    def test_event_history_by_user(self):
        """Test querying event history by specific user."""
        # Create events by different users
        event1 = Event.objects.create(
            patient=self.patient,
            event_type=Event.DAILY_NOTE_EVENT,
            description='Note by doctor',
            created_by=self.user1
        )
        
        event2 = Event.objects.create(
            patient=self.patient,
            event_type=Event.DAILY_NOTE_EVENT,
            description='Note by nurse',
            created_by=self.user2
        )
        
        # Modify events
        event1.description = 'Modified by doctor'
        event1.save()
        
        event2.description = 'Modified by nurse'
        event2.save()
        
        # Query history by user
        doctor_changes = Event.history.filter(history_user=self.user1).count()
        nurse_changes = Event.history.filter(history_user=self.user2).count()
        
        self.assertEqual(doctor_changes, 2)  # 1 creation + 1 modification
        self.assertEqual(nurse_changes, 2)   # 1 creation + 1 modification
        
    def test_event_history_by_patient(self):
        """Test querying event history for specific patient."""
        patient2 = Patient.objects.create(
            name='Another Patient',
            created_by=self.user1
        )
        
        # Create events for different patients
        event1 = Event.objects.create(
            patient=self.patient,
            event_type=Event.DAILY_NOTE_EVENT,
            description='Note for patient 1',
            created_by=self.user1
        )
        
        event2 = Event.objects.create(
            patient=patient2,
            event_type=Event.DAILY_NOTE_EVENT,
            description='Note for patient 2',
            created_by=self.user1
        )
        
        # Query history by patient
        patient1_history = Event.history.filter(patient=self.patient).count()
        patient2_history = Event.history.filter(patient=patient2).count()
        
        self.assertEqual(patient1_history, 1)
        self.assertEqual(patient2_history, 1)