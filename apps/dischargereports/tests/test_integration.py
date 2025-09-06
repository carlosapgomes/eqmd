from datetime import date, datetime, timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.patients.models import Patient
from apps.dischargereports.models import DischargeReport

User = get_user_model()


class DischargeReportIntegrationTests(TestCase):
    """Test complete workflows"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.patient = Patient.objects.create(
            name='Integration Test Patient',
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            created_by=self.user,
            updated_by=self.user
        )

    def test_complete_draft_to_final_workflow(self):
        """Test creating draft, editing, and finalizing"""
        self.client.login(username='testuser', password='testpass123')

        # Create draft
        create_url = reverse('apps.dischargereports:dischargereport_create')
        create_data = {
            'patient': self.patient.pk,
            'event_datetime': timezone.now(),
            'description': 'Test workflow report',
            'admission_date': date(2024, 1, 1),
            'discharge_date': date(2024, 1, 5),
            'medical_specialty': 'Integration Test',
            'admission_history': 'Initial history',
            'problems_and_diagnosis': 'Initial diagnosis',
            'exams_list': 'Initial exams',
            'procedures_list': 'Initial procedures',
            'inpatient_medical_history': 'Initial medical history',
            'discharge_status': 'Initial status',
            'discharge_recommendations': 'Initial recommendations',
            'save_draft': 'Save Draft'
        }

        response = self.client.post(create_url, create_data)
        self.assertEqual(response.status_code, 302)

        report = DischargeReport.objects.get(patient=self.patient)
        self.assertTrue(report.is_draft)

        # Edit draft
        update_url = reverse('apps.dischargereports:dischargereport_update', kwargs={'pk': report.pk})
        update_data = create_data.copy()
        update_data.update({
            'problems_and_diagnosis': 'Updated diagnosis',
            'save_final': 'Save Final'  # Finalize this time
        })

        response = self.client.post(update_url, update_data)
        self.assertEqual(response.status_code, 302)

        report.refresh_from_db()
        self.assertFalse(report.is_draft)
        self.assertEqual(report.problems_and_diagnosis, 'Updated diagnosis')

        # Verify can't delete finalized report
        delete_url = reverse('apps.dischargereports:dischargereport_delete', kwargs={'pk': report.pk})
        response = self.client.get(delete_url)
        self.assertEqual(response.status_code, 403)

    def test_draft_cannot_be_edited_after_24h_when_finalized(self):
        """Test that finalized draft cannot be edited after 24 hours"""
        self.client.login(username='testuser', password='testpass123')

        # Create and finalize report
        report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=timezone.now() - timedelta(hours=25),
            description='Old finalized report',
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 5),
            medical_specialty='Test Specialty',
            is_draft=False,
            created_by=self.user,
            updated_by=self.user
        )
        # Manually set created_at to simulate old report
        DischargeReport.objects.filter(pk=report.pk).update(created_at=timezone.now() - timedelta(hours=25))
        report.refresh_from_db()

        # Try to edit
        update_url = reverse('apps.dischargereports:dischargereport_update', kwargs={'pk': report.pk})
        response = self.client.get(update_url)
        self.assertEqual(response.status_code, 403)

    def test_multiple_reports_for_same_patient(self):
        """Test creating multiple reports for the same patient"""
        self.client.login(username='testuser', password='testpass123')

        # Create first report
        first_report_data = {
            'patient': self.patient.pk,
            'event_datetime': timezone.now(),
            'description': 'First report',
            'admission_date': date(2024, 1, 1),
            'discharge_date': date(2024, 1, 5),
            'medical_specialty': 'Cardiology',
            'admission_history': 'First admission',
            'problems_and_diagnosis': 'First diagnosis',
            'exams_list': 'First exams',
            'procedures_list': 'First procedures',
            'inpatient_medical_history': 'First medical history',
            'discharge_status': 'First status',
            'discharge_recommendations': 'First recommendations',
            'save_final': 'Save Final'
        }

        response = self.client.post(reverse('apps.dischargereports:dischargereport_create'), first_report_data)
        self.assertEqual(response.status_code, 302)

        # Create second report
        second_report_data = {
            'patient': self.patient.pk,
            'event_datetime': timezone.now(),
            'description': 'Second report',
            'admission_date': date(2024, 2, 1),
            'discharge_date': date(2024, 2, 10),
            'medical_specialty': 'Neurology',
            'admission_history': 'Second admission',
            'problems_and_diagnosis': 'Second diagnosis',
            'exams_list': 'Second exams',
            'procedures_list': 'Second procedures',
            'inpatient_medical_history': 'Second medical history',
            'discharge_status': 'Second status',
            'discharge_recommendations': 'Second recommendations',
            'save_final': 'Save Final'
        }

        response = self.client.post(reverse('apps.dischargereports:dischargereport_create'), second_report_data)
        self.assertEqual(response.status_code, 302)

        # Verify both reports exist
        self.assertEqual(DischargeReport.objects.filter(patient=self.patient).count(), 2)

        # Verify list view shows both reports
        response = self.client.get(reverse('apps.dischargereports:dischargereport_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'First report')
        self.assertContains(response, 'Second report')

    def test_draft_deletion_workflow(self):
        """Test complete draft deletion workflow"""
        self.client.login(username='testuser', password='testpass123')

        # Create draft
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

        # Verify draft exists
        self.assertTrue(DischargeReport.objects.filter(pk=report.pk).exists())

        # Delete draft
        delete_url = reverse('apps.dischargereports:dischargereport_delete', kwargs={'pk': report.pk})
        response = self.client.post(delete_url)
        self.assertEqual(response.status_code, 302)

        # Verify draft is deleted
        self.assertFalse(DischargeReport.objects.filter(pk=report.pk).exists())

    def test_unauthorized_user_cannot_edit(self):
        """Test that unauthorized users cannot edit reports"""
        # Create another user
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )

        # Create report as original user
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

        # Try to edit as other user
        self.client.login(username='otheruser', password='otherpass123')
        update_url = reverse('apps.dischargereports:dischargereport_update', kwargs={'pk': report.pk})
        response = self.client.get(update_url)
        self.assertEqual(response.status_code, 403)

    def test_form_validation_integration(self):
        """Test form validation in the context of views"""
        self.client.login(username='testuser', password='testpass123')

        # Try to create report with invalid data (discharge before admission)
        invalid_data = {
            'patient': self.patient.pk,
            'event_datetime': timezone.now(),
            'description': 'Invalid report',
            'admission_date': date(2024, 1, 5),
            'discharge_date': date(2024, 1, 1),  # Before admission date
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

        response = self.client.post(reverse('apps.dischargereports:dischargereport_create'), invalid_data)
        self.assertEqual(response.status_code, 200)  # Form should be redisplayed with errors
        self.assertContains(response, 'discharge_date')  # Error message should be present

    def test_timeline_integration(self):
        """Test that discharge reports appear in patient timeline"""
        self.client.login(username='testuser', password='testpass123')

        # Create discharge report
        report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description='Timeline test report',
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 5),
            medical_specialty='Test Specialty',
            created_by=self.user,
            updated_by=self.user
        )

        # Check patient timeline
        timeline_url = reverse('apps:patients:patient_timeline', kwargs={'pk': self.patient.pk})
        response = self.client.get(timeline_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Timeline test report')
        self.assertContains(response, 'Relatório de Alta')