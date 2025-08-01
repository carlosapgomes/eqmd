"""
Tests for soft delete functionality in Event models.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from apps.patients.models import Patient
from apps.events.models import Event
from apps.dailynotes.models import DailyNote

User = get_user_model()


class TestEventSoftDelete(TestCase):
    """Test soft delete functionality for Event model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            profession_type=0  # MEDICAL_DOCTOR
        )
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com'
        )
        self.patient = Patient.objects.create(
            name='Test Patient',
            fiscal_number='123456789',
            healthcard_number='H123456',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )

    def test_event_soft_delete(self):
        """Test that event soft delete works correctly."""
        event = Event.objects.create(
            event_datetime=timezone.now(),
            patient=self.patient,
            description='Test event',
            event_type=1,
            created_by=self.user,
            updated_by=self.user
        )
        event_id = event.id

        # Soft delete the event
        event.delete(deleted_by=self.user, reason='Test deletion')

        # Event should not appear in normal queries
        self.assertEqual(Event.objects.count(), 0)
        self.assertFalse(Event.objects.filter(id=event_id).exists())

        # Event should appear in all_objects queries
        self.assertEqual(Event.all_objects.count(), 1)
        deleted_event = Event.all_objects.get(id=event_id)
        self.assertTrue(deleted_event.is_deleted)
        self.assertEqual(deleted_event.deleted_by, self.user)
        self.assertEqual(deleted_event.deletion_reason, 'Test deletion')
        self.assertIsNotNone(deleted_event.deleted_at)

    def test_event_restore(self):
        """Test that event restoration works correctly."""
        event = Event.objects.create(
            event_datetime=timezone.now(),
            patient=self.patient,
            description='Test event',
            event_type=1,
            created_by=self.user,
            updated_by=self.user
        )
        event_id = event.id

        # Soft delete then restore
        event.delete(deleted_by=self.user, reason='Test deletion')
        event.restore(restored_by=self.admin)

        # Event should appear in normal queries again
        self.assertEqual(Event.objects.count(), 1)
        restored_event = Event.objects.get(id=event_id)
        self.assertFalse(restored_event.is_deleted)
        self.assertIsNone(restored_event.deleted_at)
        self.assertIsNone(restored_event.deleted_by)
        self.assertEqual(restored_event.deletion_reason, '')

    def test_event_hard_delete(self):
        """Test that hard delete permanently removes event."""
        event = Event.objects.create(
            event_datetime=timezone.now(),
            patient=self.patient,
            description='Test event',
            event_type=1,
            created_by=self.user,
            updated_by=self.user
        )
        event_id = event.id

        # Hard delete the event
        event.hard_delete()

        # Event should not exist anywhere
        self.assertEqual(Event.objects.count(), 0)
        self.assertEqual(Event.all_objects.count(), 0)
        self.assertFalse(Event.all_objects.filter(id=event_id).exists())

    def test_event_timeline_with_soft_deletes(self):
        """Test that patient timeline handles soft deleted events correctly."""
        # Create multiple events
        events = []
        for i in range(5):
            event = Event.objects.create(
            event_datetime=timezone.now(),
                patient=self.patient,
                description=f'Event {i}',
                event_type=1,
                created_by=self.user,
            updated_by=self.user
            )
            events.append(event)

        # Soft delete some events
        events[1].delete(deleted_by=self.user, reason='Test deletion 1')
        events[3].delete(deleted_by=self.user, reason='Test deletion 3')

        # Active events should only show non-deleted
        active_events = Event.objects.filter(patient=self.patient)
        self.assertEqual(active_events.count(), 3)
        
        # All events including deleted
        all_events = Event.all_objects.filter(patient=self.patient)
        self.assertEqual(all_events.count(), 5)

        # Deleted events only
        deleted_events = Event.all_objects.filter(
            patient=self.patient
        ).deleted()
        self.assertEqual(deleted_events.count(), 2)

    def test_event_with_soft_deleted_patient(self):
        """Test event behavior when patient is soft deleted."""
        event = Event.objects.create(
            event_datetime=timezone.now(),
            patient=self.patient,
            description='Test event',
            event_type=1,
            created_by=self.user,
            updated_by=self.user
        )

        # Soft delete the patient
        self.patient.delete(deleted_by=self.user, reason='Patient deletion')

        # Event should still exist and be queryable
        self.assertEqual(Event.objects.count(), 1)
        retrieved_event = Event.objects.first()
        self.assertEqual(retrieved_event.id, event.id)

        # Should be able to access the soft-deleted patient through the event
        self.assertEqual(retrieved_event.patient.name, 'Test Patient')
        self.assertTrue(retrieved_event.patient.is_deleted)

    def test_queryset_bulk_operations(self):
        """Test bulk operations on event querysets."""
        # Create multiple events
        events = []
        for i in range(10):
            event = Event.objects.create(
            event_datetime=timezone.now(),
                patient=self.patient,
                description=f'Bulk Event {i}',
                event_type=1,
                created_by=self.user,
            updated_by=self.user
            )
            events.append(event)

        # Bulk soft delete using queryset
        Event.objects.filter(description__contains='Bulk Event').delete()

        # All events should be soft deleted
        self.assertEqual(Event.objects.count(), 0)
        self.assertEqual(Event.all_objects.count(), 10)
        
        # All should be marked as deleted
        for event in Event.all_objects.all():
            self.assertTrue(event.is_deleted)
            self.assertIsNotNone(event.deleted_at)

    def test_event_filters_with_mixed_states(self):
        """Test various filter combinations with active and deleted events."""
        # Create events with different states
        active_event = Event.objects.create(
            event_datetime=timezone.now(),
            patient=self.patient,
            description='Active Event',
            event_type=1,
            created_by=self.user,
            updated_by=self.user
        )
        
        deleted_event = Event.objects.create(
            event_datetime=timezone.now(),
            patient=self.patient,
            description='Deleted Event',
            event_type=2,
            created_by=self.user,
            updated_by=self.user
        )
        deleted_event.delete(deleted_by=self.user, reason='Test')

        # Test filtering by event_type on active events
        type1_events = Event.objects.filter(event_type=1)
        self.assertEqual(type1_events.count(), 1)
        self.assertEqual(type1_events.first(), active_event)

        # Test filtering by event_type on all events
        all_type2_events = Event.all_objects.filter(event_type=2)
        self.assertEqual(all_type2_events.count(), 1)
        self.assertEqual(all_type2_events.first(), deleted_event)

        # Test complex queries
        patient_active_events = Event.objects.filter(
            patient=self.patient,
            event_type__in=[1, 2]
        )
        self.assertEqual(patient_active_events.count(), 1)


