"""Tests for the Report model."""
from datetime import date
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.patients.models import Patient, Ward
from apps.events.models import Event
from apps.reports.models import ReportTemplate, Report

User = get_user_model()


class TestReportModel(TestCase):
    """Test cases for the Report model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="Doctor",
        )
        self.ward = Ward.objects.create(
            name="Test Ward",
            abbreviation="TW",
            created_by=self.user,
            updated_by=self.user,
        )
        self.patient = Patient.objects.create(
            name="Test Patient",
            birthday=date(1990, 1, 1),
            created_by=self.user,
            updated_by=self.user,
        )
        # Create a record number for the patient
        self.patient.update_current_record_number(
            record_number="REC12345",
            user=self.user,
        )
        self.template = ReportTemplate.objects.create(
            name="Test Template",
            markdown_body="Patient: {{patient_name}}, Record: {{patient_record_number}}",
            created_by=self.user,
            updated_by=self.user,
        )

    def test_report_save_sets_event_type(self):
        """Test that saving a report automatically sets event_type to REPORT_EVENT."""
        report = Report(
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user,
            description="Test Report",
            event_datetime=timezone.now(),
            content="Test content",
            document_date=date.today(),
            template=self.template,
        )
        report.save()

        saved_report = Report.objects.get(pk=report.pk)
        self.assertEqual(saved_report.event_type, Event.REPORT_EVENT)

    def test_report_template_delete_does_not_delete_report(self):
        """Test that deleting a template does not delete associated reports (SET_NULL)."""
        report = Report.objects.create(
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user,
            description="Test Report",
            event_datetime=timezone.now(),
            content="Test content",
            document_date=date.today(),
            template=self.template,
        )
        report_id = report.pk

        # Delete the template
        self.template.delete()

        # Report should still exist
        report.refresh_from_db()
        self.assertEqual(report.pk, report_id)
        self.assertIsNone(report.template)

    def test_report_str_returns_description(self):
        """Test that __str__ returns the description."""
        report = Report.objects.create(
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user,
            description="My Test Report",
            event_datetime=timezone.now(),
            content="Test content",
            document_date=date.today(),
        )
        self.assertEqual(str(report), "My Test Report")

    def test_report_optional_title(self):
        """Test that title is optional."""
        report_with_title = Report.objects.create(
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user,
            description="Report with title",
            event_datetime=timezone.now(),
            content="Test content",
            document_date=date.today(),
            title="Custom Title",
        )
        self.assertEqual(report_with_title.title, "Custom Title")

        report_without_title = Report.objects.create(
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user,
            description="Report without title",
            event_datetime=timezone.now(),
            content="Test content",
            document_date=date.today(),
        )
        self.assertEqual(report_without_title.title, "")

    def test_report_content_stored(self):
        """Test that report content is properly stored."""
        content = "# Patient Report\n\nThis is the rendered markdown content."
        report = Report.objects.create(
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user,
            description="Test Report",
            event_datetime=timezone.now(),
            content=content,
            document_date=date.today(),
        )
        self.assertEqual(report.content, content)

    def test_report_document_date(self):
        """Test that document_date is properly stored."""
        doc_date = date(2026, 1, 15)
        report = Report.objects.create(
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user,
            description="Test Report",
            event_datetime=timezone.now(),
            content="Test content",
            document_date=doc_date,
        )
        self.assertEqual(report.document_date, doc_date)

    def test_report_has_uuid_pk(self):
        """Test that the primary key is a UUID."""
        import uuid

        report = Report.objects.create(
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user,
            description="Test Report",
            event_datetime=timezone.now(),
            content="Test content",
            document_date=date.today(),
        )
        self.assertIsInstance(report.id, uuid.UUID)

    def test_report_inherits_from_event(self):
        """Test that Report is a proper Event subtype."""
        report = Report.objects.create(
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user,
            description="Test Report",
            event_datetime=timezone.now(),
            content="Test content",
            document_date=date.today(),
        )
        # Should be retrievable through Event.objects
        event = Event.objects.get(pk=report.pk)
        self.assertEqual(event.event_type, Event.REPORT_EVENT)

    def test_report_can_be_edited_within_24h(self):
        """Test that reports follow the 24h edit window rule."""
        report = Report.objects.create(
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user,
            description="Test Report",
            event_datetime=timezone.now(),
            content="Test content",
            document_date=date.today(),
        )
        # New reports should be editable
        self.assertTrue(report.can_be_edited)

    def test_report_optional_template(self):
        """Test that template is optional."""
        report_without_template = Report.objects.create(
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user,
            description="Manual Report",
            event_datetime=timezone.now(),
            content="Manually created content",
            document_date=date.today(),
        )
        self.assertIsNone(report_without_template.template)
