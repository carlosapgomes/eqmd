"""
Tests for medical specialty models (Phase 1: TDD - Tests First).

This file contains tests for MedicalSpecialty and UserSpecialty models
following Test-Driven Development (TDD) principles.
"""
import uuid
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from apps.accounts.models import (
    MedicalSpecialty,
    UserSpecialty,
    UserProfile
)
from django.contrib.auth import get_user_model
from apps.accounts.tests.factories import (
    UserFactory,
    DoctorFactory,
    ResidentFactory
)

User = get_user_model()


# ============================================================================
# TASK 1.1: Tests for MedicalSpecialty Model Creation and Validation
# ============================================================================

class MedicalSpecialtyModelTestCase(TestCase):
    """Test cases for the MedicalSpecialty model (Task 1.1)."""

    def test_create_medical_specialty_with_required_fields(self):
        """
        Test creating a medical specialty with required fields only.

        **WHEN** an administrator creates a medical specialty with name,
        abbreviation, and optional description
        **THEN** the specialty is saved in the database with is_active=True
        and generated timestamps
        """
        specialty = MedicalSpecialty.objects.create(
            name='Cirurgia Vascular',
            abbreviation='CIRVASC'
        )

        self.assertIsNotNone(specialty.id)
        self.assertIsInstance(specialty.id, uuid.UUID)
        self.assertEqual(specialty.name, 'Cirurgia Vascular')
        self.assertEqual(specialty.abbreviation, 'CIRVASC')
        self.assertEqual(specialty.description, '')
        self.assertTrue(specialty.is_active)
        self.assertIsNotNone(specialty.created_at)
        self.assertIsNotNone(specialty.updated_at)

    def test_create_medical_specialty_with_description(self):
        """Test creating a medical specialty with all fields."""
        specialty = MedicalSpecialty.objects.create(
            name='Cirurgia Cardíaca',
            abbreviation='CIRCARD',
            description='Especialidade cirúrgica focada no coração e grandes vasos'
        )

        self.assertEqual(specialty.name, 'Cirurgia Cardíaca')
        self.assertEqual(specialty.abbreviation, 'CIRCARD')
        self.assertEqual(
            specialty.description,
            'Especialidade cirúrgica focada no coração e grandes vasos'
        )

    def test_medical_specialty_string_representation(self):
        """Test that __str__ returns the specialty name."""
        specialty = MedicalSpecialty.objects.create(
            name='Cardiologia',
            abbreviation='CARDIO'
        )

        self.assertEqual(str(specialty), 'Cardiologia')

    def test_medical_specialty_name_must_be_unique(self):
        """
        Test unique specialty constraint on name.

        **WHEN** an administrator attempts to create a specialty with a
        duplicate name or abbreviation
        **THEN** the system rejects the creation with a validation error
        """
        MedicalSpecialty.objects.create(
            name='Cirurgia Geral',
            abbreviation='CIRGER'
        )

        # Try to create with duplicate name
        with self.assertRaises(IntegrityError):
            MedicalSpecialty.objects.create(
                name='Cirurgia Geral',
                abbreviation='CIRGER2'
            )

    def test_medical_specialty_abbreviation_must_be_unique(self):
        """Test unique specialty constraint on abbreviation."""
        MedicalSpecialty.objects.create(
            name='Cirurgia Geral',
            abbreviation='CIRGER'
        )

        # Try to create with duplicate abbreviation
        with self.assertRaises(IntegrityError):
            MedicalSpecialty.objects.create(
                name='Cirurgia Geral 2',
                abbreviation='CIRGER'
            )

    def test_medical_specialty_ordering(self):
        """Test that specialties are ordered by name."""
        MedicalSpecialty.objects.create(
            name='Ortopedia',
            abbreviation='ORTO'
        )
        MedicalSpecialty.objects.create(
            name='Cardiologia',
            abbreviation='CARDIO'
        )
        MedicalSpecialty.objects.create(
            name='Pediatria',
            abbreviation='PED'
        )

        specialties = list(MedicalSpecialty.objects.all())
        self.assertEqual(specialties[0].name, 'Cardiologia')
        self.assertEqual(specialties[1].name, 'Ortopedia')
        self.assertEqual(specialties[2].name, 'Pediatria')

    def test_medical_specialty_verbose_names(self):
        """Test verbose names for admin display."""
        specialty = MedicalSpecialty(
            name='Teste',
            abbreviation='TEST'
        )

        self.assertEqual(
            MedicalSpecialty._meta.verbose_name,
            'Especialidade Médica'
        )
        self.assertEqual(
            MedicalSpecialty._meta.verbose_name_plural,
            'Especialidades Médicas'
        )

    def test_medical_specialty_soft_delete(self):
        """
        Test soft delete functionality.

        **WHEN** an administrator sets is_active=False on a specialty
        **THEN** the specialty is no longer available for assignment but
        existing assignments are preserved
        """
        specialty = MedicalSpecialty.objects.create(
            name='Cardiologia',
            abbreviation='CARDIO',
            is_active=True
        )

        self.assertTrue(specialty.is_active)

        # Soft delete
        specialty.is_active = False
        specialty.save()

        # Refresh from database
        specialty.refresh_from_db()
        self.assertFalse(specialty.is_active)

        # Specialty still exists in database (not hard deleted)
        self.assertIsNotNone(
            MedicalSpecialty.objects.filter(id=specialty.id).first()
        )

    def test_medical_specialty_field_max_lengths(self):
        """Test that field max lengths are respected."""
        # Name max length is 100
        long_name = 'A' * 100
        specialty = MedicalSpecialty.objects.create(
            name=long_name,
            abbreviation='TEST'
        )
        self.assertEqual(len(specialty.name), 100)

        # Abbreviation max length is 10
        long_abbr = 'ABCDEFGHIJ'  # 10 characters
        specialty2 = MedicalSpecialty.objects.create(
            name='Test 2',
            abbreviation=long_abbr
        )
        self.assertEqual(len(specialty2.abbreviation), 10)

    def test_medical_specialty_description_can_be_blank(self):
        """Test that description field is optional (blank=True)."""
        specialty = MedicalSpecialty.objects.create(
            name='Teste',
            abbreviation='TEST'
        )
        self.assertEqual(specialty.description, '')


