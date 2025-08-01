"""
Tests for soft delete functionality in Patient models.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from apps.patients.models import Patient, AllowedTag
from apps.events.models import Event

User = get_user_model()


class TestPatientSoftDelete(TestCase):
    """Test soft delete functionality for Patient model."""

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

    def test_patient_soft_delete(self):
        """Test that patient soft delete works correctly."""
        patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            fiscal_number='123456789',
            healthcard_number='H123456',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        patient_id = patient.id

        # Soft delete the patient
        patient.delete(deleted_by=self.user, reason='Test deletion')

        # Patient should not appear in normal queries
        self.assertEqual(Patient.objects.count(), 0)
        self.assertFalse(Patient.objects.filter(id=patient_id).exists())

        # Patient should appear in all_objects queries
        self.assertEqual(Patient.all_objects.count(), 1)
        self.assertTrue(Patient.all_objects.filter(id=patient_id).exists())

        # Check deletion fields are set correctly
        deleted_patient = Patient.all_objects.get(id=patient_id)
        self.assertTrue(deleted_patient.is_deleted)
        self.assertEqual(deleted_patient.deleted_by, self.user)
        self.assertEqual(deleted_patient.deletion_reason, 'Test deletion')
        self.assertIsNotNone(deleted_patient.deleted_at)
        self.assertTrue(
            deleted_patient.deleted_at <= timezone.now()
        )

    def test_patient_restore(self):
        """Test that patient restoration works correctly."""
        patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            fiscal_number='123456789',
            healthcard_number='H123456',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        patient_id = patient.id

        # Soft delete then restore
        patient.delete(deleted_by=self.user, reason='Test deletion')
        patient.restore(restored_by=self.admin)

        # Patient should appear in normal queries again
        self.assertEqual(Patient.objects.count(), 1)
        self.assertTrue(Patient.objects.filter(id=patient_id).exists())

        # Check restoration cleared deletion fields
        restored_patient = Patient.objects.get(id=patient_id)
        self.assertFalse(restored_patient.is_deleted)
        self.assertIsNone(restored_patient.deleted_at)
        self.assertIsNone(restored_patient.deleted_by)
        self.assertEqual(restored_patient.deletion_reason, '')

    def test_patient_hard_delete(self):
        """Test that hard delete permanently removes patient."""
        patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            fiscal_number='123456789',
            healthcard_number='H123456',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        patient_id = patient.id

        # Hard delete the patient
        patient.hard_delete()

        # Patient should not exist anywhere
        self.assertEqual(Patient.objects.count(), 0)
        self.assertEqual(Patient.all_objects.count(), 0)
        self.assertFalse(Patient.all_objects.filter(id=patient_id).exists())

    def test_queryset_delete_method(self):
        """Test that queryset delete method soft deletes all objects."""
        # Create multiple patients
        patients = []
        for i in range(3):
            patient = Patient.objects.create(
                name=f'Test Patient {i}',
                birthday='1990-01-01',
                fiscal_number=f'12345678{i}',
                healthcard_number=f'H12345{i}',
                status=Patient.Status.INPATIENT,
                created_by=self.user,
            updated_by=self.user
            )
            patients.append(patient)

        # Soft delete all patients
        Patient.objects.all().delete()

        # All patients should be soft deleted
        self.assertEqual(Patient.objects.count(), 0)
        self.assertEqual(Patient.all_objects.count(), 3)

        # All should be marked as deleted
        for patient in Patient.all_objects.all():
            self.assertTrue(patient.is_deleted)
            self.assertIsNotNone(patient.deleted_at)

    def test_queryset_filters(self):
        """Test that queryset filters work correctly."""
        # Create mix of active and deleted patients
        active_patient = Patient.objects.create(
            name='Active Patient',
            birthday='1990-01-01',
            fiscal_number='123456789',
            healthcard_number='H123456',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        deleted_patient = Patient.objects.create(
            name='Deleted Patient',
            birthday='1990-01-01',
            fiscal_number='987654321',
            healthcard_number='H987654',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        deleted_patient.delete(deleted_by=self.user, reason='Test')

        # Test default manager (active only)
        self.assertEqual(Patient.objects.count(), 1)
        self.assertEqual(Patient.objects.first(), active_patient)

        # Test all_objects manager
        self.assertEqual(Patient.all_objects.count(), 2)

        # Test queryset methods
        active_patients = Patient.all_objects.active()
        self.assertEqual(active_patients.count(), 1)
        self.assertEqual(active_patients.first(), active_patient)

        deleted_patients = Patient.all_objects.deleted()
        self.assertEqual(deleted_patients.count(), 1)
        self.assertEqual(deleted_patients.first(), deleted_patient)

        all_patients = Patient.all_objects.with_deleted()
        self.assertEqual(all_patients.count(), 2)

    def test_patient_str_method_with_deletion(self):
        """Test that __str__ method shows deletion status."""
        patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            fiscal_number='123456789',
            healthcard_number='H123456',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )

        # Active patient should not show deletion indicator
        self.assertEqual(str(patient), 'Test Patient')

        # Deleted patient should show deletion indicator
        patient.delete(deleted_by=self.user, reason='Test')
        deleted_patient = Patient.all_objects.get(id=patient.id)
        self.assertEqual(str(deleted_patient), 'Test Patient [DELETED]')

    def test_cascade_soft_delete_with_events(self):
        """Test that related objects handle patient soft deletes properly."""
        patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            fiscal_number='123456789',
            healthcard_number='H123456',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )

        # Create related event
        event = Event.objects.create(
            event_datetime=timezone.now(),
            patient=patient,
            description='Test event',
            event_type=1,
            created_by=self.user,
            updated_by=self.user
        )

        # Soft delete patient
        patient.delete(deleted_by=self.user, reason='Test deletion')

        # Event should still exist and reference the patient
        self.assertEqual(Event.objects.count(), 1)
        retrieved_event = Event.objects.first()
        self.assertEqual(retrieved_event.patient, patient)
        
        # We should be able to access the patient through the event
        # even though the patient is soft deleted
        self.assertEqual(retrieved_event.patient.name, 'Test Patient')
        self.assertTrue(retrieved_event.patient.is_deleted)

    def test_multiple_delete_restore_cycles(self):
        """Test that multiple delete/restore cycles work correctly."""
        patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            fiscal_number='123456789',
            healthcard_number='H123456',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )

        # Delete and restore multiple times
        for i in range(3):
            # Delete
            patient.delete(deleted_by=self.user, reason=f'Test deletion {i}')
            self.assertTrue(Patient.all_objects.get(id=patient.id).is_deleted)
            self.assertEqual(Patient.objects.count(), 0)

            # Restore
            patient.restore(restored_by=self.admin)
            self.assertFalse(Patient.objects.get(id=patient.id).is_deleted)
            self.assertEqual(Patient.objects.count(), 1)

    def test_delete_without_reason(self):
        """Test that deletion works without a reason."""
        patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            fiscal_number='123456789',
            healthcard_number='H123456',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )

        # Delete without reason
        patient.delete(deleted_by=self.user)

        deleted_patient = Patient.all_objects.get(id=patient.id)
        self.assertTrue(deleted_patient.is_deleted)
        self.assertEqual(deleted_patient.deletion_reason, '')

    def test_delete_without_user(self):
        """Test that deletion works without specifying deleted_by user."""
        patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            fiscal_number='123456789',
            healthcard_number='H123456',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )

        # Delete without user
        patient.delete(reason='System deletion')

        deleted_patient = Patient.all_objects.get(id=patient.id)
        self.assertTrue(deleted_patient.is_deleted)
        self.assertIsNone(deleted_patient.deleted_by)
        self.assertEqual(deleted_patient.deletion_reason, 'System deletion')


class TestAllowedTagSoftDelete(TestCase):
    """Test soft delete functionality for AllowedTag model."""

    def setUp(self):
        self.user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com'
        )

    def test_allowed_tag_soft_delete(self):
        """Test that AllowedTag soft delete works correctly."""
        tag = AllowedTag.objects.create(
            name='Test Tag',
            color='#FF0000',
            created_by=self.user,
            updated_by=self.user
        )
        tag_id = tag.id

        # Soft delete the tag
        tag.delete(deleted_by=self.user, reason='Test deletion')

        # Tag should not appear in normal queries
        self.assertEqual(AllowedTag.objects.count(), 0)
        self.assertFalse(AllowedTag.objects.filter(id=tag_id).exists())

        # Tag should appear in all_objects queries
        self.assertEqual(AllowedTag.all_objects.count(), 1)
        deleted_tag = AllowedTag.all_objects.get(id=tag_id)
        self.assertTrue(deleted_tag.is_deleted)
        self.assertEqual(deleted_tag.deleted_by, self.user)

    def test_allowed_tag_restore(self):
        """Test that AllowedTag restoration works correctly."""
        tag = AllowedTag.objects.create(
            name='Test Tag',
            color='#FF0000',
            created_by=self.user,
            updated_by=self.user
        )

        # Soft delete then restore
        tag.delete(deleted_by=self.user, reason='Test deletion')
        tag.restore(restored_by=self.user)

        # Tag should appear in normal queries again
        self.assertEqual(AllowedTag.objects.count(), 1)
        restored_tag = AllowedTag.objects.first()
        self.assertFalse(restored_tag.is_deleted)
        self.assertIsNone(restored_tag.deleted_at)


class TestSoftDeleteEdgeCases(TestCase):
    """Test edge cases and error conditions for soft delete."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            profession_type=0  # MEDICAL_DOCTOR
        )

    def test_delete_already_deleted_patient(self):
        """Test deleting an already deleted patient."""
        patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            fiscal_number='123456789',
            healthcard_number='H123456',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )

        # Delete once
        patient.delete(deleted_by=self.user, reason='First deletion')
        first_deleted_at = Patient.all_objects.get(id=patient.id).deleted_at

        # Delete again
        patient.delete(deleted_by=self.user, reason='Second deletion')
        
        # Should update the deletion info
        deleted_patient = Patient.all_objects.get(id=patient.id)
        self.assertEqual(deleted_patient.deletion_reason, 'Second deletion')
        self.assertGreaterEqual(deleted_patient.deleted_at, first_deleted_at)

    def test_restore_non_deleted_patient(self):
        """Test restoring a patient that wasn't deleted."""
        patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            fiscal_number='123456789',
            healthcard_number='H123456',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )

        # Restore without deleting first
        patient.restore(restored_by=self.user)

        # Should still be active and unchanged
        self.assertEqual(Patient.objects.count(), 1)
        active_patient = Patient.objects.get(id=patient.id)
        self.assertFalse(active_patient.is_deleted)
        self.assertIsNone(active_patient.deleted_at)

    def test_performance_with_large_dataset(self):
        """Test soft delete performance with larger dataset."""
        # Create many patients
        patients = []
        for i in range(100):
            patient = Patient.objects.create(
                name=f'Patient {i}',
                birthday='1990-01-01',
                fiscal_number=f'12345{i:04d}',
                healthcard_number=f'H{i:05d}',
                status=Patient.Status.INPATIENT,
                created_by=self.user,
            updated_by=self.user
            )
            patients.append(patient)

        # Soft delete half of them
        for i in range(0, 100, 2):
            patients[i].delete(deleted_by=self.user, reason=f'Deletion {i}')

        # Verify counts
        self.assertEqual(Patient.objects.count(), 50)  # Active patients
        self.assertEqual(Patient.all_objects.count(), 100)  # All patients
        self.assertEqual(Patient.all_objects.deleted().count(), 50)  # Deleted patients

        # Test that queries still work efficiently
        active_patients = list(Patient.objects.all())
        self.assertEqual(len(active_patients), 50)
        
        # All active patients should not be deleted
        for patient in active_patients:
            self.assertFalse(patient.is_deleted)