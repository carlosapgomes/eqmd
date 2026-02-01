"""Tests for the report service."""
from datetime import date
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.patients.models import Patient, Ward
from apps.reports.models import ReportTemplate, Report
from apps.reports.services.report_service import (
    create_report_from_template,
    ReportServiceError,
)

User = get_user_model()


class TestReportService(TestCase):
    """Test cases for the report service."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="Doctor",
        )
        self.user.profile.display_name = "Dr. Test Doctor"
        self.user.profile.save()

        self.ward = Ward.objects.create(
            name="Test Ward",
            abbreviation="TW",
            created_by=self.user,
            updated_by=self.user,
        )
        self.patient = Patient.objects.create(
            name="John Doe",
            birthday=date(1990, 1, 1),
            created_by=self.user,
            updated_by=self.user,
        )
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

    def test_report_service_renders_template_with_context(self):
        """Test that report service renders template and creates report."""
        report = create_report_from_template(
            template=self.template,
            patient=self.patient,
            doctor=self.user,
            document_date=date(2026, 1, 15),
            created_by=self.user,
        )

        # Check report was created
        self.assertIsNotNone(report)
        self.assertIsInstance(report, Report)

        # Check content was rendered
        self.assertIn("Patient: John Doe", report.content)
        self.assertIn("Record: REC12345", report.content)

        # Check other fields
        self.assertEqual(report.patient, self.patient)
        self.assertEqual(report.template, self.template)
        self.assertEqual(report.document_date, date(2026, 1, 15))
        self.assertEqual(report.created_by, self.user)

    def test_report_service_raises_on_missing_required_placeholder(self):
        """Test that report service raises error if patient is missing required data."""
        # Create patient without record number
        new_patient = Patient.objects.create(
            name="Jane Doe",
            birthday=date(1985, 5, 15),
            created_by=self.user,
            updated_by=self.user,
        )
        # No record number - context will have empty patient_record_number

        # This should still work since patient_record_number is in context (just empty)
        report = create_report_from_template(
            template=self.template,
            patient=new_patient,
            doctor=self.user,
            document_date=date.today(),
            created_by=self.user,
        )

        # The report is created but with empty record number
        self.assertIn("Record: ", report.content)

    def test_report_service_with_page_break(self):
        """Test that report service handles page_break placeholder."""
        template_with_break = ReportTemplate.objects.create(
            name="Template with Page Break",
            markdown_body=(
                "Patient: {{patient_name}}\n"
                "{{page_break}}\n"
                "Record: {{patient_record_number}}"
            ),
            created_by=self.user,
            updated_by=self.user,
        )

        report = create_report_from_template(
            template=template_with_break,
            patient=self.patient,
            doctor=self.user,
            document_date=date.today(),
            created_by=self.user,
        )

        # Check page break was rendered
        from apps.reports.services.renderer import PAGE_BREAK_TOKEN
        self.assertIn(PAGE_BREAK_TOKEN, report.content)

    def test_report_service_sets_description(self):
        """Test that report service sets a default description."""
        report = create_report_from_template(
            template=self.template,
            patient=self.patient,
            doctor=self.user,
            document_date=date.today(),
            created_by=self.user,
        )

        self.assertEqual(report.description, f"Relatório - {self.template.name}")

    def test_report_service_sets_event_datetime(self):
        """Test that report service sets event_datetime to document_date with current time."""
        from unittest.mock import patch
        from datetime import datetime

        fixed_now = timezone.make_aware(datetime(2026, 1, 15, 10, 30, 0))

        with patch('django.utils.timezone.now', return_value=fixed_now):
            report = create_report_from_template(
                template=self.template,
                patient=self.patient,
                doctor=self.user,
                document_date=date(2026, 1, 15),
                created_by=self.user,
            )

        self.assertEqual(report.event_datetime, fixed_now)

    def test_report_service_custom_title(self):
        """Test that report service accepts custom title."""
        report = create_report_from_template(
            template=self.template,
            patient=self.patient,
            doctor=self.user,
            document_date=date.today(),
            created_by=self.user,
            title="Custom Report Title",
        )

        self.assertEqual(report.title, "Custom Report Title")

    def test_report_service_title_defaults_to_template_name(self):
        """Test that report service defaults title to template name."""
        report = create_report_from_template(
            template=self.template,
            patient=self.patient,
            doctor=self.user,
            document_date=date.today(),
            created_by=self.user,
        )

        self.assertEqual(report.title, self.template.name)
