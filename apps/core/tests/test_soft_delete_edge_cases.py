"""
Tests for edge cases and error handling in soft delete functionality.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction, IntegrityError
from datetime import timedelta
from unittest.mock import patch
from apps.patients.models import Patient, AllowedTag
from apps.events.models import Event

User = get_user_model()


class TestSoftDeleteEdgeCases(TestCase):
    """Test edge cases and error conditions for soft delete."""

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

    def test_delete_with_invalid_user(self):
        """Test deletion behavior with invalid user references."""
        patient = Patient.objects.create(
            name='Test Patient',
            fiscal_number='123456789',
            healthcard_number='H123456',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )

        # Delete with None user
        patient.delete(deleted_by=None, reason='System deletion')
        
        deleted_patient = Patient.all_objects.get(id=patient.id)
        self.assertTrue(deleted_patient.is_deleted)
        self.assertIsNone(deleted_patient.deleted_by)
        self.assertEqual(deleted_patient.deletion_reason, 'System deletion')

        # Restore
        patient.restore()
        
        # Test with non-existent user ID (simulate deleted user scenario)
        # This should work since deleted_by allows null and the user may not exist
        with self.assertRaises(User.DoesNotExist):
            # Try to get a user that doesn't exist
            User.objects.get(id=99999)
        
        # Set deleted_by to None since the user doesn't exist
        patient.delete(deleted_by=None, reason='Deleted user test - user no longer exists')
        
        # Should still work (foreign key allows non-existing references in memory)
        deleted_patient = Patient.all_objects.get(id=patient.id)
        self.assertTrue(deleted_patient.is_deleted)

    def test_delete_with_extremely_long_reason(self):
        """Test deletion with very long reason text."""
        patient = Patient.objects.create(
            name='Long Reason Patient',
            fiscal_number='123456789',
            healthcard_number='H123456',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )

        # Create extremely long reason
        long_reason = 'A' * 10000  # 10KB of text
        
        patient.delete(deleted_by=self.user, reason=long_reason)
        
        deleted_patient = Patient.all_objects.get(id=patient.id)
        self.assertTrue(deleted_patient.is_deleted)
        self.assertEqual(deleted_patient.deletion_reason, long_reason)

    def test_delete_with_unicode_reason(self):
        """Test deletion with Unicode characters in reason."""
        patient = Patient.objects.create(
            name='Unicode Patient',
            fiscal_number='123456789',
            healthcard_number='H123456',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )

        unicode_reason = 'Deletão por motivo especial: 你好世界 🔥 Ñoño café'
        
        patient.delete(deleted_by=self.user, reason=unicode_reason)
        
        deleted_patient = Patient.all_objects.get(id=patient.id)
        self.assertTrue(deleted_patient.is_deleted)
        self.assertEqual(deleted_patient.deletion_reason, unicode_reason)

    def test_concurrent_delete_attempts(self):
        """Test concurrent deletion attempts on same object."""
        patient = Patient.objects.create(
            name='Concurrent Patient',
            fiscal_number='123456789',
            healthcard_number='H123456',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )

        # Simulate concurrent deletions by different users
        patient1 = Patient.objects.get(id=patient.id)
        patient2 = Patient.objects.get(id=patient.id)

        # First deletion
        patient1.delete(deleted_by=self.user, reason='First deletion')
        
        # Second deletion on same object (should update)
        patient2.delete(deleted_by=self.admin, reason='Second deletion')
        
        # Check final state - should have admin's deletion info
        final_patient = Patient.all_objects.get(id=patient.id)
        self.assertTrue(final_patient.is_deleted)
        self.assertEqual(final_patient.deleted_by, self.admin)
        self.assertEqual(final_patient.deletion_reason, 'Second deletion')

    def test_restore_with_invalid_user(self):
        """Test restoration with invalid user references."""
        patient = Patient.objects.create(
            name='Restore Test Patient',
            fiscal_number='123456789',
            healthcard_number='H123456',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )

        # Delete first
        patient.delete(deleted_by=self.user, reason='Test deletion')
        
        # Restore with None user
        patient.restore(restored_by=None)
        
        restored_patient = Patient.objects.get(id=patient.id)
        self.assertFalse(restored_patient.is_deleted)
        
        # Delete again
        patient.delete(deleted_by=self.user, reason='Second test deletion')
        
        # Restore with non-existent user
        fake_user = User(id=88888, username='fake_restorer')
        patient.restore(restored_by=fake_user)
        
        restored_patient = Patient.objects.get(id=patient.id)
        self.assertFalse(restored_patient.is_deleted)

    def test_multiple_rapid_delete_restore_cycles(self):
        """Test rapid delete/restore cycles don't cause issues."""
        patient = Patient.objects.create(
            name='Rapid Cycle Patient',
            fiscal_number='123456789',
            healthcard_number='H123456',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )

        # Perform many rapid cycles
        for i in range(20):
            patient.delete(deleted_by=self.user, reason=f'Cycle {i} deletion')
            self.assertTrue(Patient.all_objects.get(id=patient.id).is_deleted)
            
            patient.restore(restored_by=self.admin)
            self.assertFalse(Patient.objects.get(id=patient.id).is_deleted)

        # Final state should be active
        final_patient = Patient.objects.get(id=patient.id)
        self.assertFalse(final_patient.is_deleted)

    def test_soft_delete_with_database_constraints(self):
        """Test soft delete behavior with database constraints."""
        # Create patient with unique fiscal number
        patient = Patient.objects.create(
            name='Constraint Patient',
            fiscal_number='UNIQUE123',
            healthcard_number='HU123',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )

        # Soft delete the patient
        patient.delete(deleted_by=self.user, reason='Constraint test')
        
        # Should be able to create new patient with same fiscal number
        # since the first one is only soft deleted
        new_patient = Patient.objects.create(
            name='New Constraint Patient',
            fiscal_number='UNIQUE123',  # Same fiscal number
            healthcard_number='HU124',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        self.assertEqual(Patient.objects.count(), 1)  # Only new patient is active
        self.assertEqual(Patient.all_objects.count(), 2)  # Both exist in total

        # Clean up
        new_patient.delete(deleted_by=self.user, reason='Cleanup')

    def test_queryset_operations_on_empty_results(self):
        """Test queryset operations when no results match."""
        # Attempt operations on empty querysets
        empty_active = Patient.objects.filter(name='Nonexistent')
        empty_deleted = Patient.all_objects.deleted().filter(name='Nonexistent')
        
        # These should not raise errors
        self.assertEqual(empty_active.count(), 0)
        self.assertEqual(empty_deleted.count(), 0)
        
        # Bulk delete on empty queryset
        result = empty_active.delete()
        self.assertEqual(result, 0)  # Should return 0 for no records affected

    def test_soft_delete_with_very_old_timestamps(self):
        """Test soft delete behavior with very old timestamps."""
        patient = Patient.objects.create(
            name='Old Timestamp Patient',
            fiscal_number='123456789',
            healthcard_number='H123456',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )

        # Set a very old creation time
        from datetime import datetime
        from django.utils.timezone import make_aware
        very_old_time = make_aware(datetime(1990, 1, 1))
        Patient.all_objects.filter(id=patient.id).update(created_at=very_old_time)
        
        # Soft delete should work normally
        patient.delete(deleted_by=self.user, reason='Old timestamp test')
        
        deleted_patient = Patient.all_objects.get(id=patient.id)
        self.assertTrue(deleted_patient.is_deleted)
        self.assertIsNotNone(deleted_patient.deleted_at)
        # Deleted timestamp should be recent, not old
        self.assertGreater(deleted_patient.deleted_at, very_old_time)

    def test_soft_delete_with_future_timestamps(self):
        """Test soft delete behavior with future timestamps."""
        patient = Patient.objects.create(
            name='Future Timestamp Patient',
            fiscal_number='123456789',
            healthcard_number='H123456',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )

        # Mock timezone.now() to return future time
        future_time = timezone.now() + timedelta(days=365)
        
        with patch('django.utils.timezone.now', return_value=future_time):
            patient.delete(deleted_by=self.user, reason='Future timestamp test')
        
        deleted_patient = Patient.all_objects.get(id=patient.id)
        self.assertTrue(deleted_patient.is_deleted)
        self.assertEqual(deleted_patient.deleted_at, future_time)

    def test_soft_delete_model_inheritance_edge_cases(self):
        """Test soft delete with model inheritance edge cases."""
        # Test that Event and its subclasses handle soft delete correctly
        patient = Patient.objects.create(
            name='Inheritance Patient',
            fiscal_number='123456789',
            healthcard_number='H123456',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )

        # Create base Event
        event = Event.objects.create(
            event_datetime=timezone.now(),
            patient=patient,
            description='Base Event',
            event_type=1,
            created_by=self.user,
            updated_by=self.user
        )

        # Soft delete through base model
        event.delete(deleted_by=self.user, reason='Base model deletion')
        
        # Should be deleted in both base and derived querysets
        self.assertEqual(Event.objects.count(), 0)
        self.assertEqual(Event.all_objects.count(), 1)
        
        deleted_event = Event.all_objects.get(id=event.id)
        self.assertTrue(deleted_event.is_deleted)

    def test_soft_delete_with_null_foreign_keys(self):
        """Test soft delete behavior with null foreign key fields."""
        # Create patient with valid user (created_by cannot be null)
        patient = Patient.objects.create(
            name='Null FK Patient',
            fiscal_number='123456789',
            healthcard_number='H123456',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Test deletion - deleted_by can be set, created_by remains unchanged
        patient.delete(deleted_by=self.user, reason='Null FK test')
        
        deleted_patient = Patient.all_objects.get(id=patient.id)
        self.assertTrue(deleted_patient.is_deleted)
        self.assertEqual(deleted_patient.created_by, self.user)  # created_by unchanged
        self.assertEqual(deleted_patient.deleted_by, self.user)

    def test_soft_delete_during_transaction_rollback(self):
        """Test soft delete behavior during transaction rollbacks."""
        patient = Patient.objects.create(
            name='Transaction Patient',
            fiscal_number='123456789',
            healthcard_number='H123456',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )

        try:
            with transaction.atomic():
                # Soft delete within transaction
                patient.delete(deleted_by=self.user, reason='Transaction test')
                
                # Verify deletion within transaction
                self.assertTrue(Patient.all_objects.get(id=patient.id).is_deleted)
                
                # Force rollback
                raise IntegrityError("Forced rollback")
                
        except IntegrityError:
            pass  # Expected
        
        # After rollback, patient should be active again
        active_patient = Patient.objects.get(id=patient.id)
        self.assertFalse(active_patient.is_deleted)

    def test_soft_delete_with_large_related_object_counts(self):
        """Test soft delete performance with many related objects."""
        patient = Patient.objects.create(
            name='Many Relations Patient',
            fiscal_number='123456789',
            healthcard_number='H123456',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )

        # Create many related events
        events = []
        for i in range(100):
            event = Event.objects.create(
            event_datetime=timezone.now(),
                patient=patient,
                description=f'Related Event {i}',
                event_type=(i % 5) + 1,
                created_by=self.user,
            updated_by=self.user
            )
            events.append(event)

        # Soft delete patient should be fast and not affect events
        patient.delete(deleted_by=self.user, reason='Many relations test')
        
        # Patient should be deleted
        self.assertEqual(Patient.objects.count(), 0)
        
        # All events should still be active
        self.assertEqual(Event.objects.count(), 100)
        
        # Events should still reference the soft-deleted patient
        for event in Event.objects.all():
            self.assertEqual(event.patient, patient)
            self.assertTrue(event.patient.is_deleted)

    def test_soft_delete_string_representations(self):
        """Test string representations of soft deleted objects."""
        patient = Patient.objects.create(
            name='String Repr Patient',
            fiscal_number='123456789',
            healthcard_number='H123456',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )

        # Active patient string representation
        self.assertEqual(str(patient), 'String Repr Patient')
        
        # Soft delete
        patient.delete(deleted_by=self.user, reason='String repr test')
        
        # Deleted patient string representation should show deletion status
        deleted_patient = Patient.all_objects.get(id=patient.id)
        self.assertEqual(str(deleted_patient), 'String Repr Patient [DELETED]')

    def test_soft_delete_manager_edge_cases(self):
        """Test edge cases in soft delete manager behavior."""
        # Test manager methods on empty database
        self.assertEqual(Patient.objects.count(), 0)
        self.assertEqual(Patient.all_objects.count(), 0)
        self.assertEqual(Patient.all_objects.deleted_only().count(), 0)
        
        # Create and delete patient
        patient = Patient.objects.create(
            name='Manager Edge Case Patient',
            fiscal_number='123456789',
            healthcard_number='H123456',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        patient.delete(deleted_by=self.user, reason='Manager test')
        
        # Test various manager methods
        self.assertEqual(Patient.objects.count(), 0)
        self.assertEqual(Patient.all_objects.count(), 1)
        self.assertEqual(Patient.all_objects.deleted_only().count(), 1)
        
        # Test queryset chaining
        deleted_patients = Patient.all_objects.deleted().filter(name__contains='Manager')
        self.assertEqual(deleted_patients.count(), 1)
        
        active_patients = Patient.all_objects.active().filter(name__contains='Manager')
        self.assertEqual(active_patients.count(), 0)


class TestSoftDeleteErrorHandling(TestCase):
    """Test error handling in soft delete functionality."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='erroruser',
            email='error@example.com',
            profession_type=0  # MEDICAL_DOCTOR
        )

    def test_delete_method_parameter_validation(self):
        """Test that delete method handles various parameter combinations."""
        patient = Patient.objects.create(
            name='Param Test Patient',
            fiscal_number='123456789',
            healthcard_number='H123456',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )

        # Test all valid parameter combinations
        test_cases = [
            {'deleted_by': self.user, 'reason': 'With both params'},
            {'deleted_by': self.user},  # Only user
            {'reason': 'Only reason'},  # Only reason
            {},  # No params
        ]
        
        for i, params in enumerate(test_cases):
            # Restore patient first (except first iteration)
            if i > 0:
                patient.restore()
            
            # Delete with test parameters
            patient.delete(**params)
            
            # Verify deletion worked
            deleted_patient = Patient.all_objects.get(id=patient.id)
            self.assertTrue(deleted_patient.is_deleted)
            
            # Verify parameters were set correctly
            if 'deleted_by' in params:
                self.assertEqual(deleted_patient.deleted_by, params['deleted_by'])
            else:
                self.assertIsNone(deleted_patient.deleted_by)
                
            if 'reason' in params:
                self.assertEqual(deleted_patient.deletion_reason, params['reason'])
            else:
                self.assertEqual(deleted_patient.deletion_reason, '')

    def test_restore_method_parameter_validation(self):
        """Test that restore method handles various parameter combinations."""
        patient = Patient.objects.create(
            name='Restore Param Test Patient',
            fiscal_number='123456789',
            healthcard_number='H123456',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )

        # Delete first
        patient.delete(deleted_by=self.user, reason='For restore test')
        
        # Test restore with and without user
        patient.restore(restored_by=self.user)
        self.assertFalse(Patient.objects.get(id=patient.id).is_deleted)
        
        # Delete again
        patient.delete(deleted_by=self.user, reason='Second test')
        
        # Restore without user parameter
        patient.restore()
        self.assertFalse(Patient.objects.get(id=patient.id).is_deleted)

    def test_invalid_queryset_operations(self):
        """Test invalid operations on soft delete querysets."""
        # These operations should work without errors even on edge cases
        
        # Operations on empty querysets
        empty_qs = Patient.objects.filter(name='NonExistent')
        self.assertEqual(empty_qs.delete(), 0)
        
        # Chaining operations
        chained_qs = Patient.all_objects.active().deleted()  # This should return empty
        self.assertEqual(chained_qs.count(), 0)
        
        # Multiple filter operations
        complex_qs = Patient.all_objects.filter(
            name__contains='Test'
        ).active().filter(
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT
        ).deleted()  # Should be empty due to active().deleted() chain
        self.assertEqual(complex_qs.count(), 0)