"""
Tests verifying that the simple note detail page uses the shared patient
context component and keeps page-specific metadata and actions intact.
"""

from datetime import date

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from apps.accounts.models import EqmdCustomUser
from apps.patients.models import Patient
from apps.simplenotes.models import SimpleNote


class SimpleNoteDetailContextUITests(TestCase):
    """UI-level tests for the shared patient context on simplenote detail."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.user = EqmdCustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword',
            password_change_required=False,
            terms_accepted=True,
        )

        # Grant view_event (required by the detail view)
        from apps.events.models import Event
        event_ct = ContentType.objects.get_for_model(Event)
        cls.user.user_permissions.add(
            Permission.objects.get(content_type=event_ct, codename='view_event'),
        )

        # Grant view_patient
        patient_ct = ContentType.objects.get_for_model(Patient)
        cls.user.user_permissions.add(
            Permission.objects.get(content_type=patient_ct, codename='view_patient'),
        )

        cls.patient = Patient.objects.create(
            name='João Souza',
            birthday=date(1990, 3, 10),
            current_record_number='99001',
            status=Patient.Status.OUTPATIENT,
            created_by=cls.user,
            updated_by=cls.user,
        )

        cls.simplenote = SimpleNote.objects.create(
            patient=cls.patient,
            event_datetime=timezone.now(),
            description='Nota de teste',
            content='Paciente em observação.',
            created_by=cls.user,
            updated_by=cls.user,
        )

    def setUp(self):
        self.client.login(username='testuser', password='testpassword')

    def _detail_url(self):
        return reverse(
            'apps.simplenotes:simplenote_detail',
            kwargs={'pk': self.simplenote.pk},
        )

    # ------------------------------------------------------------------
    # 1. Shared component is used instead of duplicated blocks
    # ------------------------------------------------------------------

    def test_simplenote_detail_uses_shared_patient_context_component(self):
        """The simple note detail page renders the shared patient context
        component (patient-context-summary) rather than a local copy."""
        response = self.client.get(self._detail_url())
        self.assertEqual(response.status_code, 200)

        content = response.content.decode()

        # The shared component's CSS class must be present
        self.assertIn('patient-context-summary', content)

        # Canonical compact fields rendered by the component should appear
        self.assertIn('João Souza', content)
        self.assertIn('99001', content)

    # ------------------------------------------------------------------
    # 2. Event actions and datetime remain visible
    # ------------------------------------------------------------------

    def test_simplenote_detail_keeps_event_actions_and_datetime_visible(self):
        """After adopting the shared component the page still shows the simple
        note event datetime and action buttons (print, back)."""
        response = self.client.get(self._detail_url())
        self.assertEqual(response.status_code, 200)

        content = response.content.decode()

        # Event datetime formatted in the breadcrumb or header
        expected_dt = self.simplenote.event_datetime.strftime('%d/%m/%Y')
        self.assertIn(expected_dt, content)

        # Print action
        print_url = reverse(
            'apps.simplenotes:simplenote_print',
            kwargs={'pk': self.simplenote.pk},
        )
        self.assertIn(print_url, content)

        # Back-to-timeline link
        timeline_url = reverse(
            'apps.patients:patient_events_timeline',
            kwargs={'patient_id': self.patient.pk},
        )
        self.assertIn(timeline_url, content)
