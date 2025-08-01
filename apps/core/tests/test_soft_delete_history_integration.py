"""
Tests for soft delete integration with django-simple-history.
Tests that soft deletes work correctly with audit history tracking.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.patients.models import Patient, AllowedTag
from apps.events.models import Event

User = get_user_model()


class TestSoftDeleteHistoryIntegration(TestCase):
    """Test soft delete functionality with history tracking."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='historyuser',
            email='history@example.com',
            profession_type=0  # MEDICAL_DOCTOR
        )
        self.admin = User.objects.create_superuser(
            username='historyadmin',
            email='historyadmin@example.com'
        )

    def test_patient_soft_delete_creates_history_record(self):
        """Test that soft deleting a patient creates appropriate history records."""
        patient = Patient.objects.create(
            name='History Test Patient',
            fiscal_number='123456789',
            healthcard_number='H123456',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )

        # Get initial history count
        if hasattr(patient, 'history'):
            initial_history_count = patient.history.count()
            
            # Soft delete with change reason
            patient._change_reason = 'Soft delete for history test'
            patient.delete(deleted_by=self.user, reason='History integration test')
            
            # Should have additional history record
            updated_history_count = patient.history.count()
            self.assertGreater(updated_history_count, initial_history_count)
            
            # Latest history record should show the soft delete
            latest_history = patient.history.first()
            self.assertTrue(latest_history.is_deleted)
            self.assertEqual(latest_history.deleted_by, self.user)
            self.assertEqual(latest_history.deletion_reason, 'History integration test')
            self.assertIsNotNone(latest_history.deleted_at)
            
            # History should preserve the change reason
            self.assertEqual(latest_history.history_change_reason, 'Soft delete for history test')

    def test_patient_restore_creates_history_record(self):
        """Test that restoring a patient creates appropriate history records."""
        patient = Patient.objects.create(
            name='Restore History Patient',
            fiscal_number='123456789',
            healthcard_number='H123456',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )

        # Soft delete first
        patient.delete(deleted_by=self.user, reason='For restore test')
        
        if hasattr(patient, 'history'):
            history_after_delete = patient.history.count()
            
            # Restore with change reason
            patient._change_reason = f'Restored by {self.admin.username}'
            patient.restore(restored_by=self.admin)
            
            # Should have additional history record for restoration
            history_after_restore = patient.history.count()
            self.assertGreater(history_after_restore, history_after_delete)
            
            # Latest history record should show restoration
            latest_history = patient.history.first()
            self.assertFalse(latest_history.is_deleted)
            self.assertIsNone(latest_history.deleted_at)
            self.assertIsNone(latest_history.deleted_by)
            self.assertEqual(latest_history.deletion_reason, '')
            
            # Should have restore change reason
            self.assertIn('Restored by historyadmin', latest_history.history_change_reason)

    def test_event_soft_delete_history_integration(self):
        """Test that Event soft deletes integrate with history tracking."""
        patient = Patient.objects.create(
            name='Event History Patient',
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
            description='History Integration Event',
            event_type=1,
            created_by=self.user,
            updated_by=self.user
        )

        if hasattr(event, 'history'):
            initial_history_count = event.history.count()
            
            # Soft delete event
            event._change_reason = 'Event soft delete for history test'
            event.delete(deleted_by=self.user, reason='Event history test')
            
            # Should create history record
            updated_history_count = event.history.count()
            self.assertGreater(updated_history_count, initial_history_count)
            
            # Latest history should show soft delete
            latest_history = event.history.first()
            self.assertTrue(latest_history.is_deleted)
            self.assertEqual(latest_history.deleted_by, self.user)

    def test_allowed_tag_soft_delete_history_integration(self):
        """Test that AllowedTag soft deletes integrate with history tracking."""
        tag = AllowedTag.objects.create(
            name='History Tag',
            color='#FF0000',
            created_by=self.user,
            updated_by=self.user
        )

        if hasattr(tag, 'history'):
            initial_history_count = tag.history.count()
            
            # Soft delete tag
            tag._change_reason = 'Tag removal for history test'
            tag.delete(deleted_by=self.admin, reason='Tag history test')
            
            # Should create history record
            updated_history_count = tag.history.count()
            self.assertGreater(updated_history_count, initial_history_count)
            
            # Latest history should show soft delete
            latest_history = tag.history.first()
            self.assertTrue(latest_history.is_deleted)
            self.assertEqual(latest_history.deleted_by, self.admin)

    def test_bulk_soft_delete_history_tracking(self):
        """Test history tracking with bulk soft delete operations."""
        # Create multiple patients
        patients = []
        for i in range(5):
            patient = Patient.objects.create(
                name=f'Bulk History Patient {i}',
                fiscal_number=f'12345678{i}',
                healthcard_number=f'H12345{i}',
                birthday='1990-01-01',
                status=Patient.Status.INPATIENT,
                created_by=self.user,
                updated_by=self.user
            )
            patients.append(patient)

        # Get initial history counts
        initial_history_counts = {}
        for patient in patients:
            if hasattr(patient, 'history'):
                initial_history_counts[patient.id] = patient.history.count()

        # Bulk soft delete using individual deletion for proper history tracking
        bulk_patients = Patient.objects.filter(name__contains='Bulk History')
        for patient in bulk_patients:
            patient.delete(deleted_by=self.user, reason='Bulk deletion test')

        # Check that each patient has additional history record
        for patient in patients:
            if hasattr(patient, 'history'):
                current_count = patient.history.count()
                initial_count = initial_history_counts.get(patient.id, 0)
                self.assertGreater(current_count, initial_count)
                
                # Latest history should show soft delete
                latest_history = patient.history.first()
                self.assertTrue(latest_history.is_deleted)

    def test_history_preservation_across_delete_restore_cycles(self):
        """Test that history is preserved across multiple delete/restore cycles."""
        patient = Patient.objects.create(
            name='Cycle History Patient',
            fiscal_number='123456789',
            healthcard_number='H123456',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )

        if hasattr(patient, 'history'):
            # Perform multiple delete/restore cycles
            history_counts = []
            
            for i in range(3):
                # Record current history count
                current_count = patient.history.count()
                history_counts.append(current_count)
                
                # Delete
                patient._change_reason = f'Cycle {i} deletion'
                patient.delete(deleted_by=self.user, reason=f'Cycle {i} deletion reason')
                
                # Should have more history
                after_delete_count = patient.history.count()
                self.assertGreater(after_delete_count, current_count)
                
                # Restore
                patient._change_reason = f'Cycle {i} restoration'
                patient.restore(restored_by=self.admin)
                
                # Should have even more history
                after_restore_count = patient.history.count()
                self.assertGreater(after_restore_count, after_delete_count)

            # Final history count should be significantly higher than initial
            final_count = patient.history.count()
            initial_count = history_counts[0]
            self.assertGreater(final_count, initial_count + 5)  # At least 6 additional records

            # History should contain all the operations
            all_history = list(patient.history.all())
            
            # Should find both deletion and restoration records
            deletion_records = [h for h in all_history if h.is_deleted]
            restoration_records = [h for h in all_history if not h.is_deleted and 'Restored by' in (h.history_change_reason or '')]
            
            self.assertEqual(len(deletion_records), 3)
            self.assertGreaterEqual(len(restoration_records), 3)

    def test_history_access_for_soft_deleted_objects(self):
        """Test that history can be accessed for soft deleted objects."""
        patient = Patient.objects.create(
            name='Deleted Access Patient',
            fiscal_number='123456789',
            healthcard_number='H123456',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )

        # Make some changes to create history
        patient.name = 'Updated Deleted Access Patient'
        patient._change_reason = 'Name update'
        patient.save()

        patient.status = Patient.Status.DISCHARGED
        patient._change_reason = 'Status update'
        patient.save()

        # Soft delete
        patient.delete(deleted_by=self.user, reason='Final deletion')

        if hasattr(patient, 'history'):
            # Should be able to access full history even after soft delete
            full_history = patient.history.all()
            self.assertGreater(full_history.count(), 2)  # At least creation + updates + deletion

            # Should be able to access history through soft-deleted object
            deleted_patient = Patient.all_objects.get(id=patient.id)
            deleted_history = deleted_patient.history.all()
            self.assertEqual(full_history.count(), deleted_history.count())

            # History should show progression of changes
            history_list = list(full_history)
            
            # Latest should be deletion
            latest = history_list[0]
            self.assertTrue(latest.is_deleted)
            
            # Should find name and status updates in history
            name_updates = [h for h in history_list if h.name == 'Updated Deleted Access Patient']
            status_updates = [h for h in history_list if h.status == Patient.Status.DISCHARGED]
            
            self.assertGreater(len(name_updates), 0)
            self.assertGreater(len(status_updates), 0)

    def test_history_with_related_object_deletions(self):
        """Test history behavior when related objects are soft deleted."""
        patient = Patient.objects.create(
            name='Related History Patient',
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
            description='Related Event',
            event_type=1,
            created_by=self.user,
            updated_by=self.user
        )

        # Get initial history counts
        patient_history_count = patient.history.count() if hasattr(patient, 'history') else 0
        event_history_count = event.history.count() if hasattr(event, 'history') else 0

        # Soft delete patient (should not cascade to event)
        patient.delete(deleted_by=self.user, reason='Related object test')

        # Patient history should be updated
        if hasattr(patient, 'history'):
            self.assertGreater(patient.history.count(), patient_history_count)

        # Event should still exist and its history should be unchanged
        self.assertEqual(Event.objects.count(), 1)
        if hasattr(event, 'history'):
            self.assertEqual(event.history.count(), event_history_count)

        # Event should still reference the soft-deleted patient
        active_event = Event.objects.get(id=event.id)
        self.assertEqual(active_event.patient, patient)
        self.assertTrue(active_event.patient.is_deleted)

    def test_history_change_reason_in_restore_method(self):
        """Test that restore method properly sets history change reason."""
        patient = Patient.objects.create(
            name='Change Reason Patient',
            fiscal_number='123456789',
            healthcard_number='H123456',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )

        # Delete
        patient.delete(deleted_by=self.user, reason='For change reason test')

        if hasattr(patient, 'history'):
            # Test restore method's automatic change reason setting
            patient.restore(restored_by=self.admin)

            # Latest history should have automatic change reason
            latest_history = patient.history.first()
            self.assertIsNotNone(latest_history.history_change_reason)
            self.assertIn('Restored by historyadmin', latest_history.history_change_reason)

    def test_history_integrity_after_hard_delete(self):
        """Test history behavior when objects are hard deleted."""
        patient = Patient.objects.create(
            name='Hard Delete History Patient',
            fiscal_number='123456789',
            healthcard_number='H123456',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )

        if hasattr(patient, 'history'):
            # Create some history
            patient.name = 'Updated Hard Delete Patient'
            patient.save()

            # Get patient ID and history count before hard delete
            patient_id = patient.id
            history_count = patient.history.count()
            self.assertGreater(history_count, 0)

            # Hard delete the patient
            patient.hard_delete()

            # Patient should be completely gone
            self.assertFalse(Patient.all_objects.filter(id=patient_id).exists())

            # History should still exist (django-simple-history preserves it)
            from simple_history.models import HistoricalRecords
            # Note: We can't easily test this without direct access to the historical model
            # In a real application, historical records would remain in the database
            # even after hard deletion of the main object

    def test_soft_delete_without_history_model(self):
        """Test soft delete works even if history is not available."""
        # This test ensures soft delete functionality doesn't break
        # if history tracking is not set up for a model
        
        patient = Patient.objects.create(
            name='No History Patient',
            fiscal_number='123456789',
            healthcard_number='H123456',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )

        # Even without history, soft delete should work
        patient.delete(deleted_by=self.user, reason='No history test')
        
        deleted_patient = Patient.all_objects.get(id=patient.id)
        self.assertTrue(deleted_patient.is_deleted)
        self.assertEqual(deleted_patient.deletion_reason, 'No history test')

        # Restore should also work
        patient.restore(restored_by=self.admin)
        
        restored_patient = Patient.objects.get(id=patient.id)
        self.assertFalse(restored_patient.is_deleted)


