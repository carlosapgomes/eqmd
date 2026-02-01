"""
Tests for report detail, update, and delete views.
"""
from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import EqmdCustomUser
from apps.patients.models import Patient
from apps.reports.models import ReportTemplate, Report


class ReportDetailViewTests(TestCase):
    """Tests for report detail view."""

    def setUp(self):
        """Set up test users, patient, and report."""
        self.doctor = EqmdCustomUser.objects.create_user(
            username='doctor',
            email='doctor@test.com',
            password='testpass123',
            profession_type=EqmdCustomUser.MEDICAL_DOCTOR,
            password_change_required=False,
            terms_accepted=True,
        )
        self.other_user = EqmdCustomUser.objects.create_user(
            username='other',
            email='other@test.com',
            password='testpass123',
            profession_type=EqmdCustomUser.NURSE,
            password_change_required=False,
            terms_accepted=True,
        )

        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            created_by=self.doctor,
            updated_by=self.doctor,
            current_record_number='REC12345',
        )

        self.report = Report.objects.create(
            patient=self.patient,
            created_by=self.doctor,
            updated_by=self.doctor,
            title='Test Report',
            content='# Test Report\n\nThis is test content with **bold** text.',
            document_date=date(2024, 1, 15),
            event_datetime=timezone.now(),
        )

    def test_report_detail_shows_markdown(self):
        """Report detail view displays rendered markdown content."""
        self.client.login(username='doctor', password='testpass123')
        url = reverse('reports:report_detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Report')
        self.assertContains(response, 'test content')
        self.assertContains(response, 'Test Report</h1>')  # Markdown rendered as HTML

    def test_report_detail_requires_login(self):
        """Report detail view requires authentication."""
        url = reverse('reports:report_detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/accounts/login/'))

    def test_report_detail_shows_patient_info(self):
        """Report detail view shows patient information."""
        self.client.login(username='doctor', password='testpass123')
        url = reverse('reports:report_detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Patient')
        self.assertContains(response, 'REC12345')

    def test_report_detail_shows_document_date(self):
        """Report detail view shows document date."""
        self.client.login(username='doctor', password='testpass123')
        url = reverse('reports:report_detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '15/01/2024')


class ReportUpdateViewTests(TestCase):
    """Tests for report update view."""

    def setUp(self):
        """Set up test users, patient, and reports."""
        self.doctor = EqmdCustomUser.objects.create_user(
            username='doctor',
            email='doctor@test.com',
            password='testpass123',
            profession_type=EqmdCustomUser.MEDICAL_DOCTOR,
            password_change_required=False,
            terms_accepted=True,
        )
        self.other_user = EqmdCustomUser.objects.create_user(
            username='other',
            email='other@test.com',
            password='testpass123',
            profession_type=EqmdCustomUser.NURSE,
            password_change_required=False,
            terms_accepted=True,
        )

        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            created_by=self.doctor,
            updated_by=self.doctor,
            current_record_number='REC12345',
        )

        # Recent report (within 24h)
        self.recent_report = Report.objects.create(
            patient=self.patient,
            created_by=self.doctor,
            updated_by=self.doctor,
            title='Recent Report',
            content='Original content',
            document_date=date(2024, 1, 15),
            event_datetime=timezone.now(),
        )

        # Old report (outside 24h window)
        self.old_report = Report.objects.create(
            patient=self.patient,
            created_by=self.doctor,
            updated_by=self.doctor,
            title='Old Report',
            content='Old content',
            document_date=date(2024, 1, 10),
            event_datetime=timezone.now() - timedelta(hours=25),
        )

        # Report by other user
        self.other_report = Report.objects.create(
            patient=self.patient,
            created_by=self.other_user,
            updated_by=self.other_user,
            title='Other Report',
            content='Other content',
            document_date=date(2024, 1, 15),
            event_datetime=timezone.now(),
        )

    def test_report_update_requires_login(self):
        """Report update view requires authentication."""
        url = reverse('reports:report_update', kwargs={'pk': self.recent_report.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/accounts/login/'))

    def test_report_update_allowed_within_24h_by_creator(self):
        """Report creator can update report within 24 hours."""
        self.client.login(username='doctor', password='testpass123')
        url = reverse('reports:report_update', kwargs={'pk': self.recent_report.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Recent Report')
        self.assertContains(response, 'Original content')

        # Submit update
        response = self.client.post(
            url,
            {
                'title': 'Updated Report',
                'document_date': '01-16-2024',
                'content': 'Updated content',
            }
        )

        self.assertEqual(response.status_code, 302)

        # Verify report was updated
        self.recent_report.refresh_from_db()
        self.assertEqual(self.recent_report.title, 'Updated Report')
        self.assertEqual(self.recent_report.content, 'Updated content')
        self.assertEqual(self.recent_report.document_date, date(2024, 1, 16))

    def test_report_update_denied_after_24h(self):
        """Report cannot be updated after 24 hours."""
        self.client.login(username='doctor', password='testpass123')
        url = reverse('reports:report_update', kwargs={'pk': self.old_report.pk})

        # GET should be denied
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        # POST should also be denied
        response = self.client.post(
            url,
            {
                'title': 'Hacked Update',
                'document_date': '01-16-2024',
                'content': 'Hacked content',
            }
        )

        self.assertEqual(response.status_code, 403)

        # Verify report was not updated
        self.old_report.refresh_from_db()
        self.assertEqual(self.old_report.title, 'Old Report')
        self.assertEqual(self.old_report.content, 'Old content')

    def test_report_update_denied_for_non_creator(self):
        """Report cannot be updated by non-creator, even within 24h."""
        self.client.login(username='doctor', password='testpass123')  # NOT the creator
        url = reverse('reports:report_update', kwargs={'pk': self.other_report.pk})

        # GET should be denied
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        # POST should also be denied
        response = self.client.post(
            url,
            {
                'title': 'Hacked by other',
                'document_date': '01-16-2024',
                'content': 'Hacked content',
            }
        )

        self.assertEqual(response.status_code, 403)

        # Verify report was not updated
        self.other_report.refresh_from_db()
        self.assertEqual(self.other_report.title, 'Other Report')


class ReportDeleteViewTests(TestCase):
    """Tests for report delete view."""

    def setUp(self):
        """Set up test users, patient, and reports."""
        self.doctor = EqmdCustomUser.objects.create_user(
            username='doctor',
            email='doctor@test.com',
            password='testpass123',
            profession_type=EqmdCustomUser.MEDICAL_DOCTOR,
            password_change_required=False,
            terms_accepted=True,
        )
        self.other_user = EqmdCustomUser.objects.create_user(
            username='other',
            email='other@test.com',
            password='testpass123',
            profession_type=EqmdCustomUser.NURSE,
            password_change_required=False,
            terms_accepted=True,
        )

        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            created_by=self.doctor,
            updated_by=self.doctor,
            current_record_number='REC12345',
        )

        # Recent report (within 24h)
        self.recent_report = Report.objects.create(
            patient=self.patient,
            created_by=self.doctor,
            updated_by=self.doctor,
            title='Recent Report',
            content='Recent content',
            document_date=date(2024, 1, 15),
            event_datetime=timezone.now(),
        )

        # Old report (outside 24h window)
        self.old_report = Report.objects.create(
            patient=self.patient,
            created_by=self.doctor,
            updated_by=self.doctor,
            title='Old Report',
            content='Old content',
            document_date=date(2024, 1, 10),
            event_datetime=timezone.now() - timedelta(hours=25),
        )

        # Report by other user
        self.other_report = Report.objects.create(
            patient=self.patient,
            created_by=self.other_user,
            updated_by=self.other_user,
            title='Other Report',
            content='Other content',
            document_date=date(2024, 1, 15),
            event_datetime=timezone.now(),
        )

    def test_report_delete_requires_login(self):
        """Report delete view requires authentication."""
        url = reverse('reports:report_delete', kwargs={'pk': self.recent_report.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/accounts/login/'))

    def test_report_delete_allowed_within_24h_by_creator(self):
        """Report creator can delete report within 24 hours."""
        self.client.login(username='doctor', password='testpass123')
        url = reverse('reports:report_delete', kwargs={'pk': self.recent_report.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Recent Report')
        self.assertContains(response, 'Tem certeza')

        # Confirm deletion
        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)

        # Verify report was soft deleted
        self.recent_report.refresh_from_db()
        self.assertTrue(self.recent_report.is_deleted)

    def test_report_delete_denied_after_24h(self):
        """Report cannot be deleted after 24 hours."""
        self.client.login(username='doctor', password='testpass123')
        url = reverse('reports:report_delete', kwargs={'pk': self.old_report.pk})

        # GET should be denied
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        # POST should also be denied
        response = self.client.post(url)

        self.assertEqual(response.status_code, 403)

        # Verify report was not deleted
        self.old_report.refresh_from_db()
        self.assertFalse(self.old_report.is_deleted)

    def test_report_delete_denied_for_non_creator(self):
        """Report cannot be deleted by non-creator, even within 24h."""
        self.client.login(username='doctor', password='testpass123')  # NOT the creator
        url = reverse('reports:report_delete', kwargs={'pk': self.other_report.pk})

        # GET should be denied
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        # POST should also be denied
        response = self.client.post(url)

        self.assertEqual(response.status_code, 403)

        # Verify report was not deleted
        self.other_report.refresh_from_db()
        self.assertFalse(self.other_report.is_deleted)

    def test_report_delete_redirects_to_timeline(self):
        """After successful delete, redirect to patient timeline."""
        self.client.login(username='doctor', password='testpass123')
        url = reverse('reports:report_delete', kwargs={'pk': self.recent_report.pk})

        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)

        expected_url = reverse(
            'patients:patient_events_timeline',
            kwargs={'patient_id': self.patient.pk}
        )
        self.assertTrue(response.url.startswith(expected_url))
