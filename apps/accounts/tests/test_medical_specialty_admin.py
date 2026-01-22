"""
Tests for medical specialty admin configuration (Phase 3: TDD).

This file contains tests for Django admin interface for managing
medical specialties and user specialty assignments.
"""
from django.test import TestCase
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from apps.accounts.models import (
    MedicalSpecialty,
    UserSpecialty
)
from apps.accounts.admin import (
    MedicalSpecialtyAdmin,
    UserSpecialtyInline
)
from apps.accounts.tests.factories import (
    DoctorFactory,
    StaffUserFactory
)

User = get_user_model()


# ============================================================================
# TASK 3.1: Tests for MedicalSpecialty CRUD Operations
# ============================================================================

class MedicalSpecialtyAdminTestCase(TestCase):
    """Test cases for MedicalSpecialtyAdmin (Task 3.1)."""

    def setUp(self):
        """Set up test data."""
        self.site = AdminSite()
        self.admin = MedicalSpecialtyAdmin(MedicalSpecialty, self.site)
        self.staff_user = StaffUserFactory()

    def test_list_displays_correct_fields(self):
        """Test that list_display shows correct fields."""
        specialty = MedicalSpecialty.objects.create(
            name='Cirurgia Vascular',
            abbreviation='CIRVASC'
        )

        result = self.admin.get_list_display(None)

        expected = ['name', 'abbreviation', 'is_active', 'created_at']
        self.assertEqual(list(result), expected)

    def test_list_filters_include_is_active(self):
        """Test that list_filters includes is_active field."""
        result = self.admin.get_list_filter(None)

        self.assertIn('is_active', result)

    def test_search_fields_include_name_and_abbreviation(self):
        """Test that search_fields include name and abbreviation."""
        result = self.admin.get_search_fields(None)

        self.assertIn('name', result)
        self.assertIn('abbreviation', result)

    def test_ordering_by_name(self):
        """Test that ordering is by name."""
        result = self.admin.get_ordering(None)

        self.assertEqual(result, ['name'])

    def test_fieldsets_structure(self):
        """Test that fieldsets are properly configured."""
        fieldsets = self.admin.get_fieldsets(None)

        # Should have two fieldsets
        self.assertEqual(len(fieldsets), 2)

        # First fieldset should have name and abbreviation
        self.assertIn('name', fieldsets[0][1]['fields'])
        self.assertIn('abbreviation', fieldsets[0][1]['fields'])

        # Second fieldset should have description and is_active
        self.assertIn('description', fieldsets[1][1]['fields'])
        self.assertIn('is_active', fieldsets[1][1]['fields'])


# ============================================================================
# TASK 3.2: Tests for UserSpecialtyInline in User Admin
# ============================================================================

class UserSpecialtyInlineTestCase(TestCase):
    """Test cases for UserSpecialtyInline (Task 3.2)."""

    def setUp(self):
        """Set up test data."""
        self.site = AdminSite()
        self.inline = UserSpecialtyInline(UserSpecialty, self.site)

    def test_inline_model_is_user_specialty(self):
        """Test that inline uses UserSpecialty model."""
        self.assertEqual(self.inline.model, UserSpecialty)

    def test_extra_is_zero(self):
        """Test that extra forms is set to 0."""
        self.assertEqual(self.inline.extra, 0)

    def test_readonly_fields_include_assigned_at(self):
        """Test that assigned_at is in readonly_fields."""
        readonly_fields = self.inline.get_readonly_fields(None)

        self.assertIn('assigned_at', readonly_fields)

    def test_inline_fields_include_correct_fields(self):
        """Test that inline includes correct fields."""
        fields = self.inline.get_fields(None)

        expected_fields = ['specialty', 'is_primary', 'assigned_at']
        self.assertEqual(sorted(fields), sorted(expected_fields))


# ============================================================================
# TASK 3.3: Tests for Specialty Assignment via User Admin
# ============================================================================