class TestDailyNoteSoftDelete(TestCase):
    """Test soft delete functionality for DailyNote model (inherits from Event)."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            profession_type=0  # MEDICAL_DOCTOR
        )
        self.patient = Patient.objects.create(
            name='Test Patient',
            fiscal_number='123456789',
            healthcard_number='H123456',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )

    def test_daily_note_soft_delete(self):
        """Test that DailyNote soft delete works correctly."""
        daily_note = DailyNote.objects.create(
            event_datetime=timezone.now(),
            patient=self.patient,
            description='Test daily note',
            content='Daily note content',
            created_by=self.user,
            updated_by=self.user
        )
        note_id = daily_note.id

        # Soft delete the daily note
        daily_note.delete(deleted_by=self.user, reason='Test deletion')

        # Should not appear in normal queries
        self.assertEqual(DailyNote.objects.count(), 0)
        self.assertEqual(Event.objects.count(), 0)  # Should also not appear in Event queries

        # Should appear in all_objects queries
        self.assertEqual(DailyNote.all_objects.count(), 1)
        self.assertEqual(Event.all_objects.count(), 1)
        
        deleted_note = DailyNote.all_objects.get(id=note_id)
        self.assertTrue(deleted_note.is_deleted)
        self.assertEqual(deleted_note.deletion_reason, 'Test deletion')

    def test_daily_note_restore(self):
        """Test that DailyNote restoration works correctly."""
        daily_note = DailyNote.objects.create(
            event_datetime=timezone.now(),
            patient=self.patient,
            description='Test daily note',
            content='Daily note content',
            created_by=self.user,
            updated_by=self.user
        )

        # Soft delete then restore
        daily_note.delete(deleted_by=self.user, reason='Test deletion')
        daily_note.restore(restored_by=self.user)

        # Should appear in normal queries again
        self.assertEqual(DailyNote.objects.count(), 1)
        self.assertEqual(Event.objects.count(), 1)
        
        restored_note = DailyNote.objects.first()
        self.assertFalse(restored_note.is_deleted)
        self.assertEqual(restored_note.content, 'Daily note content')

    def test_mixed_event_types_soft_delete(self):
        """Test soft deletes with mixed event types in same patient timeline."""
        # Create different types of events
        regular_event = Event.objects.create(
            event_datetime=timezone.now(),
            patient=self.patient,
            description='Regular Event',
            event_type=2,
            created_by=self.user,
            updated_by=self.user
        )
        
        daily_note = DailyNote.objects.create(
            event_datetime=timezone.now(),
            patient=self.patient,
            description='Daily Note Event',
            content='Note content',
            created_by=self.user,
            updated_by=self.user
        )

        # Soft delete the daily note only
        daily_note.delete(deleted_by=self.user, reason='Note deletion')

        # Check counts
        self.assertEqual(Event.objects.count(), 1)  # Only regular event
        self.assertEqual(DailyNote.objects.count(), 0)  # Daily note deleted
        self.assertEqual(Event.all_objects.count(), 2)  # Both events exist
        self.assertEqual(DailyNote.all_objects.count(), 1)  # Daily note in all_objects

        # Regular event should still be active
        active_event = Event.objects.first()
        self.assertEqual(active_event, regular_event)
        self.assertFalse(active_event.is_deleted)


class TestEventSoftDeleteEdgeCases(TestCase):
    """Test edge cases for Event soft delete functionality."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            profession_type=0  # MEDICAL_DOCTOR
        )
        self.patient = Patient.objects.create(
            name='Test Patient',
            fiscal_number='123456789',
            healthcard_number='H123456',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )

    def test_event_24_hour_edit_window_with_soft_delete(self):
        """Test that soft deleted events respect the 24-hour edit window."""
        # Create event more than 24 hours ago
        old_event = Event.objects.create(
            event_datetime=timezone.now(),
            patient=self.patient,
            description='Old Event',
            event_type=1,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Manually set created_at to more than 24 hours ago
        old_time = timezone.now() - timedelta(hours=25)
        Event.all_objects.filter(id=old_event.id).update(created_at=old_time)

        # Soft delete the old event
        old_event.delete(deleted_by=self.user, reason='Test old deletion')

        # Event should be soft deleted
        deleted_event = Event.all_objects.get(id=old_event.id)
        self.assertTrue(deleted_event.is_deleted)

        # Create recent event
        recent_event = Event.objects.create(
            event_datetime=timezone.now(),
            patient=self.patient,
            description='Recent Event',
            event_type=1,
            created_by=self.user,
            updated_by=self.user
        )

        # Soft delete the recent event
        recent_event.delete(deleted_by=self.user, reason='Test recent deletion')

        # Both should be soft deleted
        self.assertEqual(Event.objects.count(), 0)
        self.assertEqual(Event.all_objects.deleted().count(), 2)

    def test_event_foreign_key_behavior_after_soft_delete(self):
        """Test foreign key relationships after soft deletion."""
        event = Event.objects.create(
            event_datetime=timezone.now(),
            patient=self.patient,
            description='Test Event',
            event_type=1,
            created_by=self.user,
            updated_by=self.user
        )

        # Store references
        patient_id = event.patient.id
        user_id = event.created_by.id

        # Soft delete event
        event.delete(deleted_by=self.user, reason='FK test')

        # Retrieve soft deleted event
        deleted_event = Event.all_objects.get(id=event.id)

        # Foreign key relationships should still work
        self.assertEqual(deleted_event.patient.id, patient_id)
        self.assertEqual(deleted_event.created_by.id, user_id)
        self.assertEqual(deleted_event.deleted_by.id, user_id)

        # Should be able to navigate relationships
        self.assertEqual(deleted_event.patient.name, 'Test Patient')
        self.assertEqual(deleted_event.created_by.username, 'testuser')

    def test_event_ordering_with_soft_deletes(self):
        """Test that event ordering works correctly with soft deletes."""
        # Create events with different timestamps
        events = []
        for i in range(5):
            event = Event.objects.create(
            event_datetime=timezone.now(),
                patient=self.patient,
                description=f'Event {i}',
                event_type=1,
                created_by=self.user,
            updated_by=self.user
            )
            events.append(event)

        # Soft delete middle event
        events[2].delete(deleted_by=self.user, reason='Middle deletion')

        # Test ordering of active events
        active_events = list(Event.objects.filter(patient=self.patient).order_by('created_at'))
        self.assertEqual(len(active_events), 4)
        
        # Should maintain proper order excluding deleted event  
        expected_descriptions = ['Event 0', 'Event 1', 'Event 3', 'Event 4']
        actual_descriptions = [e.description for e in active_events]
        self.assertEqual(actual_descriptions, expected_descriptions)

        # Test ordering of all events including deleted
        all_events = list(Event.all_objects.filter(patient=self.patient).order_by('created_at'))
        self.assertEqual(len(all_events), 5)
        
        all_descriptions = [e.description for e in all_events]
        expected_all = ['Event 0', 'Event 1', 'Event 2', 'Event 3', 'Event 4']
        self.assertEqual(all_descriptions, expected_all)