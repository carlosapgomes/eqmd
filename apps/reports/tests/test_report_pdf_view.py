"""
Tests for report PDF download view.
"""
from datetime import date

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import EqmdCustomUser
from apps.patients.models import Patient
from apps.reports.models import ReportTemplate, Report


class ReportPDFViewTests(TestCase):
    """Tests for report PDF download view."""

    def setUp(self):
        """Set up test users, patient, and report."""
        self.doctor = EqmdCustomUser.objects.create_user(
            username='doctor',
            email='doctor@test.com',
            password='testpass123',
            profession_type=EqmdCustomUser.MEDICAL_DOCTOR,
            password_change_required=False,
            terms_accepted=True,
            first_name='Dr.',
            last_name='Smith',
        )
        self.other_user = EqmdCustomUser.objects.create_user(
            username='otheruser',
            email='other@test.com',
            password='testpass123',
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
            description='Test Report',
            content='# Test Report\n\nPatient: Test Patient\nRecord: REC12345',
            document_date=date(2024, 1, 15),
            title='Test Report',
        )

    def test_report_pdf_requires_login(self):
        """PDF download view requires authentication."""
        url = reverse('reports:report_pdf', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/accounts/login/'))

    def test_report_pdf_requires_access(self):
        """PDF download view allows authenticated users to access."""
        self.client.login(username='otheruser', password='testpass123')
        url = reverse('reports:report_pdf', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        # Authenticated users can access all patients
        self.assertEqual(response.status_code, 200)

    def test_report_pdf_returns_pdf_content_type(self):
        """PDF download view returns PDF content type."""
        self.client.login(username='doctor', password='testpass123')
        url = reverse('reports:report_pdf', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_report_pdf_returns_attachment_disposition(self):
        """PDF download view returns as attachment with safe filename."""
        self.client.login(username='doctor', password='testpass123')
        url = reverse('reports:report_pdf', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        disposition = response.get('Content-Disposition', '')
        self.assertIn('attachment', disposition)
        self.assertIn('.pdf', disposition)

    def test_report_pdf_content_not_empty(self):
        """PDF download view returns non-empty PDF content."""
        self.client.login(username='doctor', password='testpass123')
        url = reverse('reports:report_pdf', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.content), 0)
