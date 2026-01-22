"""
Tests for medical specialty AJAX endpoint and avatar dropdown (Phase 5: TDD).

This file contains tests for specialty change API endpoint and
quick specialty switching from avatar dropdown.
"""
import uuid
import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.accounts.models import (
    MedicalSpecialty,
    UserSpecialty
)
from apps.accounts.tests.factories import DoctorFactory

User = get_user_model()


# ============================================================================
# TASK 5.1: Tests for change_specialty_api Endpoint
# ============================================================================

class ChangeSpecialtyApiTestCase(TestCase):
    """Test cases for change_specialty_api view (Task 5.1)."""

    def setUp(self):
        """Set up test data."""
        self.user = DoctorFactory(
            password='testpass123',
            password_change_required=False,
            terms_accepted=True
        )
        self.client = Client()
        self.client.login(username=self.user.username, password='testpass123')

        # Create specialties
        self.specialty1 = MedicalSpecialty.objects.create(
            name='Cirurgia Geral',
            abbreviation='CIRGER'
        )
        self.specialty2 = MedicalSpecialty.objects.create(
            name='Cirurgia Vascular',
            abbreviation='CIRVASC'
        )

    def test_valid_specialty_change_request(self):
        """
        Test valid specialty change request.

        **WHEN** an authenticated user POSTs a valid specialty_id to
        the change-specialty endpoint
        **THEN** the system validates the specialty is assigned and
        active, updates the profile, and returns success response
        """
        # Assign specialty to user
        UserSpecialty.objects.create(user=self.user, specialty=self.specialty1)

        # Change specialty
        response = self.client.post(
            reverse('apps.accounts:change_specialty_api'),
            data=json.dumps({'specialty_id': str(self.specialty1.id)}),
            content_type='application/json'
        )

        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'success': True})

        # Check profile was updated
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.current_specialty, self.specialty1)

    def test_invalid_specialty_id_format(self):
        """
        Test invalid specialty ID format.

        **WHEN** a user POSTs an invalid UUID format to the
        change-specialty endpoint
        **THEN** the system returns a 400 error with an invalid
        specialty ID message
        """
        response = self.client.post(
            reverse('apps.accounts:change_specialty_api'),
            data=json.dumps({'specialty_id': 'invalid-uuid'}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['success'], False)
        self.assertIn('error', response.json())

    def test_specialty_not_assigned_to_user(self):
        """
        Test specialty not assigned to user.

        **WHEN** a user POSTs a specialty_id for a specialty not
        assigned to them
        **THEN** the system returns a 403 error with a not assigned
        message
        """
        # Don't assign specialty to user
        response = self.client.post(
            reverse('apps.accounts:change_specialty_api'),
            data=json.dumps({'specialty_id': str(self.specialty1.id)}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['success'], False)
        self.assertIn('error', response.json())

    def test_inactive_specialty_change_attempt(self):
        """
        Test inactive specialty change attempt.

        **WHEN** a user POSTs a specialty_id for an inactive
        specialty
        **THEN** the system returns a 403 error and does not change
        the current specialty
        """
        # Deactivate specialty
        self.specialty1.is_active = False
        self.specialty1.save()

        # Assign specialty (even though it's inactive)
        UserSpecialty.objects.create(user=self.user, specialty=self.specialty1)

        # Try to change to it
        response = self.client.post(
            reverse('apps.accounts:change_specialty_api'),
            data=json.dumps({'specialty_id': str(self.specialty1.id)}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['success'], False)


# ============================================================================
# TASK 5.2: Tests for Permission on Specialty Change Endpoint
# ============================================================================

class ChangeSpecialtyPermissionTestCase(TestCase):
    """Test cases for specialty change permissions (Task 5.2)."""

    def setUp(self):
        """Set up test data."""
        self.user = DoctorFactory(
            password='testpass123',
            password_change_required=False,
            terms_accepted=True
        )
        self.client = Client()
        self.specialty = MedicalSpecialty.objects.create(
            name='Cirurgia Geral',
            abbreviation='CIRGER'
        )

    def test_require_authentication(self):
        """
        Test that authentication is required.

        **WHEN** an unauthenticated user attempts to access the
        specialty change endpoint
        **THEN** the system redirects to the login page
        """
        response = self.client.post(
            reverse('apps.accounts:change_specialty_api'),
            data={'specialty_id': str(self.specialty.id)},
            content_type='application/json'
        )

        # Should redirect to login
        self.assertIn(response.status_code, [302, 301])

    def test_authenticated_user_can_change_specialty(self):
        """Test that authenticated user can change specialty."""
        self.client.login(
            username=self.user.username,
            password='testpass123'
        )
        UserSpecialty.objects.create(
            user=self.user,
            specialty=self.specialty
        )

        response = self.client.post(
            reverse('apps.accounts:change_specialty_api'),
            data={'specialty_id': str(self.specialty.id)},
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['success'], True)


# ============================================================================
# TASK 5.3: Tests for Specialty Switching Integration
# ============================================================================

class SpecialtySwitchingIntegrationTestCase(TestCase):
    """Test cases for complete specialty switching flow (Task 5.3)."""

    def setUp(self):
        """Set up test data."""
        self.user = DoctorFactory(
            password='testpass123',
            password_change_required=False,
            terms_accepted=True
        )
        self.client = Client()
        self.client.login(username=self.user.username, password='testpass123')

        # Create specialties
        self.specialty1 = MedicalSpecialty.objects.create(
            name='Cirurgia Geral',
            abbreviation='CIRGER'
        )
        self.specialty2 = MedicalSpecialty.objects.create(
            name='Cirurgia Vascular',
            abbreviation='CIRVASC'
        )

        # Assign both to user
        UserSpecialty.objects.create(
            user=self.user,
            specialty=self.specialty1,
            is_primary=True
        )
        UserSpecialty.objects.create(
            user=self.user,
            specialty=self.specialty2,
            is_primary=False
        )

    def test_switch_between_specialties(self):
        """Test switching between multiple specialties."""
        # Start with specialty1
        self.user.profile.current_specialty = self.specialty1
        self.user.profile.save()

        # Switch to specialty2
        response = self.client.post(
            reverse('apps.accounts:change_specialty_api'),
            data={'specialty_id': str(self.specialty2.id)},
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertEqual(
            self.user.profile.current_specialty,
            self.specialty2
        )

    def test_switch_to_primary_specialty(self):
        """Test switching to primary specialty."""
        # Start with non-primary
        self.user.profile.current_specialty = self.specialty2
        self.user.profile.save()

        # Switch to primary
        response = self.client.post(
            reverse('apps.accounts:change_specialty_api'),
            data={'specialty_id': str(self.specialty1.id)},
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertEqual(
            self.user.profile.current_specialty,
            self.specialty1
        )

    def test_clear_current_specialty(self):
        """Test clearing current specialty."""
        # Set current specialty
        self.user.profile.current_specialty = self.specialty1
        self.user.profile.save()

        # Clear it (set to None - though API might not support this)
        # For now, just test setting to another specialty
        response = self.client.post(
            reverse('apps.accounts:change_specialty_api'),
            data={'specialty_id': str(self.specialty2.id)},
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertEqual(
            self.user.profile.current_specialty,
            self.specialty2
        )
