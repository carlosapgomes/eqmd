"""
Tests for report duplicate view.

Covers the duplication contract: pre-filled form from the source report,
independent copy creation, template provenance not copied, permission
gating, and source immutability.
"""
from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import EqmdCustomUser
from apps.events.models import Event
from apps.patients.models import Patient
from apps.reports.forms import ReportDuplicateForm
from apps.reports.models import Report, ReportTemplate


class ReportDuplicateViewTests(TestCase):
    """Tests for the report duplicate view."""

    def setUp(self):
        """Set up users, patient, template, and source report."""
        self.doctor = EqmdCustomUser.objects.create_user(
            username='doctor',
            email='doctor@test.com',
            password='testpass123',
            profession_type=EqmdCustomUser.MEDICAL_DOCTOR,
            password_change_required=False,
            terms_accepted=True,
        )
        self.nurse = EqmdCustomUser.objects.create_user(
            username='nurse',
            email='nurse@test.com',
            password='testpass123',
            profession_type=EqmdCustomUser.NURSE,
            password_change_required=False,
            terms_accepted=True,
        )

        event_content_type = ContentType.objects.get_for_model(Event)
        add_event_permission = Permission.objects.get(
            content_type=event_content_type,
            codename='add_event',
        )
        self.doctor.user_permissions.add(add_event_permission)

        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            created_by=self.doctor,
            updated_by=self.doctor,
            current_record_number='REC12345',
        )

        self.template = ReportTemplate.objects.create(
            name='Source Template',
            markdown_body='Template for {{patient_name}}',
            is_public=True,
            created_by=self.doctor,
            updated_by=self.doctor,
        )

        self.source_report = Report.objects.create(
            patient=self.patient,
            created_by=self.doctor,
            updated_by=self.doctor,
            title='Source Report',
            content='# Source content\n\nBody of the source report.',
            document_date=date(2024, 1, 15),
            event_datetime=timezone.now() - timedelta(hours=30),
            template=self.template,
        )
        self.source_event_datetime = self.source_report.event_datetime

    def _duplicate_url(self, pk=None):
        """Return the duplicate URL for the given report (source by default)."""
        return reverse(
            'reports:report_duplicate',
            kwargs={'pk': pk or self.source_report.pk},
        )

    def test_report_duplicate_route_exists(self):
        """The duplicate route reverses to the documented path."""
        self.assertEqual(
            self._duplicate_url(),
            f'/reports/{self.source_report.pk}/duplicate/',
        )

    def test_duplicate_get_prefills_form_from_source(self):
        """GET renders the create form pre-filled with the source title/content."""
        self.client.login(username='doctor', password='testpass123')

        response = self.client.get(self._duplicate_url())

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'reports/report_duplicate_form.html')

        form = response.context['form']
        self.assertIsInstance(form, ReportDuplicateForm)
        self.assertEqual(form.initial['title'], 'Source Report')
        self.assertEqual(form.initial['content'], self.source_report.content)
        self.assertEqual(
            form.fields['document_date'].initial,
            timezone.localdate().strftime('%m-%d-%Y'),
        )

        content = response.content.decode()
        self.assertIn('Source Report', content)
        self.assertIn('Body of the source report.', content)

    def test_duplicate_form_excludes_template_field(self):
        """The duplicate form offers no template selector."""
        self.client.login(username='doctor', password='testpass123')

        response = self.client.get(self._duplicate_url())

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('template', response.context['form'].fields)
        self.assertNotIn('id_template', response.content.decode())

    def test_duplicate_get_ignores_template_query_parameter(self):
        """?template= must not re-render content; initial comes from the source."""
        other_template = ReportTemplate.objects.create(
            name='Other Template',
            markdown_body='Other template body for {{patient_name}}',
            is_public=True,
            created_by=self.doctor,
            updated_by=self.doctor,
        )
        self.client.login(username='doctor', password='testpass123')

        response = self.client.get(
            self._duplicate_url(),
            {'template': str(other_template.pk)},
        )

        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertEqual(form.initial['content'], self.source_report.content)
        self.assertNotIn('template', form.fields)

    def test_duplicate_get_requires_add_event_permission(self):
        """Users without events.add_event are denied."""
        self.client.login(username='nurse', password='testpass123')

        response = self.client.get(self._duplicate_url())

        self.assertEqual(response.status_code, 403)

    def test_duplicate_get_denied_without_patient_access(self):
        """Users who cannot access the patient are denied."""
        self.client.login(username='doctor', password='testpass123')

        with patch(
            'apps.reports.views.report_views.can_access_patient',
            return_value=False,
        ):
            response = self.client.get(self._duplicate_url())

        self.assertEqual(response.status_code, 403)

    def test_duplicate_get_requires_login(self):
        """Anonymous requests are denied."""
        response = self.client.get(self._duplicate_url())

        self.assertEqual(response.status_code, 403)

    def test_duplicate_unknown_report_returns_404(self):
        """An unknown report pk yields 404."""
        self.client.login(username='doctor', password='testpass123')

        response = self.client.get(
            self._duplicate_url(pk='00000000-0000-0000-0000-000000000000')
        )

        self.assertEqual(response.status_code, 404)

    def test_duplicate_post_creates_independent_copy(self):
        """POST creates a new report attributed to the submitting user."""
        self.client.login(username='doctor', password='testpass123')

        response = self.client.post(
            self._duplicate_url(),
            {
                'title': 'Duplicated Report',
                'document_date': '02-20-2024',
                'content': 'Duplicated content body.',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse(
                'patients:patient_events_timeline',
                kwargs={'patient_id': self.patient.pk},
            ),
            fetch_redirect_response=False,
        )

        copy = Report.objects.get(title='Duplicated Report')
        self.assertEqual(copy.patient, self.patient)
        self.assertEqual(copy.created_by, self.doctor)
        self.assertEqual(copy.updated_by, self.doctor)
        self.assertEqual(copy.content, 'Duplicated content body.')
        self.assertEqual(copy.document_date, date(2024, 2, 20))
        self.assertIsNone(copy.template)
        self.assertEqual(copy.event_type, Event.REPORT_EVENT)
        self.assertTrue(copy.can_be_edited)

        success_messages = [str(message) for message in get_messages(response.wsgi_request)]
        self.assertTrue(
            any('criado com base no relat' in message for message in success_messages),
            success_messages,
        )

    def test_duplicate_post_accepts_source_content_without_template(self):
        """Submitting the pre-filled source content creates a template-free copy."""
        self.client.login(username='doctor', password='testpass123')

        response = self.client.post(
            self._duplicate_url(),
            {
                'title': self.source_report.title,
                'document_date': timezone.localdate().strftime('%m-%d-%Y'),
                'content': self.source_report.content,
            },
        )

        self.assertEqual(response.status_code, 302)
        copy = Report.objects.exclude(pk=self.source_report.pk).get()
        self.assertEqual(copy.patient, self.patient)
        self.assertEqual(copy.content, self.source_report.content)
        self.assertIsNone(copy.template)
        # Fresh 24h window anchored at the new event datetime.
        self.assertGreater(
            copy.event_datetime,
            self.source_report.event_datetime + timedelta(hours=24),
        )

    def test_duplicate_post_requires_add_event_permission(self):
        """Users without events.add_event cannot create a copy."""
        self.client.login(username='nurse', password='testpass123')

        response = self.client.post(
            self._duplicate_url(),
            {
                'title': 'Denied Report',
                'document_date': '02-20-2024',
                'content': 'Should not be saved.',
            },
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Report.objects.filter(title='Denied Report').exists())

    def test_duplicate_source_report_unchanged(self):
        """Neither GET nor POST modifies the source report."""
        self.client.login(username='doctor', password='testpass123')

        self.client.get(self._duplicate_url())
        self.client.post(
            self._duplicate_url(),
            {
                'title': 'Another Copy',
                'document_date': '02-20-2024',
                'content': 'Copy body.',
            },
        )

        self.source_report.refresh_from_db()
        self.assertEqual(self.source_report.title, 'Source Report')
        self.assertEqual(
            self.source_report.content,
            '# Source content\n\nBody of the source report.',
        )
        self.assertEqual(self.source_report.document_date, date(2024, 1, 15))
        self.assertEqual(self.source_report.template, self.template)
        self.assertEqual(self.source_report.created_by, self.doctor)
        self.assertEqual(self.source_report.updated_by, self.doctor)
        self.assertEqual(
            self.source_report.event_datetime,
            self.source_event_datetime,
        )
