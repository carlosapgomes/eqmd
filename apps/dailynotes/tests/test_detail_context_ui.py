"""
Tests verifying that the daily note detail page uses the shared patient
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
from apps.dailynotes.models import DailyNote


class DailyNoteDetailContextUITests(TestCase):
    """UI-level tests for the shared patient context on dailynote detail."""

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

        # Grant view_patient
        patient_ct = ContentType.objects.get_for_model(Patient)
        cls.user.user_permissions.add(
            Permission.objects.get(content_type=patient_ct, codename='view_patient'),
        )

        # Grant view_event (required by the detail view)
        from apps.events.models import Event
        event_ct = ContentType.objects.get_for_model(Event)
        cls.user.user_permissions.add(
            Permission.objects.get(content_type=event_ct, codename='view_event'),
        )

        cls.patient = Patient.objects.create(
            name='Maria da Silva',
            birthday=date(1985, 6, 15),
            current_record_number='12345',
            status=Patient.Status.OUTPATIENT,
            created_by=cls.user,
            updated_by=cls.user,
        )

        cls.dailynote = DailyNote.objects.create(
            patient=cls.patient,
            event_datetime=timezone.now(),
            description='Evolução de teste',
            content='Paciente estável.',
            created_by=cls.user,
            updated_by=cls.user,
        )

    def setUp(self):
        self.client.login(username='testuser', password='testpassword')

    def _detail_url(self):
        return reverse('dailynotes:dailynote_detail', kwargs={'pk': self.dailynote.pk})

    # ------------------------------------------------------------------
    # 1. Shared component is used instead of duplicated blocks
    # ------------------------------------------------------------------

    def test_dailynote_detail_uses_shared_patient_context_component(self):
        """The daily note detail page renders the shared patient context
        component (patient-context-summary) rather than a local copy."""
        response = self.client.get(self._detail_url())
        self.assertEqual(response.status_code, 200)

        content = response.content.decode()

        # The shared component's CSS class must be present
        self.assertIn('patient-context-summary', content)

        # Canonical compact fields rendered by the component should appear
        self.assertIn('Maria da Silva', content)
        self.assertIn('12345', content)

    # ------------------------------------------------------------------
    # 2. Event actions and datetime remain visible
    # ------------------------------------------------------------------

    def test_dailynote_detail_keeps_event_actions_and_datetime_visible(self):
        """After adopting the shared component the page still shows the daily
        note event datetime and action buttons (PDF, copy, edit, back)."""
        response = self.client.get(self._detail_url())
        self.assertEqual(response.status_code, 200)

        content = response.content.decode()

        # Event datetime formatted in the breadcrumb or header
        expected_dt = self.dailynote.event_datetime.strftime('%d/%m/%Y')
        self.assertIn(expected_dt, content)

        # PDF action is present
        pdf_url = reverse('dailynotes:dailynote_pdf', kwargs={'pk': self.dailynote.pk})
        self.assertIn(pdf_url, content)

        # Back-to-timeline link
        timeline_url = reverse(
            'apps.patients:patient_events_timeline',
            kwargs={'patient_id': self.patient.pk},
        )
        self.assertIn(timeline_url, content)

    def test_dailynote_detail_has_no_legacy_print_action(self):
        """The detail page must not contain any link to the legacy print endpoint."""
        response = self.client.get(self._detail_url())
        self.assertEqual(response.status_code, 200)
        # Check the actual resolved print URL is absent
        print_url = reverse('dailynotes:dailynote_print', kwargs={'pk': self.dailynote.pk})
        self.assertNotContains(response, print_url)

    # ------------------------------------------------------------------
    # 3. Desktop layout no longer uses sidebar structure
    # ------------------------------------------------------------------

    def test_dailynote_detail_desktop_no_longer_uses_sidebar_layout(self):
        """The daily note detail page must not use the old desktop sidebar
        layout classes (desktop-layout, patient-sidebar, content-main)."""
        response = self.client.get(self._detail_url())
        self.assertEqual(response.status_code, 200)

        content = response.content.decode()

        # The old desktop sidebar layout classes must be absent
        self.assertNotIn('desktop-layout', content)
        self.assertNotIn('patient-sidebar', content)
        self.assertNotIn('content-main', content)

    # ------------------------------------------------------------------
    # 4. Shared context + metadata + actions still visible
    # ------------------------------------------------------------------

    def test_dailynote_detail_keeps_shared_context_metadata_and_actions_visible(self):
        """After removing the sidebar layout the page still renders the shared
        patient context, daily note metadata, and action buttons on desktop."""
        response = self.client.get(self._detail_url())
        self.assertEqual(response.status_code, 200)

        content = response.content.decode()

        # Shared patient context component is present
        self.assertIn('patient-context-summary', content)
        self.assertIn('Maria da Silva', content)

        # Event datetime visible
        expected_dt = self.dailynote.event_datetime.strftime('%d/%m/%Y')
        self.assertIn(expected_dt, content)

        # Page-specific metadata: description
        self.assertIn('Evolução de teste', content)

        # Created-by info is visible
        self.assertIn('testuser', content)

        # PDF action visible (print removed)
        pdf_url = reverse('dailynotes:dailynote_pdf', kwargs={'pk': self.dailynote.pk})
        self.assertIn(pdf_url, content)

        # Legacy print action must NOT be present
        print_url = reverse('dailynotes:dailynote_print', kwargs={'pk': self.dailynote.pk})
        self.assertNotIn(print_url, content)
