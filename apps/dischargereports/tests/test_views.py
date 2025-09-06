from datetime import date, datetime, timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from apps.patients.models import Patient
from apps.dischargereports.models import DischargeReport

User = get_user_model()


class DischargeReportViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            created_by=self.user,
            updated_by=self.user
        )

    def test_create_view_requires_login(self):
        """Test that create view requires authentication"""
        url = reverse('apps.dischargereports:dischargereport_create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_create_view_saves_draft_by_default(self):
        """Test that create view saves as draft by default"""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('apps.dischargereports:dischargereport_create')

        data = {
            'patient': self.patient.pk,
            'event_datetime': timezone.now(),
            'description': 'Test report',
            'admission_date': date(2024, 1, 1),
            'discharge_date': date(2024, 1, 5),
            'medical_specialty': 'Test Specialty',
            'admission_history': 'Test history',
            'problems_and_diagnosis': 'Test diagnosis',
            'exams_list': 'Test exams',
            'procedures_list': 'Test procedures',
            'inpatient_medical_history': 'Test medical history',
            'discharge_status': 'Test status',
            'discharge_recommendations': 'Test recommendations',
            'save_draft': 'Save Draft'
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)  # Redirect after save

        report = DischargeReport.objects.get(patient=self.patient)
        self.assertTrue(report.is_draft)

    def test_create_view_saves_final(self):
        """Test that create view can save as final"""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('apps.dischargereports:dischargereport_create')

        data = {
            'patient': self.patient.pk,
            'event_datetime': timezone.now(),
            'description': 'Test report',
            'admission_date': date(2024, 1, 1),
            'discharge_date': date(2024, 1, 5),
            'medical_specialty': 'Test Specialty',
            'admission_history': 'Test history',
            'problems_and_diagnosis': 'Test diagnosis',
            'exams_list': 'Test exams',
            'procedures_list': 'Test procedures',
            'inpatient_medical_history': 'Test medical history',
            'discharge_status': 'Test status',
            'discharge_recommendations': 'Test recommendations',
            'save_final': 'Save Final'
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)

        report = DischargeReport.objects.get(patient=self.patient)
        self.assertFalse(report.is_draft)

    def test_update_view_blocks_non_editable(self):
        """Test that update view blocks non-editable reports"""
        # Create final report older than 24 hours
        old_datetime = timezone.now() - timedelta(hours=25)
        report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=old_datetime,
            description='Old final report',
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 5),
            medical_specialty='Test Specialty',
            is_draft=False,
            created_by=self.user,
            updated_by=self.user
        )
        # Manually set created_at to simulate old report
        DischargeReport.objects.filter(pk=report.pk).update(created_at=old_datetime)

        self.client.login(username='testuser', password='testpass123')
        url = reverse('apps.dischargereports:dischargereport_update', kwargs={'pk': report.pk})

        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)  # PermissionDenied

    def test_delete_view_allows_drafts_only(self):
        """Test that delete view only allows draft deletion"""
        draft_report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description='Draft report',
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 5),
            medical_specialty='Test Specialty',
            is_draft=True,
            created_by=self.user,
            updated_by=self.user
        )

        final_report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description='Final report',
            admission_date=date(2024, 2, 1),
            discharge_date=date(2024, 2, 5),
            medical_specialty='Test Specialty',
            is_draft=False,
            created_by=self.user,
            updated_by=self.user
        )

        self.client.login(username='testuser', password='testpass123')

        # Draft can be deleted
        draft_url = reverse('apps.dischargereports:dischargereport_delete', kwargs={'pk': draft_report.pk})
        response = self.client.get(draft_url)
        self.assertEqual(response.status_code, 200)

        # Final report cannot be deleted
        final_url = reverse('apps.dischargereports:dischargereport_delete', kwargs={'pk': final_report.pk})
        response = self.client.get(final_url)
        self.assertEqual(response.status_code, 403)

    def test_detail_view_requires_login(self):
        """Test that detail view requires authentication"""
        report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description='Test report',
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 5),
            medical_specialty='Test Specialty',
            created_by=self.user,
            updated_by=self.user
        )
        url = reverse('apps.dischargereports:dischargereport_detail', kwargs={'pk': report.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_detail_view_works_when_authenticated(self):
        """Test that detail view works when authenticated"""
        self.client.login(username='testuser', password='testpass123')
        report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description='Test report',
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 5),
            medical_specialty='Test Specialty',
            created_by=self.user,
            updated_by=self.user
        )
        url = reverse('apps.dischargereports:dischargereport_detail', kwargs={'pk': report.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test report')

    def test_list_view_requires_login(self):
        """Test that list view requires authentication"""
        url = reverse('apps.dischargereports:dischargereport_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_list_view_shows_reports(self):
        """Test that list view shows reports"""
        self.client.login(username='testuser', password='testpass123')
        report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description='Test report',
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 5),
            medical_specialty='Test Specialty',
            created_by=self.user,
            updated_by=self.user
        )
        url = reverse('apps.dischargereports:dischargereport_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test report')

    def test_update_view_saves_draft(self):
        """Test that update view can save as draft"""
        self.client.login(username='testuser', password='testpass123')
        report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description='Original report',
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 5),
            medical_specialty='Test Specialty',
            is_draft=True,
            created_by=self.user,
            updated_by=self.user
        )
        url = reverse('apps.dischargereports:dischargereport_update', kwargs={'pk': report.pk})

        data = {
            'patient': self.patient.pk,
            'event_datetime': datetime.now(),
            'description': 'Updated report',
            'admission_date': date(2024, 1, 1),
            'discharge_date': date(2024, 1, 5),
            'medical_specialty': 'Test Specialty',
            'admission_history': 'Test history',
            'problems_and_diagnosis': 'Test diagnosis',
            'exams_list': 'Test exams',
            'procedures_list': 'Test procedures',
            'inpatient_medical_history': 'Test medical history',
            'discharge_status': 'Test status',
            'discharge_recommendations': 'Test recommendations',
            'save_draft': 'Save Draft'
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)

        report.refresh_from_db()
        self.assertTrue(report.is_draft)
        self.assertEqual(report.description, 'Updated report')

    def test_update_view_saves_final(self):
        """Test that update view can save as final"""
        self.client.login(username='testuser', password='testpass123')
        report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description='Original report',
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 5),
            medical_specialty='Test Specialty',
            is_draft=True,
            created_by=self.user,
            updated_by=self.user
        )
        url = reverse('apps.dischargereports:dischargereport_update', kwargs={'pk': report.pk})

        data = {
            'patient': self.patient.pk,
            'event_datetime': datetime.now(),
            'description': 'Final report',
            'admission_date': date(2024, 1, 1),
            'discharge_date': date(2024, 1, 5),
            'medical_specialty': 'Test Specialty',
            'admission_history': 'Test history',
            'problems_and_diagnosis': 'Test diagnosis',
            'exams_list': 'Test exams',
            'procedures_list': 'Test procedures',
            'inpatient_medical_history': 'Test medical history',
            'discharge_status': 'Test status',
            'discharge_recommendations': 'Test recommendations',
            'save_final': 'Save Final'
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)

        report.refresh_from_db()
        self.assertFalse(report.is_draft)
        self.assertEqual(report.description, 'Final report')

    def test_delete_view_deletes_draft(self):
        """Test that delete view actually deletes draft reports"""
        self.client.login(username='testuser', password='testpass123')
        report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description='Draft to delete',
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 5),
            medical_specialty='Test Specialty',
            is_draft=True,
            created_by=self.user,
            updated_by=self.user
        )
        url = reverse('apps.dischargereports:dischargereport_delete', kwargs={'pk': report.pk})

        # Get confirmation page
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Confirm deletion
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)

        # Verify report is deleted
        self.assertFalse(DischargeReport.objects.filter(pk=report.pk).exists())