from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.events.models import Event
from apps.patients.models import Patient
from datetime import timedelta

User = get_user_model()


def _create_event(patient, user, event_type, description):
    """Helper to create an Event with _history_user set for audit tracking."""
    event = Event(
        patient=patient,
        event_type=event_type,
        event_datetime=timezone.now(),
        description=description,
        created_by=user,
        updated_by=user,
    )
    event._history_user = user
    event.save()
    return event


class TestEventHistory(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='doctor',
            email='doctor@example.com',
            profession_type=User.MEDICAL_DOCTOR
        )
        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            created_by=self.user,
            updated_by=self.user
        )

    def test_event_creation_history(self):
        """Test that event creation is tracked."""
        event = _create_event(
            self.patient, self.user,
            Event.HISTORY_AND_PHYSICAL_EVENT,
            'Initial history and physical examination',
        )

        # Check history record created
        history = event.history.first()
        self.assertEqual(history.history_type, '+')
        self.assertEqual(history.history_user, self.user)
        self.assertEqual(history.description, 'Initial history and physical examination')
        self.assertEqual(history.event_type, Event.HISTORY_AND_PHYSICAL_EVENT)

    def test_event_modification_history(self):
        """Test that event modifications are tracked."""
        event = _create_event(
            self.patient, self.user,
            Event.HISTORY_AND_PHYSICAL_EVENT,
            'Original description',
        )

        # Modify event
        event.description = 'Updated description with additional findings'
        event.event_type = Event.DAILY_NOTE_EVENT
        event._change_reason = 'Updated description and changed event type'
        event._history_user = self.user
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
        """Test tracking of event soft-delete (is_deleted flag set)."""
        event = _create_event(
            self.patient, self.user,
            Event.DAILY_NOTE_EVENT,
            'Daily note to be deleted',
        )

        event_id = event.id

        # Soft-delete event (Event uses SoftDeleteModel)
        event._change_reason = 'Event deleted by user request'
        event.delete()

        # Soft delete saves the object with is_deleted=True, creating a
        # modification history entry (type '~'), not a hard-delete (type '-').
        deletion_history = event.history.filter(
            id=event_id,
            history_type='~',
        ).first()

        self.assertIsNotNone(deletion_history)
        self.assertTrue(event.is_deleted)
        self.assertEqual(deletion_history.history_change_reason, 'Event deleted by user request')

    def test_critical_event_modifications(self):
        """Test tracking of critical medical event modifications."""
        # Create a critical medical event
        event = _create_event(
            self.patient, self.user,
            Event.PHOTO_EVENT,
            'Critical medical imaging',
        )

        # Simulate unauthorized modification
        event.description = 'Modified medical imaging description'
        event._change_reason = 'Unauthorized modification detected'
        event._history_user = self.user
        event.save()

        # Check modification is tracked
        modification = event.history.filter(history_type='~').first()
        self.assertIsNotNone(modification)
        self.assertEqual(modification.description, 'Modified medical imaging description')
        self.assertEqual(modification.history_change_reason, 'Unauthorized modification detected')

    def test_event_audit_trail_integrity(self):
        """Test that complete audit trail is maintained for events."""
        event = _create_event(
            self.patient, self.user,
            Event.DAILY_NOTE_EVENT,
            'Initial daily note',
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
            event._history_user = self.user
            event.save()

        # Verify complete audit trail
        history_records = list(event.history.all())
        self.assertEqual(len(history_records), 4)  # 1 creation + 3 modifications

        # history.all() default ordering is newest-first (by history_date DESC)
        # Record 0: latest modification, Record 3: original creation
        latest_mod = history_records[0]
        self.assertEqual(latest_mod.history_type, '~')
        self.assertEqual(latest_mod.description, 'Final notes added')
        self.assertEqual(latest_mod.history_change_reason, 'End of day update')

        # Verify original creation is the last record
        creation_record = history_records[-1]
        self.assertEqual(creation_record.history_type, '+')
        self.assertEqual(creation_record.description, 'Initial daily note')

        # Verify all modifications have correct type
        for record in history_records[0:3]:
            self.assertEqual(record.history_type, '~')

    def test_bulk_event_changes_detection(self):
        """Test detection of bulk event changes by same user."""
        # Create multiple events and modify them
        events = []
        for i in range(12):  # Create more than suspicious threshold
            event = _create_event(
                self.patient, self.user,
                Event.DAILY_NOTE_EVENT,
                f'Daily note {i}',
            )
            # Modify each event
            event.description = f'Modified daily note {i}'
            event._change_reason = f'Bulk modification {i}'
            event._history_user = self.user
            event.save()
            events.append(event)

        # Count modifications by user in last day
        yesterday = timezone.now() - timedelta(days=1)
        modification_count = Event.history.filter(
            history_date__gte=yesterday,
            history_user=self.user,
            history_type='~'  # Only modifications
        ).count()

        # Should detect bulk modifications (12 modify-saves)
        self.assertGreaterEqual(modification_count, 10)

    def test_event_history_patient_association(self):
        """Test that event history maintains patient association."""
        event = _create_event(
            self.patient, self.user,
            Event.HISTORY_AND_PHYSICAL_EVENT,
            'History and physical',
        )

        # Modify event
        event.description = 'Updated history and physical'
        event._history_user = self.user
        event.save()

        # Check patient association in history
        history_records = list(event.history.all())
        for record in history_records:
            self.assertEqual(record.patient, self.patient)

    def test_event_type_change_tracking(self):
        """Test tracking of event type changes (critical for medical records)."""
        event = _create_event(
            self.patient, self.user,
            Event.DAILY_NOTE_EVENT,
            'Daily evolution note',
        )

        # Change event type (this should be tracked carefully)
        event.event_type = Event.PHOTO_EVENT
        event._change_reason = 'Event type changed from daily note to photo'
        event._history_user = self.user
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
            profession_type=User.MEDICAL_DOCTOR
        )
        self.user2 = User.objects.create_user(
            username='nurse1',
            email='nurse1@example.com',
            profession_type=User.NURSE
        )
        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            created_by=self.user1,
            updated_by=self.user1
        )

    def test_event_history_by_user(self):
        """Test querying event history by specific user."""
        # Create events by different users
        event1 = _create_event(
            self.patient, self.user1,
            Event.DAILY_NOTE_EVENT,
            'Note by doctor',
        )

        event2 = _create_event(
            self.patient, self.user2,
            Event.DAILY_NOTE_EVENT,
            'Note by nurse',
        )

        # Modify events
        event1.description = 'Modified by doctor'
        event1._history_user = self.user1
        event1.save()

        event2.description = 'Modified by nurse'
        event2._history_user = self.user2
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
            birthday='1985-06-15',
            created_by=self.user1,
            updated_by=self.user1
        )

        # Create events for different patients
        _create_event(
            self.patient, self.user1,
            Event.DAILY_NOTE_EVENT,
            'Note for patient 1',
        )

        _create_event(
            patient2, self.user1,
            Event.DAILY_NOTE_EVENT,
            'Note for patient 2',
        )

        # Query history by patient
        patient1_history = Event.history.filter(patient=self.patient).count()
        patient2_history = Event.history.filter(patient=patient2).count()

        self.assertEqual(patient1_history, 1)
        self.assertEqual(patient2_history, 1)
