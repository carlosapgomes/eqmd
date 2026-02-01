"""Tests for the context builder service."""
from datetime import date
from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.patients.models import Patient, Ward
from apps.reports.models import ReportTemplate
from apps.reports.services.context_builder import build_report_context

User = get_user_model()


class TestContextBuilder(TestCase):
    """Test cases for the context builder service."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="Doctor",
        )
        # Create user profile for full_name access
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
        # Create record number
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

    def test_context_builder_includes_patient_doctor_document_hospital_fields(self):
        """Test that context builder includes all required fields."""
        document_date = date(2026, 1, 15)
        context = build_report_context(
            patient=self.patient,
            doctor=self.user,
            document_date=document_date,
        )

        # Patient fields
        self.assertIn("patient_name", context)
        self.assertEqual(context["patient_name"], "John Doe")
        self.assertIn("patient_record_number", context)
        self.assertEqual(context["patient_record_number"], "REC12345")

        # Doctor fields
        self.assertIn("doctor_name", context)
        self.assertEqual(context["doctor_name"], "Dr. Test Doctor")

        # Document fields
        self.assertIn("document_date", context)
        self.assertEqual(context["document_date"], "15/01/2026")

    def test_context_builder_patient_without_record_number(self):
        """Test context builder handles patient without record number."""
        new_patient = Patient.objects.create(
            name="Jane Doe",
            birthday=date(1985, 5, 15),
            created_by=self.user,
            updated_by=self.user,
        )
        # No record number created

        context = build_report_context(
            patient=new_patient,
            doctor=self.user,
            document_date=date.today(),
        )

        self.assertEqual(context["patient_name"], "Jane Doe")
        self.assertEqual(context["patient_record_number"], "")

    def test_context_builder_doctor_without_profile(self):
        """Test context builder handles doctor without profile display_name."""
        doctor_without_profile = User.objects.create_user(
            username="noprofile",
            email="noprofile@example.com",
            password="testpass123",
            first_name="No",
            last_name="Profile",
        )

        context = build_report_context(
            patient=self.patient,
            doctor=doctor_without_profile,
            document_date=date.today(),
        )

        self.assertEqual(context["doctor_name"], "No Profile")

    def test_context_builder_includes_page_break(self):
        """Test that page_break placeholder is available in context."""
        context = build_report_context(
            patient=self.patient,
            doctor=self.user,
            document_date=date.today(),
        )

        self.assertIn("page_break", context)
