"""
Tests for patient detail page links.
"""

from datetime import date

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from apps.accounts.models import EqmdCustomUser
from apps.patients.models import Patient


class PatientDetailLinksTests(TestCase):
    """Tests for links on the patient detail page."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        # Create test user
        cls.user = EqmdCustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword',
            password_change_required=False,
            terms_accepted=True,
        )

        # Add view_patient permission
        content_type = ContentType.objects.get_for_model(Patient)
        view_permission = Permission.objects.get(
            content_type=content_type,
            codename='view_patient'
        )
        cls.user.user_permissions.add(view_permission)

        # Create test patient
        cls.patient = Patient.objects.create(
            name='Test Patient',
            birthday=date(1980, 1, 1),
            status=Patient.Status.OUTPATIENT,
            created_by=cls.user,
            updated_by=cls.user,
        )

    def setUp(self):
        """Log in the test user."""
        self.client.login(username='testuser', password='testpassword')

    def test_patient_detail_contains_report_create_link_for_authorized_user(self):
        """Test that patient detail page contains report create link for authenticated user."""
        response = self.client.get(
            reverse('patients:patient_detail', kwargs={'pk': self.patient.pk})
        )
        self.assertEqual(response.status_code, 200)

        # Check that the report create link is present
        report_create_url = reverse('reports:report_create', kwargs={'patient_id': self.patient.pk})
        self.assertContains(response, report_create_url)

    def test_patient_detail_report_create_link_requires_authentication(self):
        """Test that report create link is not shown to unauthenticated users."""
        # Logout the user
        self.client.logout()

        response = self.client.get(
            reverse('patients:patient_detail', kwargs={'pk': self.patient.pk})
        )

        # The page should redirect or not contain the link
        # Typically unauthenticated users are redirected to login
        # If they can access the page, the link should not be present
        if response.status_code == 200:
            report_create_url = reverse('reports:report_create', kwargs={'patient_id': self.patient.pk})
            self.assertNotContains(response, report_create_url)
