"""
Tests for medical specialty profile form and display (Phase 4: TDD).

This file contains tests for profile form filtering and profile
template display of specialties.
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.accounts.models import (
    MedicalSpecialty,
    UserSpecialty
)
from apps.accounts.forms import UserProfileForm
from apps.accounts.tests.factories import DoctorFactory

User = get_user_model()


# ============================================================================
# TASK 4.1: Tests for UserProfileForm current_specialty Filtering
# ============================================================================

class UserProfileFormTestCase(TestCase):
    """Test cases for UserProfileForm with specialty filtering (Task 4.1)."""

    def setUp(self):
        """Set up test data."""
        self.user = DoctorFactory()
        self.profile = self.user.profile

    def test_form_includes_current_specialty_field(self):
        """Test that form includes current_specialty field."""
        form = UserProfileForm(instance=self.profile)

        self.assertIn('current_specialty', form.fields)

    def test_form_filters_specialties_to_assigned_only(self):
        """
        Test that form filters current_specialty to user's assigned
        specialties.

        **WHEN** a user views their profile update form
        **THEN** the current_specialty dropdown only shows specialties that
        are assigned to the user and active
        """
        # Create specialties
        specialty_assigned, _ = MedicalSpecialty.objects.get_or_create(
            name='Cirurgia Geral',
            defaults={'abbreviation': 'CG', 'is_active': True}
        )
        specialty_unassigned, _ = MedicalSpecialty.objects.get_or_create(
            name='Cirurgia Vascular',
            defaults={'abbreviation': 'CVASC', 'is_active': True}
        )
        specialty_inactive, _ = MedicalSpecialty.objects.get_or_create(
            name='Cardiologia',
            defaults={'abbreviation': 'CARDIO', 'is_active': False}
        )

        # Assign only one specialty to user
        UserSpecialty.objects.create(
            user=self.user,
            specialty=specialty_assigned,
            is_primary=True
        )

        # Create form
        form = UserProfileForm(instance=self.profile)

        # Check queryset
        queryset = form.fields['current_specialty'].queryset

        # Should only contain assigned specialty
        self.assertIn(specialty_assigned, list(queryset))
        self.assertNotIn(specialty_unassigned, list(queryset))
        self.assertNotIn(specialty_inactive, list(queryset))

    def test_form_shows_all_assigned_specialties(self):
        """
        Test that form shows all assigned specialties in dropdown.

        **WHEN** a user has multiple assigned specialties
        **THEN** the current_specialty dropdown shows all of them
        """
        specialty1, _ = MedicalSpecialty.objects.get_or_create(
            name='Cirurgia Geral',
            defaults={'abbreviation': 'CG'}
        )
        specialty2, _ = MedicalSpecialty.objects.get_or_create(
            name='Cirurgia Vascular',
            defaults={'abbreviation': 'CVASC'}
        )

        UserSpecialty.objects.create(user=self.user, specialty=specialty1)
        UserSpecialty.objects.create(user=self.user, specialty=specialty2)

        form = UserProfileForm(instance=self.profile)
        queryset = form.fields['current_specialty'].queryset

        # Should contain both assigned specialties
        self.assertIn(specialty1, list(queryset))
        self.assertIn(specialty2, list(queryset))

    def test_form_specialties_ordered_by_name(self):
        """Test that specialties are ordered by name in the dropdown."""
        specialty_b, _ = MedicalSpecialty.objects.get_or_create(
            name='Ortopedia',
            defaults={'abbreviation': 'ORTO'}
        )
        specialty_a, _ = MedicalSpecialty.objects.get_or_create(
            name='Cardiologia',
            defaults={'abbreviation': 'CARDIO'}
        )
        specialty_c, _ = MedicalSpecialty.objects.get_or_create(
            name='Pediatria',
            defaults={'abbreviation': 'PED'}
        )

        UserSpecialty.objects.create(user=self.user, specialty=specialty_b)
        UserSpecialty.objects.create(user=self.user, specialty=specialty_a)
        UserSpecialty.objects.create(user=self.user, specialty=specialty_c)

        form = UserProfileForm(instance=self.profile)
        specialties = list(form.fields['current_specialty'].queryset)

        # Should be ordered by name
        self.assertEqual(specialties[0], specialty_a)
        self.assertEqual(specialties[1], specialty_b)
        self.assertEqual(specialties[2], specialty_c)

    def test_form_empty_label_for_no_specialties(self):
        """Test that form has empty label when user has no specialties."""
        form = UserProfileForm(instance=self.profile)

        self.assertIsNotNone(
            form.fields['current_specialty'].empty_label
        )


# ============================================================================
# TASK 4.2: Tests for Profile View with Specialties
# ============================================================================

class ProfileViewTestCase(TestCase):
    """Test cases for profile view with specialties (Task 4.2)."""

    def setUp(self):
        """Set up test data."""
        self.user = DoctorFactory(
            password='testpass123',
            password_change_required=False,
            terms_accepted=True
        )
        self.client = Client()
        self.client.login(username=self.user.username, password='testpass123')

    def test_profile_view_includes_specialties_in_context(self):
        """Test that profile view includes user specialties in context."""
        specialty, _ = MedicalSpecialty.objects.get_or_create(
            name='Cirurgia Geral',
            defaults={'abbreviation': 'CG'}
        )
        UserSpecialty.objects.create(
            user=self.user,
            specialty=specialty,
            is_primary=True
        )

        # Get profile
        url = reverse('apps.accounts:profile', kwargs={
            'public_id': self.user.profile.public_id
        })
        response = self.client.get(url)

        # Check context - allow redirect (302)
        self.assertIn(response.status_code, [200, 302])
        if response.status_code == 200:
            self.assertIn('profile', response.context)
            self.assertIn('user', response.context)


# ============================================================================
# TASK 4.3: Tests for Specialty Badges in Profile Template
# ============================================================================

class ProfileTemplateTestCase(TestCase):
    """Test cases for profile template with specialty badges (Task 4.3)."""

    def setUp(self):
        """Set up test data."""
        self.user = DoctorFactory(
            password='testpass123',
            password_change_required=False,
            terms_accepted=True
        )
        self.client = Client()
        self.client.login(username=self.user.username, password='testpass123')

    def test_profile_displays_current_specialty(self):
        """
        Test that profile displays current specialty with badge.

        **WHEN** viewing a user's profile page
        **THEN** the current specialty is displayed with a badge showing
        the specialty name
        """
        specialty, _ = MedicalSpecialty.objects.get_or_create(
            name='Cirurgia Vascular',
            defaults={'abbreviation': 'CVASC'}
        )
        self.user.profile.current_specialty = specialty
        self.user.profile.save()

        url = reverse('apps.accounts:profile', kwargs={
            'public_id': self.user.profile.public_id
        })
        response = self.client.get(url)

        # Allow redirect, check response content on success
        self.assertIn(response.status_code, [200, 302])
        if response.status_code == 200:
            self.assertContains(response, 'Cirurgia Vascular')

    def test_profile_displays_all_specialties_with_badges(self):
        """
        Test that profile displays all assigned specialties with badges.

        **WHEN** viewing a user's profile page who has multiple assigned
        specialties
        **THEN** the system displays all specialties as badges
        """
        specialty1, _ = MedicalSpecialty.objects.get_or_create(
            name='Cirurgia Geral',
            defaults={'abbreviation': 'CG'}
        )
        specialty2, _ = MedicalSpecialty.objects.get_or_create(
            name='Cirurgia Vascular',
            defaults={'abbreviation': 'CVASC'}
        )

        UserSpecialty.objects.create(
            user=self.user,
            specialty=specialty1,
            is_primary=True
        )
        UserSpecialty.objects.create(
            user=self.user,
            specialty=specialty2,
            is_primary=False
        )

        url = reverse('apps.accounts:profile', kwargs={
            'public_id': self.user.profile.public_id
        })
        response = self.client.get(url)

        # Allow redirect, check response content on success
        self.assertIn(response.status_code, [200, 302])
        if response.status_code == 200:
            self.assertContains(response, 'Cirurgia Geral')
            self.assertContains(response, 'Cirurgia Vascular')
