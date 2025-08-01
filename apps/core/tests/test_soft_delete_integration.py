"""
Integration tests for soft delete functionality across models.
Tests cascade behavior and complex relationships.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.patients.models import Patient, AllowedTag, Tag
from apps.events.models import Event
from apps.dailynotes.models import DailyNote

User = get_user_model()


class TestSoftDeleteCascadeBehavior(TestCase):
    """Test cascade behavior and relationships with soft deletes."""

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

    def test_patient_with_events_soft_delete(self):
        """Test that patient soft delete doesn't affect related events."""
        patient = Patient.objects.create(
            name='Test Patient',
            fiscal_number='123456789',
            healthcard_number='H123456',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )

        # Create various types of events
        regular_event = Event.objects.create(
            event_datetime=timezone.now(),
            patient=patient,
            description='Regular Event',
            event_type=2,
            created_by=self.user,
            updated_by=self.user
        )

        daily_note = DailyNote.objects.create(
            event_datetime=timezone.now(),
            patient=patient,
            description='Daily Note',
            content='Note content',
            created_by=self.user,
            updated_by=self.user
        )

        # Soft delete the patient
        patient.delete(deleted_by=self.user, reason='Patient test deletion')

        # Events should still be active and queryable
        self.assertEqual(Event.objects.count(), 2)
        self.assertEqual(DailyNote.objects.count(), 1)

        # Events should still reference the (soft-deleted) patient
        active_event = Event.objects.get(id=regular_event.id)
        active_note = DailyNote.objects.get(id=daily_note.id)

        self.assertEqual(active_event.patient, patient)
        self.assertEqual(active_note.patient, patient)
        
        # Should be able to access patient data through events
        self.assertEqual(active_event.patient.name, 'Test Patient')
        self.assertTrue(active_event.patient.is_deleted)

    def test_patient_with_tags_soft_delete(self):
        """Test patient soft delete with tag relationships."""
        # Create allowed tag
        allowed_tag = AllowedTag.objects.create(
            name='Test Tag',
            color='#FF0000',
            created_by=self.user,
            updated_by=self.user
        )

        patient = Patient.objects.create(
            name='Test Patient',
            fiscal_number='123456789',
            healthcard_number='H123456',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )

        # Create tag instance
        tag = Tag.objects.create(
            patient=patient,
            allowed_tag=allowed_tag,
            created_by=self.user,
            updated_by=self.user
        )

        # Soft delete patient
        patient.delete(deleted_by=self.user, reason='Patient with tags deletion')

        # Tag instances should still exist (they don't inherit soft delete)
        self.assertEqual(Tag.objects.count(), 1)
        active_tag = Tag.objects.first()
        
        # Should still reference the soft-deleted patient
        self.assertEqual(active_tag.patient, patient)
        self.assertTrue(active_tag.patient.is_deleted)
        
        # AllowedTag should still be active
        self.assertEqual(AllowedTag.objects.count(), 1)
        self.assertFalse(allowed_tag.is_deleted)

    def test_allowed_tag_soft_delete_with_instances(self):
        """Test AllowedTag soft delete with existing tag instances."""
        allowed_tag = AllowedTag.objects.create(
            name='Test Tag',
            color='#FF0000',
            created_by=self.user,
            updated_by=self.user
        )

        patient = Patient.objects.create(
            name='Test Patient',
            fiscal_number='123456789',
            healthcard_number='H123456',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )

        # Create tag instance
        tag = Tag.objects.create(
            patient=patient,
            allowed_tag=allowed_tag,
            created_by=self.user,
            updated_by=self.user
        )

        # Soft delete the allowed tag
        allowed_tag.delete(deleted_by=self.user, reason='Tag type removal')

        # Tag instance should still exist and reference the soft-deleted allowed_tag
        self.assertEqual(Tag.objects.count(), 1)
        active_tag = Tag.objects.first()
        self.assertEqual(active_tag.allowed_tag, allowed_tag)
        
        # Should be able to access soft-deleted allowed tag data
        self.assertEqual(active_tag.allowed_tag.name, 'Test Tag')
        self.assertTrue(active_tag.allowed_tag.is_deleted)

    def test_user_with_created_records_deletion(self):
        """Test behavior when user who created records is deleted/deactivated."""
        # Create records
        patient = Patient.objects.create(
            name='Test Patient',
            fiscal_number='123456789',
            healthcard_number='H123456',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )

        event = Event.objects.create(
            event_datetime=timezone.now(),
            patient=patient,
            description='Event by user',
            event_type=1,
            created_by=self.user,
            updated_by=self.user
        )

        # Soft delete patient and event
        patient.delete(deleted_by=self.user, reason='Test patient deletion')
        event.delete(deleted_by=self.user, reason='Test event deletion')

        # Deactivate the user (simulate user deletion/deactivation)
        self.user.is_active = False
        self.user.save()

        # Soft deleted records should still exist and reference the user
        deleted_patient = Patient.all_objects.get(id=patient.id)
        deleted_event = Event.all_objects.get(id=event.id)

        self.assertEqual(deleted_patient.created_by, self.user)
        self.assertEqual(deleted_patient.deleted_by, self.user)
        self.assertEqual(deleted_event.created_by, self.user)
        self.assertEqual(deleted_event.deleted_by, self.user)

        # Should be able to restore records even with inactive user
        deleted_patient.restore(restored_by=self.admin)
        deleted_event.restore(restored_by=self.admin)

        self.assertEqual(Patient.objects.count(), 1)
        self.assertEqual(Event.objects.count(), 1)

    def test_complex_patient_timeline_with_mixed_deletions(self):
        """Test complex patient timeline with mix of active and deleted events."""
        patient = Patient.objects.create(
            name='Timeline Patient',
            fiscal_number='123456789',
            healthcard_number='H123456',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )

        # Create timeline of events
        events = []
        for i in range(10):
            if i % 3 == 0:  # Every third event is a daily note
                event = DailyNote.objects.create(
            event_datetime=timezone.now(),
                    patient=patient,
                    description=f'Daily Note {i}',
                    content=f'Content for day {i}',
                    created_by=self.user,
            updated_by=self.user
                )
            else:
                event = Event.objects.create(
            event_datetime=timezone.now(),
                    patient=patient,
                    description=f'Event {i}',
                    event_type=i % 5 + 1,
                    created_by=self.user,
            updated_by=self.user
                )
            events.append(event)

        # Soft delete some events (mix of regular events and daily notes)
        events[1].delete(deleted_by=self.user, reason='Event 1 deletion')
        events[3].delete(deleted_by=self.user, reason='Daily Note 3 deletion')  
        events[7].delete(deleted_by=self.user, reason='Event 7 deletion')

        # Test active timeline
        active_events = Event.objects.filter(patient=patient).order_by('created_at')
        self.assertEqual(active_events.count(), 7)  # 10 - 3 deleted

        active_daily_notes = DailyNote.objects.filter(patient=patient).order_by('created_at')
        self.assertEqual(active_daily_notes.count(), 3)  # 4 created - 1 deleted

        # Test complete timeline (including deleted)
        all_events = Event.all_objects.filter(patient=patient).order_by('created_at')
        self.assertEqual(all_events.count(), 10)

        all_daily_notes = DailyNote.all_objects.filter(patient=patient).order_by('created_at')
        self.assertEqual(all_daily_notes.count(), 4)

        # Test deleted timeline
        deleted_events = Event.all_objects.filter(patient=patient).deleted().order_by('created_at')
        self.assertEqual(deleted_events.count(), 3)

        # Verify correct events are deleted
        deleted_ids = {e.id for e in deleted_events}
        expected_deleted_ids = {events[1].id, events[3].id, events[7].id}
        self.assertEqual(deleted_ids, expected_deleted_ids)

    def test_bulk_operations_across_models(self):
        """Test bulk soft delete operations across different models."""
        # Step 1: Create test data
        patients = []
        events = []
        allowed_tags = []

        # Create patients and related data
        for i in range(5):
            patient = Patient.objects.create(
                name=f'Bulk Patient {i}',
                fiscal_number=f'12345{i:04d}',
                healthcard_number=f'H{i:05d}',
                birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
                created_by=self.user,
            updated_by=self.user
            )
            patients.append(patient)

            # Create events for each patient
            for j in range(3):
                event = Event.objects.create(
            event_datetime=timezone.now(),
                    patient=patient,
                    description=f'Event {j} for Patient {i}',
                    event_type=(j % 5) + 1,
                    created_by=self.user,
            updated_by=self.user
                )
                events.append(event)

            # Create allowed tags
            if i < 3:  # Only create 3 allowed tags
                allowed_tag = AllowedTag.objects.create(
                    name=f'Bulk Tag {i}',
                    color=f'#FF{i:02d}{i:02d}',
                    created_by=self.user,
            updated_by=self.user
                )
                allowed_tags.append(allowed_tag)

        # Step 2: Verify initial state
        self.assertEqual(Patient.objects.count(), 5)
        self.assertEqual(Event.objects.count(), 15)  # 5 patients * 3 events
        self.assertEqual(AllowedTag.objects.count(), 3)

        # Step 3: Bulk soft delete some patients
        Patient.objects.filter(name__contains='Bulk Patient').exclude(
            name__contains='Patient 0'
        ).delete()  # Delete patients 1-4, keep patient 0

        # Step 4: Verify patient deletions
        self.assertEqual(Patient.objects.count(), 1)  # Only patient 0 active
        self.assertEqual(Patient.all_objects.count(), 5)  # All still exist
        self.assertEqual(Patient.all_objects.deleted().count(), 4)  # 4 deleted

        # Step 5: Verify events still exist (related to soft-deleted patients)
        self.assertEqual(Event.objects.count(), 15)  # Events not affected by patient soft delete
        
        # Step 6: Bulk soft delete some events
        Event.objects.filter(description__contains='Event 0').delete()  # Delete "Event 0" for all patients

        self.assertEqual(Event.objects.count(), 10)  # 15 - 5 deleted
        self.assertEqual(Event.all_objects.count(), 15)  # All still exist
        self.assertEqual(Event.all_objects.deleted().count(), 5)  # 5 deleted

        # Step 7: Bulk soft delete allowed tags
        AllowedTag.objects.all().delete()

        self.assertEqual(AllowedTag.objects.count(), 0)  # All soft deleted
        self.assertEqual(AllowedTag.all_objects.count(), 3)  # All still exist
        self.assertEqual(AllowedTag.all_objects.deleted().count(), 3)  # All deleted

    def test_restoration_cascade_scenarios(self):
        """Test restoration in various cascade scenarios."""
        # Create patient with events
        patient = Patient.objects.create(
            name='Restoration Patient',
            fiscal_number='123456789',
            healthcard_number='H123456',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )

        event = Event.objects.create(
            event_datetime=timezone.now(),
            patient=patient,
            description='Event for restoration test',
            event_type=1,
            created_by=self.user,
            updated_by=self.user
        )

        # Soft delete both
        patient.delete(deleted_by=self.user, reason='Patient deletion for restoration test')
        event.delete(deleted_by=self.user, reason='Event deletion for restoration test')

        # Verify both are deleted
        self.assertEqual(Patient.objects.count(), 0)
        self.assertEqual(Event.objects.count(), 0)

        # Restore patient only
        patient.restore(restored_by=self.admin)

        # Patient should be active, event still deleted
        self.assertEqual(Patient.objects.count(), 1)
        self.assertEqual(Event.objects.count(), 0)

        # Event should still reference the restored patient
        deleted_event = Event.all_objects.get(id=event.id)
        self.assertEqual(deleted_event.patient, patient)
        self.assertFalse(deleted_event.patient.is_deleted)

        # Restore event
        event.restore(restored_by=self.admin)

        # Both should now be active
        self.assertEqual(Patient.objects.count(), 1)
        self.assertEqual(Event.objects.count(), 1)

    def test_soft_delete_with_history_integration(self):
        """Test that soft deletes work correctly with history tracking."""
        patient = Patient.objects.create(
            name='History Patient',
            fiscal_number='123456789',
            healthcard_number='H123456',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )

        # Update patient to create history
        patient.name = 'Updated History Patient'
        patient._change_reason = 'Name update test'
        patient.save()

        # Soft delete patient
        patient.delete(deleted_by=self.user, reason='History integration test')

        # Patient should be soft deleted
        deleted_patient = Patient.all_objects.get(id=patient.id)
        self.assertTrue(deleted_patient.is_deleted)

        # History should still exist and be accessible
        if hasattr(patient, 'history'):
            history_records = patient.history.all()
            self.assertGreater(history_records.count(), 0)
            
            # Should have creation, update, and deletion records
            latest_history = history_records.first()
            self.assertEqual(latest_history.name, 'Updated History Patient')

        # Restore patient
        patient.restore(restored_by=self.admin)

        # History should still be intact
        restored_patient = Patient.objects.get(id=patient.id)
        self.assertFalse(restored_patient.is_deleted)
        
        if hasattr(restored_patient, 'history'):
            history_after_restore = restored_patient.history.all()
            # Should have at least the same number of records (potentially more with restore)
            self.assertGreaterEqual(history_after_restore.count(), history_records.count())


