"""
Tests for medical specialty properties on User and UserProfile models (Phase 2: TDD).

This file contains tests for the properties that provide access to medical
specialties on EqmdCustomUser and UserProfile models.
"""
import uuid
from django.test import TestCase
from apps.accounts.models import (
    MedicalSpecialty,
    UserSpecialty,
    UserProfile
)
from django.contrib.auth import get_user_model
from apps.accounts.tests.factories import (
    DoctorFactory,
    ResidentFactory
)

User = get_user_model()


# ============================================================================
# TASK 2.1: Tests for EqmdCustomUser.specialties Property
# ============================================================================

class EqmdCustomUserSpecialtiesPropertyTestCase(TestCase):
    """Test cases for EqmdCustomUser.specialties property (Task 2.1)."""

    def test_specialties_property_returns_list_of_specialties(self):
        """
        Test that specialties property returns a list of MedicalSpecialty objects.

        **WHEN** accessing user.specialties on a user with multiple active
        specialty assignments
        **THEN** the system returns a list of MedicalSpecialty objects for all
        assignments where specialty.is_active=True
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

        UserSpecialty.objects.create(user=user, specialty=specialty1)
        UserSpecialty.objects.create(user=user, specialty=specialty2)

        specialties = user.specialties

        self.assertIsInstance(specialties, list)
        self.assertEqual(len(specialties), 2)
        self.assertIn(specialty1, specialties)
        self.assertIn(specialty2, specialties)

    def test_specialties_property_filters_active_specialties(self):
        """Test that specialties property filters out inactive specialties."""
        user = DoctorFactory()
        specialty_active = MedicalSpecialty.objects.create(
            name='Cirurgia Geral',
            abbreviation='CIRGER',
            is_active=True
        )
        specialty_inactive = MedicalSpecialty.objects.create(
            name='Cirurgia Vascular',
            abbreviation='CIRVASC',
            is_active=False
        )

        UserSpecialty.objects.create(user=user, specialty=specialty_active)
        UserSpecialty.objects.create(user=user, specialty=specialty_inactive)

        specialties = user.specialties

        self.assertEqual(len(specialties), 1)
        self.assertIn(specialty_active, specialties)
        self.assertNotIn(specialty_inactive, specialties)

    def test_specialties_property_returns_empty_list_for_no_assignments(self):
        """
        Test that specialties property returns empty list for user without
        specialty assignments.

        **WHEN** accessing user.specialties on a user with no specialty
        assignments
        **THEN** the system returns an empty list
        """
        user = DoctorFactory()

        specialties = user.specialties

        self.assertIsInstance(specialties, list)
        self.assertEqual(len(specialties), 0)
        self.assertEqual(specialties, [])


# ============================================================================
# TASK 2.2: Tests for EqmdCustomUser.primary_specialty Property
# ============================================================================

class EqmdCustomUserPrimarySpecialtyPropertyTestCase(TestCase):
    """Test cases for EqmdCustomUser.primary_specialty property (Task 2.2)."""

    def test_primary_specialty_returns_marked_primary(self):
        """
        Test that primary_specialty property returns the specialty marked as
        primary.

        **WHEN** accessing user.primary_specialty on a user with one specialty
        marked as is_primary=True
        **THEN** the system returns that specialty object
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

        primary = user.primary_specialty

        self.assertEqual(primary, specialty2)

    def test_primary_specialty_falls_back_to_first_when_none_marked(self):
        """
        Test that primary_specialty returns first specialty when none is marked
        as primary.

        **WHEN** accessing user.primary_specialty on a user with specialties
        but none marked as primary
        **THEN** the system returns the first specialty in the ordered list
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

        UserSpecialty.objects.create(
            user=user,
            specialty=specialty1,
            is_primary=False
        )
        UserSpecialty.objects.create(
            user=user,
            specialty=specialty2,
            is_primary=False
        )

        primary = user.primary_specialty

        # First specialty by name ordering
        self.assertEqual(primary, specialty1)

    def test_primary_specialty_returns_none_for_no_assignments(self):
        """
        Test that primary_specialty returns None for user with no specialty
        assignments.

        **WHEN** accessing user.primary_specialty on a user with no specialty
        assignments
        **THEN** the system returns None
        """
        user = DoctorFactory()

        primary = user.primary_specialty

        self.assertIsNone(primary)


# ============================================================================
# TASK 2.3: Tests for EqmdCustomUser.specialty_display Property
# ============================================================================

class EqmdCustomUserSpecialtyDisplayPropertyTestCase(TestCase):
    """Test cases for EqmdCustomUser.specialty_display property (Task 2.3)."""

    def test_specialty_display_returns_primary_name(self):
        """
        Test that specialty_display returns the primary specialty name.

        **WHEN** accessing user.specialty_display on a user with a primary
        specialty
        **THEN** the system returns the specialty's name as a string
        """
        user = DoctorFactory()
        specialty = MedicalSpecialty.objects.create(
            name='Cirurgia Vascular',
            abbreviation='CIRVASC'
        )

        UserSpecialty.objects.create(
            user=user,
            specialty=specialty,
            is_primary=True
        )

        display = user.specialty_display

        self.assertEqual(display, 'Cirurgia Vascular')
        self.assertIsInstance(display, str)

    def test_specialty_display_returns_empty_string_for_no_specialty(self):
        """
        Test that specialty_display returns empty string for user without
        specialty.

        **WHEN** accessing user.specialty_display on a user with no specialty
        **THEN** the system returns an empty string
        """
        user = DoctorFactory()

        display = user.specialty_display

        self.assertEqual(display, '')


# ============================================================================
# TASK 2.4: Tests for UserProfile.current_specialty_display Property
# ============================================================================

class UserProfileCurrentSpecialtyDisplayPropertyTestCase(TestCase):
    """Test cases for UserProfile.current_specialty_display property (Task 2.4)."""

    def test_current_specialty_display_returns_current_name(self):
        """Test that current_specialty_display returns current specialty name."""
        user = DoctorFactory()
        specialty = MedicalSpecialty.objects.create(
            name='Cirurgia Vascular',
            abbreviation='CIRVASC'
        )

        user.profile.current_specialty = specialty
        user.profile.save()

        display = user.profile.current_specialty_display

        self.assertEqual(display, 'Cirurgia Vascular')

    def test_current_specialty_display_fallback_to_primary(self):
        """Test that current_specialty_display falls back to primary."""
        user = DoctorFactory()
        specialty = MedicalSpecialty.objects.create(
            name='Cirurgia Vascular',
            abbreviation='CIRVASC'
        )

        UserSpecialty.objects.create(
            user=user,
            specialty=specialty,
            is_primary=True
        )

        # current_specialty is None
        display = user.profile.current_specialty_display

        # Should fallback to primary specialty
        self.assertEqual(display, 'Cirurgia Vascular')

    def test_current_specialty_display_returns_empty_string_when_no_specialty(self):
        """Test that current_specialty_display returns empty string when no specialty."""
        user = DoctorFactory()

        # No specialties assigned
        display = user.profile.current_specialty_display

        self.assertEqual(display, '')

    def test_current_specialty_display_prefers_current_over_primary(self):
        """Test that current_specialty_display prefers current over primary."""
        user = DoctorFactory()
        specialty_primary = MedicalSpecialty.objects.create(
            name='Cirurgia Geral',
            abbreviation='CIRGER'
        )
        specialty_current = MedicalSpecialty.objects.create(
            name='Cirurgia Vascular',
            abbreviation='CIRVASC'
        )

        UserSpecialty.objects.create(
            user=user,
            specialty=specialty_primary,
            is_primary=True
        )
        user.profile.current_specialty = specialty_current
        user.profile.save()

        display = user.profile.current_specialty_display

        # Should return current, not primary
        self.assertEqual(display, 'Cirurgia Vascular')
        self.assertNotEqual(display, 'Cirurgia Geral')
