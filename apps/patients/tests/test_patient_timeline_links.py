"""
Tests for patient timeline page links.
"""

from datetime import date

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from apps.accounts.models import EqmdCustomUser
from apps.patients.models import Patient


class PatientTimelineLinksTests(TestCase):
    """Tests for links on the patient timeline page."""

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

        # Add add_event permission (required for the dropdown to show)
        from apps.events.models import Event
        event_content_type = ContentType.objects.get_for_model(Event)
        add_event_permission = Permission.objects.get(
            content_type=event_content_type,
            codename='add_event'
        )
        cls.user.user_permissions.add(add_event_permission)

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

    def test_patient_timeline_dropdown_includes_report_link(self):
        """Test that patient timeline page includes report create link in the dropdown."""
        response = self.client.get(
            reverse('apps.patients:patient_events_timeline', kwargs={'patient_id': self.patient.pk})
        )
        self.assertEqual(response.status_code, 200)

        # Check that the report create link is present in the timeline dropdown
        report_create_url = reverse('reports:report_create', kwargs={'patient_id': self.patient.pk})
        self.assertContains(response, report_create_url)
        # Also check that the link is not disabled
        # The report link should have the correct icon and not be marked as disabled
        self.assertContains(response, 'bi-file-earmark-medical')
        # Check that there's no disabled report link
        self.assertNotRegex(response.content.decode(), r'disabled[^>]*>.*Relatório.*Em breve')