class TestSoftDeletePerformance(TestCase):
    """Test performance characteristics of soft delete implementation."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='perfuser',
            email='perf@example.com',
            profession_type=0  # MEDICAL_DOCTOR
        )

    def test_query_performance_with_large_dataset(self):
        """Test that soft delete queries perform well with large datasets."""
        # Create large dataset
        patients = []
        for i in range(100):
            patient = Patient.objects.create(
                name=f'Performance Patient {i}',
                fiscal_number=f'PERF{i:06d}',
                healthcard_number=f'HP{i:06d}',
                birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
                created_by=self.user,
            updated_by=self.user
            )
            patients.append(patient)

        # Soft delete half the patients
        for i in range(0, 100, 2):
            patients[i].delete(deleted_by=self.user, reason=f'Performance test deletion {i}')

        # Test query performance (these should be fast with proper indexes)
        with self.assertNumQueries(1):
            active_count = Patient.objects.count()
            self.assertEqual(active_count, 50)

        with self.assertNumQueries(1):
            deleted_count = Patient.all_objects.deleted().count()
            self.assertEqual(deleted_count, 50)

        with self.assertNumQueries(1):
            total_count = Patient.all_objects.count()
            self.assertEqual(total_count, 100)

        # Test filtering performance
        with self.assertNumQueries(1):
            filtered_active = Patient.objects.filter(name__contains='Patient 1').count()
            # Patients 1, 10, 12, 14, 16, 18 should be active (index 1 is odd, so not deleted)
            self.assertEqual(filtered_active, 6)

        with self.assertNumQueries(1):
            filtered_deleted = Patient.all_objects.deleted().filter(name__contains='Patient 1').count()
            # Patients 11, 13, 15, 17, 19 should be deleted (odd indices)
            self.assertEqual(filtered_deleted, 5)

    def test_bulk_operations_performance(self):
        """Test performance of bulk soft delete operations."""
        # Create test data
        patients = []
        for i in range(50):
            patient = Patient.objects.create(
                name=f'Bulk Perf Patient {i}',
                fiscal_number=f'BULK{i:05d}',
                healthcard_number=f'HB{i:05d}',
                birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
                created_by=self.user,
            updated_by=self.user
            )
            patients.append(patient)

        # Bulk soft delete should be efficient
        with self.assertNumQueries(1):
            Patient.objects.filter(name__contains='Bulk Perf').delete()

        # Verify results
        self.assertEqual(Patient.objects.count(), 0)
        self.assertEqual(Patient.all_objects.count(), 50)
        self.assertEqual(Patient.all_objects.deleted().count(), 50)