class SpecialtyAssignmentTestCase(TestCase):
    """Test cases for specialty assignment functionality (Task 3.3)."""

    def test_assign_specialty_to_user_via_inline(self):
        """
        Test assigning a specialty to a user through admin inline.

        **WHEN** an administrator assigns a specialty to a user via the
        user admin inline
        **THEN** a UserSpecialty record is created with the user and specialty
        """
        user = DoctorFactory()
        specialty = MedicalSpecialty.objects.create(
            name='Cirurgia Geral',
            abbreviation='CIRGER'
        )

        # Simulate admin inline assignment
        UserSpecialty.objects.create(
            user=user,
            specialty=specialty,
            is_primary=True
        )

        # Verify assignment exists
        assignment = UserSpecialty.objects.get(user=user, specialty=specialty)
        self.assertIsNotNone(assignment)
        self.assertTrue(assignment.is_primary)

    def test_assign_multiple_specialties_to_user(self):
        """Test that multiple specialties can be assigned to a user."""
        user = DoctorFactory()
        specialty1 = MedicalSpecialty.objects.create(
            name='Cirurgia Geral',
            abbreviation='CIRGER'
        )
        specialty2 = MedicalSpecialty.objects.create(
            name='Cirurgia Vascular',
            abbreviation='CIRVASC'
        )

        # Assign multiple specialties
        UserSpecialty.objects.create(user=user, specialty=specialty1)
        UserSpecialty.objects.create(user=user, specialty=specialty2)

        # Verify both assignments exist
        self.assertEqual(user.user_specialties.count(), 2)
        self.assertTrue(
            user.user_specialties.filter(specialty=specialty1).exists()
        )
        self.assertTrue(
            user.user_specialties.filter(specialty=specialty2).exists()
        )

    def test_remove_specialty_from_user(self):
        """Test that a specialty can be removed from a user."""
        user = DoctorFactory()
        specialty = MedicalSpecialty.objects.create(
            name='Cirurgia Geral',
            abbreviation='CIRGER'
        )

        # Create assignment
        assignment = UserSpecialty.objects.create(user=user, specialty=specialty)

        # Remove assignment
        assignment.delete()

        # Verify it's gone
        self.assertFalse(
            UserSpecialty.objects.filter(user=user, specialty=specialty).exists()
        )

    def test_mark_primary_specialty(self):
        """
        Test marking a specialty as primary.

        **WHEN** an administrator marks is_primary=True on a user's specialty
        assignment
        **THEN** the specialty is marked as the user's primary specialty
        """
        user = DoctorFactory()
        specialty1 = MedicalSpecialty.objects.create(
            name='Cirurgia Geral',
            abbreviation='CIRGER'
        )
        specialty2 = MedicalSpecialty.objects.create(
            name='Cirurgia Vascular',
            abbreviation='CIRVASC'
        )

        # Create assignments
        UserSpecialty.objects.create(
            user=user,
            specialty=specialty1,
            is_primary=False
        )
        UserSpecialty.objects.create(
            user=user,
            specialty=specialty2,
            is_primary=True
        )

        # Verify primary is correctly set
        primary = user.user_specialties.get(is_primary=True)
        self.assertEqual(primary.specialty, specialty2)

    def test_admin_can_create_specialty(self):
        """
        Test that admin can create medical specialty.

        **WHEN** an administrator creates a medical specialty with name,
        abbreviation, and optional description
        **THEN** the specialty is saved in the database with is_active=True
        and generated timestamps
        """
        specialty = MedicalSpecialty.objects.create(
            name='Cardiologia',
            abbreviation='CARDIO',
            description='Especialidade médica focada no coração'
        )

        # Verify specialty was created
        retrieved = MedicalSpecialty.objects.get(abbreviation='CARDIO')
        self.assertEqual(retrieved.name, 'Cardiologia')
        self.assertEqual(retrieved.description, 'Especialidade médica focada no coração')
        self.assertTrue(retrieved.is_active)
        self.assertIsNotNone(retrieved.created_at)
        self.assertIsNotNone(retrieved.updated_at)

    def test_admin_can_soft_delete_specialty(self):
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

        # Soft delete
        specialty.is_active = False
        specialty.save()

        # Refresh from database
        specialty.refresh_from_db()

        # Verify it's inactive
        self.assertFalse(specialty.is_active)

        # Verify it still exists
        self.assertTrue(
            MedicalSpecialty.objects.filter(id=specialty.id).exists()
        )