# ============================================================================
# TASK 1.2: Tests for UserSpecialty Model Creation and Constraints
# ============================================================================

class UserSpecialtyModelTestCase(TestCase):
    """Test cases for the UserSpecialty model (Task 1.2)."""

    def setUp(self):
        """Set up test data."""
        self.specialty = MedicalSpecialty.objects.create(
            name='Cirurgia Geral',
            abbreviation='CIRGER'
        )
        self.user = DoctorFactory()

    def test_create_user_specialty(self):
        """
        Test creating a user-specialty assignment.

        **WHEN** an administrator assigns a specialty to a user via the
        user admin inline
        **THEN** a UserSpecialty record is created with the user, specialty,
        assigned_at timestamp, and assigned_by set to the current admin user
        """
        admin_user = UserFactory(is_staff=True)

        user_specialty = UserSpecialty.objects.create(
            user=self.user,
            specialty=self.specialty,
            is_primary=False,
            assigned_by=admin_user
        )

        self.assertIsNotNone(user_specialty.id)
        self.assertIsInstance(user_specialty.id, uuid.UUID)
        self.assertEqual(user_specialty.user, self.user)
        self.assertEqual(user_specialty.specialty, self.specialty)
        self.assertFalse(user_specialty.is_primary)
        self.assertIsNotNone(user_specialty.assigned_at)
        self.assertEqual(user_specialty.assigned_by, admin_user)

    def test_create_user_specialty_without_assigned_by(self):
        """Test creating a user-specialty without specifying assigned_by."""
        user_specialty = UserSpecialty.objects.create(
            user=self.user,
            specialty=self.specialty
        )

        self.assertIsNone(user_specialty.assigned_by)

    def test_user_specialty_string_representation(self):
        """Test __str__ returns user name and specialty name."""
        user_specialty = UserSpecialty.objects.create(
            user=self.user,
            specialty=self.specialty
        )

        expected = f"{self.user.get_full_name()} - {self.specialty.name}"
        self.assertEqual(str(user_specialty), expected)

    def test_user_specialty_prevents_duplicate_assignments(self):
        """
        Test unique constraint on (user, specialty).

        **WHEN** an administrator attempts to assign the same specialty to
        a user twice
        **THEN** the system prevents the duplicate assignment due to the
        unique constraint on (user, specialty)
        """
        UserSpecialty.objects.create(
            user=self.user,
            specialty=self.specialty
        )

        # Try to create duplicate assignment
        with self.assertRaises(IntegrityError):
            UserSpecialty.objects.create(
                user=self.user,
                specialty=self.specialty
            )

    def test_user_can_have_multiple_specialties(self):
        """Test that a user can have multiple different specialties."""
        specialty2 = MedicalSpecialty.objects.create(
            name='Cirurgia Vascular',
            abbreviation='CIRVASC'
        )

        UserSpecialty.objects.create(
            user=self.user,
            specialty=self.specialty,
            is_primary=True
        )
        UserSpecialty.objects.create(
            user=self.user,
            specialty=specialty2,
            is_primary=False
        )

        self.assertEqual(self.user.user_specialties.count(), 2)

    def test_user_specialty_ordering(self):
        """Test that user specialties are ordered by is_primary desc, then name."""
        specialty2 = MedicalSpecialty.objects.create(
            name='Cirurgia Vascular',
            abbreviation='CIRVASC'
        )
        specialty3 = MedicalSpecialty.objects.create(
            name='Ortopedia',
            abbreviation='ORTO'
        )

        # Create specialties in non-ordered way
        UserSpecialty.objects.create(
            user=self.user,
            specialty=specialty2,
            is_primary=False
        )
        UserSpecialty.objects.create(
            user=self.user,
            specialty=self.specialty,
            is_primary=True
        )
        UserSpecialty.objects.create(
            user=self.user,
            specialty=specialty3,
            is_primary=False
        )

        specialties = list(self.user.user_specialties.all())

        # Primary should be first
        self.assertTrue(specialties[0].is_primary)
        self.assertEqual(specialties[0].specialty.name, 'Cirurgia Geral')

        # Others should be ordered by name
        self.assertEqual(specialties[1].specialty.name, 'Cirurgia Vascular')
        self.assertEqual(specialties[2].specialty.name, 'Ortopedia')

    def test_user_specialty_verbose_names(self):
        """Test verbose names for admin display."""
        user_specialty = UserSpecialty(
            user=self.user,
            specialty=self.specialty
        )

        self.assertEqual(
            UserSpecialty._meta.verbose_name,
            'Especialidade do Usuário'
        )
        self.assertEqual(
            UserSpecialty._meta.verbose_name_plural,
            'Especialidades dos Usuários'
        )

    def test_user_specialty_assigned_at_is_auto_now_add(self):
        """Test that assigned_at is automatically set on creation."""
        import time
        from django.utils import timezone

        before = timezone.now()
        time.sleep(0.01)  # Small delay to ensure timestamp changes

        user_specialty = UserSpecialty.objects.create(
            user=self.user,
            specialty=self.specialty
        )

        after = timezone.now()

        self.assertIsNotNone(user_specialty.assigned_at)
        self.assertGreaterEqual(user_specialty.assigned_at, before)
        self.assertLessEqual(user_specialty.assigned_at, after)


