from datetime import date, datetime, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from apps.patients.models import Patient
from apps.events.models import Event
from apps.dischargereports.models import DischargeReport

User = get_user_model()


class DischargeReportModelTests(TestCase):
    def setUp(self):
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

    def test_save_sets_event_type(self):
        """Test that save() sets correct event type"""
        report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description='Test report',
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 5),
            medical_specialty='Test Specialty',
            admission_history='Test history',
            problems_and_diagnosis='Test diagnosis',
            exams_list='Test exams',
            procedures_list='Test procedures',
            inpatient_medical_history='Test medical history',
            discharge_status='Test status',
            discharge_recommendations='Test recommendations',
            created_by=self.user,
            updated_by=self.user
        )
        self.assertEqual(report.event_type, Event.DISCHARGE_REPORT_EVENT)

    def test_is_draft_default_true(self):
        """Test that is_draft defaults to True"""
        report = DischargeReport(
            patient=self.patient,
            event_datetime=timezone.now(),
            description='Test report',
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 5),
            medical_specialty='Test Specialty',
            created_by=self.user,
            updated_by=self.user
        )
        self.assertTrue(report.is_draft)

    def test_string_representation(self):
        """Test __str__ method"""
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
        expected = f"Relatório de Alta - {self.patient.name} - 05/01/2024 (Rascunho)"
        self.assertEqual(str(report), expected)

    def test_can_be_edited_by_user_draft(self):
        """Test that drafts can be edited by creator"""
        report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description='Test report',
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 5),
            medical_specialty='Test Specialty',
            is_draft=True,
            created_by=self.user,
            updated_by=self.user
        )
        self.assertTrue(report.can_be_edited_by_user(self.user))

    def test_can_be_deleted_by_user_rules(self):
        """Test delete permissions for draft and final reports"""
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

        self.assertTrue(draft_report.can_be_deleted_by_user(self.user))
        self.assertTrue(final_report.can_be_deleted_by_user(self.user))

        old_datetime = timezone.now() - timedelta(hours=25)
        old_final_report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=old_datetime,
            description='Old final report',
            admission_date=date(2024, 2, 1),
            discharge_date=date(2024, 2, 5),
            medical_specialty='Test Specialty',
            is_draft=False,
            created_by=self.user,
            updated_by=self.user
        )
        DischargeReport.objects.filter(pk=old_final_report.pk).update(created_at=old_datetime)
        old_final_report.refresh_from_db()
        self.assertFalse(old_final_report.can_be_deleted_by_user(self.user))

    def test_status_display_properties(self):
        """Test status display properties"""
        draft_report = DischargeReport(is_draft=True)
        final_report = DischargeReport(is_draft=False)

        self.assertEqual(draft_report.status_display, "Rascunho")
        self.assertEqual(final_report.status_display, "Finalizado")

        self.assertEqual(draft_report.status_badge_class, "badge bg-warning text-dark")
        self.assertEqual(final_report.status_badge_class, "badge bg-success")

    def test_can_be_edited_by_user_final_within_24h(self):
        """Test that final reports can be edited within 24 hours"""
        report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description='Recent final report',
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 5),
            medical_specialty='Test Specialty',
            is_draft=False,
            created_by=self.user,
            updated_by=self.user
        )
        self.assertTrue(report.can_be_edited_by_user(self.user))

    def test_can_be_edited_by_user_final_after_24h(self):
        """Test that final reports cannot be edited after 24 hours"""
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
        report.refresh_from_db()
        self.assertFalse(report.can_be_edited_by_user(self.user))

    def test_can_be_edited_by_user_different_user(self):
        """Test that reports cannot be edited by different users"""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
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
        self.assertFalse(report.can_be_edited_by_user(other_user))

    def test_get_absolute_url(self):
        """Test get_absolute_url method"""
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
        expected_url = f'/dischargereports/{report.pk}/'
        self.assertEqual(report.get_absolute_url(), expected_url)
