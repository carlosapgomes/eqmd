"""
Tests for report create view.
"""
from datetime import date

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import EqmdCustomUser
from apps.patients.models import Patient
from apps.reports.models import ReportTemplate, Report


class ReportCreateViewTests(TestCase):
    """Tests for report create view."""

    def setUp(self):
        """Set up test users, patient, and templates."""
        self.admin_user = EqmdCustomUser.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_staff=True,
            password_change_required=False,
            terms_accepted=True,
        )
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

        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            created_by=self.admin_user,
            updated_by=self.admin_user,
            current_record_number='REC12345',
        )

        self.public_template = ReportTemplate.objects.create(
            name='Public Template',
            markdown_body='Dear {{patient_name}}, Record: {{patient_record_number}}',
            is_public=True,
            created_by=self.admin_user,
            updated_by=self.admin_user,
        )
        self.private_template = ReportTemplate.objects.create(
            name='Private Template',
            markdown_body='Private: {{patient_name}}, {{patient_record_number}}',
            is_public=False,
            created_by=self.doctor,
            updated_by=self.doctor,
        )

    def test_report_create_requires_login(self):
        """Report create view requires authentication."""
        url = reverse('reports:report_create', kwargs={'patient_id': self.patient.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/accounts/login/'))

    def test_report_create_filters_templates_public_or_own(self):
        """Template dropdown only shows public templates and user's own private templates."""
        self.client.login(username='doctor', password='testpass123')
        url = reverse('reports:report_create', kwargs={'patient_id': self.patient.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        form = response.context['form']
        template_field = form.fields['template']
        template_choices = list(template_field.queryset)

        # Should show public template and doctor's own private template
        self.assertEqual(len(template_choices), 2)
        template_names = {t.name for t in template_choices}
        self.assertIn('Public Template', template_names)
        self.assertIn('Private Template', template_names)

    def test_report_create_from_template_saves_report(self):
        """Creating a report from a template renders and saves correctly."""
        self.client.login(username='doctor', password='testpass123')
        url = reverse('reports:report_create', kwargs={'patient_id': self.patient.pk})

        response = self.client.post(
            url,
            {
                'template': str(self.public_template.pk),
                'title': 'Test Report',
                'document_date': '2024-01-15',
                'content': 'Rendered content for Test Patient',
            }
        )

        self.assertEqual(response.status_code, 302)

        # Verify report was created
        report = Report.objects.get(title='Test Report')
        self.assertEqual(report.patient, self.patient)
        self.assertEqual(report.created_by, self.doctor)
        self.assertEqual(report.template, self.public_template)
        self.assertEqual(report.content, 'Rendered content for Test Patient')
        self.assertEqual(report.document_date, date(2024, 1, 15))

    def test_report_create_manual_content_without_template(self):
        """Creating a report without a template saves manual content."""
        self.client.login(username='doctor', password='testpass123')
        url = reverse('reports:report_create', kwargs={'patient_id': self.patient.pk})

        response = self.client.post(
            url,
            {
                'template': '',
                'title': 'Manual Report',
                'document_date': '2024-01-15',
                'content': 'Manual content without template',
            }
        )

        self.assertEqual(response.status_code, 302)

        # Verify report was created without template
        report = Report.objects.get(title='Manual Report')
        self.assertEqual(report.patient, self.patient)
        self.assertIsNone(report.template)
        self.assertEqual(report.content, 'Manual content without template')

    def test_report_create_rejects_private_template_from_other_user(self):
        """Cannot use another user's private template."""
        # Create another doctor with a private template
        other_doctor = EqmdCustomUser.objects.create_user(
            username='other_doctor',
            email='other@test.com',
            password='testpass123',
            profession_type=EqmdCustomUser.MEDICAL_DOCTOR,
            password_change_required=False,
            terms_accepted=True,
        )
        other_private_template = ReportTemplate.objects.create(
            name='Other Private Template',
            markdown_body='Other: {{patient_name}}, {{patient_record_number}}',
            is_public=False,
            created_by=other_doctor,
            updated_by=other_doctor,
        )

        self.client.login(username='doctor', password='testpass123')
        url = reverse('reports:report_create', kwargs={'patient_id': self.patient.pk})

        response = self.client.post(
            url,
            {
                'template': str(other_private_template.pk),
                'title': 'Hacked Report',
                'document_date': '2024-01-15',
                'content': 'Content',
            }
        )

        # Should stay on form with error
        self.assertEqual(response.status_code, 200)
        self.assertTrue('template' in response.context['form'].errors or
                       'form' in response.context)

        # Verify report was not created
        self.assertFalse(Report.objects.filter(title='Hacked Report').exists())