# ============================================================================
# TASK 1.3: Tests for UserProfile.current_specialty Field
# ============================================================================

class UserProfileCurrentSpecialtyTestCase(TestCase):
    """Test cases for UserProfile.current_specialty field (Task 1.3)."""

    def setUp(self):
        """Set up test data."""
        self.user = DoctorFactory()
        self.specialty1 = MedicalSpecialty.objects.create(
            name='Cirurgia Geral',
            abbreviation='CIRGER'
        )
        self.specialty2 = MedicalSpecialty.objects.create(
            name='Cirurgia Vascular',
            abbreviation='CIRVASC'
        )

    def test_profile_current_specialty_can_be_null(self):
        """Test that current_specialty field can be null (blank=True)."""
        profile = self.user.profile
        self.assertIsNone(profile.current_specialty)

    def test_set_current_specialty(self):
        """
        Test setting current specialty.

        **WHEN** a user updates their profile and selects a specialty from
        their assigned list
        **THEN** the user's profile.current_specialty is set to the selected
        specialty
        """
        profile = self.user.profile
        profile.current_specialty = self.specialty1
        profile.save()

        profile.refresh_from_db()
        self.assertEqual(profile.current_specialty, self.specialty1)

    def test_change_current_specialty(self):
        """Test changing current specialty."""
        profile = self.user.profile
        profile.current_specialty = self.specialty1
        profile.save()

        # Change to another specialty
        profile.current_specialty = self.specialty2
        profile.save()

        profile.refresh_from_db()
        self.assertEqual(profile.current_specialty, self.specialty2)

    def test_clear_current_specialty(self):
        """Test clearing current specialty (set to None)."""
        profile = self.user.profile
        profile.current_specialty = self.specialty1
        profile.save()

        # Clear it
        profile.current_specialty = None
        profile.save()

        profile.refresh_from_db()
        self.assertIsNone(profile.current_specialty)

    def test_current_specialty_set_null_on_specialty_delete(self):
        """
        Test SET_NULL constraint when deleting a specialty.

        **WHEN** a MedicalSpecialty that is set as current_specialty is deleted
        **THEN** the profile's current_specialty is set to NULL (SET_NULL behavior)
        """
        profile = self.user.profile
        profile.current_specialty = self.specialty1
        profile.save()

        # Delete the specialty
        self.specialty1.delete()

        # Refresh profile from database
        profile.refresh_from_db()

        # current_specialty should be NULL now
        self.assertIsNone(profile.current_specialty)

    def test_current_specialty_protect_on_specialty_delete_with_userspecialty(self):
        """
        Test PROTECT constraint when deleting a specialty with UserSpecialty.

        **WHEN** an administrator attempts to delete a MedicalSpecialty that
        has users assigned via UserSpecialty
        **THEN** the system prevents deletion due to PROTECT constraint on
        UserSpecialty.specialty
        """
        # Create a UserSpecialty assignment
        UserSpecialty.objects.create(
            user=self.user,
            specialty=self.specialty1
        )

        # Try to delete the specialty - should fail due to PROTECT on UserSpecialty
        with self.assertRaises(IntegrityError):
            self.specialty1.delete()

        # Specialty should still exist
        self.assertTrue(
            MedicalSpecialty.objects.filter(id=self.specialty1.id).exists()
        )

    def test_multiple_users_can_have_same_current_specialty(self):
        """Test that multiple users can have the same current specialty."""
        user2 = DoctorFactory()

        self.user.profile.current_specialty = self.specialty1
        self.user.profile.save()

        user2.profile.current_specialty = self.specialty1
        user2.profile.save()

        self.assertEqual(self.user.profile.current_specialty, self.specialty1)
        self.assertEqual(user2.profile.current_specialty, self.specialty1)
