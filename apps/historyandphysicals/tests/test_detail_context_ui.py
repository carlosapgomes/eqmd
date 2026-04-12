"""
Tests verifying that the history and physical detail page uses the shared
patient context component and keeps page-specific metadata and actions intact.
"""

from datetime import date

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from apps.accounts.models import EqmdCustomUser
from apps.patients.models import Patient
from apps.historyandphysicals.models import HistoryAndPhysical


class HistoryAndPhysicalDetailContextUITests(TestCase):
    """UI-level tests for the shared patient context on H&P detail."""

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
            name='Carlos Lima',
            birthday=date(1978, 11, 5),
            current_record_number='77889',
            status=Patient.Status.OUTPATIENT,
            created_by=cls.user,
            updated_by=cls.user,
        )

        cls.historyandphysical = HistoryAndPhysical.objects.create(
            patient=cls.patient,
            event_datetime=timezone.now(),
            description='Anamnese de teste',
            content='Paciente refere dor abdominal.',
            created_by=cls.user,
            updated_by=cls.user,
        )

    def setUp(self):
        self.client.login(username='testuser', password='testpassword')

    def _detail_url(self):
        return reverse(
            'apps.historyandphysicals:historyandphysical_detail',
            kwargs={'pk': self.historyandphysical.pk},
        )

    # ------------------------------------------------------------------
    # 1. Shared component is used instead of duplicated blocks
    # ------------------------------------------------------------------

    def test_historyandphysical_detail_uses_shared_patient_context_component(self):
        """The H&P detail page renders the shared patient context
        component (patient-context-summary) rather than a local copy."""
        response = self.client.get(self._detail_url())
        self.assertEqual(response.status_code, 200)

        content = response.content.decode()

        # The shared component's CSS class must be present
        self.assertIn('patient-context-summary', content)

        # Canonical compact fields rendered by the component should appear
        self.assertIn('Carlos Lima', content)
        self.assertIn('77889', content)

    # ------------------------------------------------------------------
    # 2. Event actions and datetime remain visible
    # ------------------------------------------------------------------

    def test_historyandphysical_detail_keeps_event_actions_and_datetime_visible(self):
        """After adopting the shared component the page still shows the H&P
        event datetime and action buttons (print, back)."""
        response = self.client.get(self._detail_url())
        self.assertEqual(response.status_code, 200)

        content = response.content.decode()

        # Event datetime formatted in the breadcrumb or header
        expected_dt = self.historyandphysical.event_datetime.strftime('%d/%m/%Y')
        self.assertIn(expected_dt, content)

        # Print action
        print_url = reverse(
            'apps.historyandphysicals:historyandphysical_print',
            kwargs={'pk': self.historyandphysical.pk},
        )
        self.assertIn(print_url, content)

        # Back-to-timeline link
        timeline_url = reverse(
            'apps.patients:patient_events_timeline',
            kwargs={'patient_id': self.patient.pk},
        )
        self.assertIn(timeline_url, content)

    # ------------------------------------------------------------------
    # 3. Desktop layout no longer uses sidebar structure
    # ------------------------------------------------------------------

    def test_historyandphysical_detail_desktop_no_longer_uses_sidebar_layout(self):
        """The H&P detail page must not use the old desktop sidebar layout
        classes (desktop-layout, patient-sidebar, content-main)."""
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

    def test_historyandphysical_detail_keeps_shared_context_metadata_and_actions_visible(self):
        """After removing the sidebar layout the page still renders the shared
        patient context, H&P metadata, and action buttons on desktop."""
        response = self.client.get(self._detail_url())
        self.assertEqual(response.status_code, 200)

        content = response.content.decode()

        # Shared patient context component is present
        self.assertIn('patient-context-summary', content)
        self.assertIn('Carlos Lima', content)

        # Event datetime visible
        expected_dt = self.historyandphysical.event_datetime.strftime('%d/%m/%Y')
        self.assertIn(expected_dt, content)

        # Page-specific metadata: description
        self.assertIn('Anamnese de teste', content)

        # Created-by info is visible
        self.assertIn('testuser', content)

        # Print action visible
        print_url = reverse(
            'apps.historyandphysicals:historyandphysical_print',
            kwargs={'pk': self.historyandphysical.pk},
        )
        self.assertIn(print_url, content)