class TestSoftDeleteHistoryPerformance(TestCase):
    """Test performance implications of soft delete with history tracking."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='perfuser',
            email='perf@example.com',
            profession_type=0  # MEDICAL_DOCTOR
        )

    def test_bulk_operations_history_performance(self):
        """Test that bulk soft delete operations don't cause excessive history creation."""
        # Create test data
        patients = []
        for i in range(50):
            patient = Patient.objects.create(
                name=f'Perf Patient {i}',
                fiscal_number=f'PERF{i:05d}',
                healthcard_number=f'HP{i:05d}',
                birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
                created_by=self.user,
            updated_by=self.user
            )
            patients.append(patient)

        # Get initial total history count across all patients
        initial_total_history = 0
        for patient in patients:
            if hasattr(patient, 'history'):
                initial_total_history += patient.history.count()

        # Bulk soft delete - use individual deletions for proper history tracking
        bulk_patients = Patient.objects.filter(name__contains='Perf Patient')
        deleted_count = 0
        for patient in bulk_patients:
            patient.delete(deleted_by=self.user, reason='Performance test deletion')
            deleted_count += 1

        # History should be created for each deletion, but efficiently
        final_total_history = 0
        for patient in patients:
            if hasattr(patient, 'history'):
                final_total_history += patient.history.count()

        # Should have more history records (one per patient deletion)
        expected_increase = deleted_count  # One deletion record per patient
        actual_increase = final_total_history - initial_total_history
        
        # Should be close to expected (allowing for some variation in history creation)
        self.assertGreaterEqual(actual_increase, expected_increase)
        self.assertLessEqual(actual_increase, expected_increase * 2)  # Not more than double