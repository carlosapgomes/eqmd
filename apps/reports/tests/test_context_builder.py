"""Tests for the context builder service."""
from datetime import date, datetime
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from unittest.mock import patch

from apps.patients.models import Patient, Ward
from apps.accounts.models import MedicalSpecialty
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
            profession_type=User.MEDICAL_DOCTOR,
            professional_registration_number="CRM-12345",
        )
        # Create user profile for full_name access
        self.user.profile.display_name = "Dr. Test Doctor"
        specialty = MedicalSpecialty.objects.create(
            name="Cardiology",
            abbreviation="CARD",
            is_active=True,
        )
        self.user.profile.current_specialty = specialty
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
            fiscal_number="FISC123",
            healthcard_number="HC123",
            bed="B12",
            status=Patient.Status.INPATIENT,
            ward=self.ward,
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

    @override_settings(
        HOSPITAL_CONFIG={
            "name": "Test Hospital",
            "city": "Test City",
            "state_full": "Test State",
            "address": "123 Test Street",
        }
    )
    def test_context_builder_includes_patient_doctor_document_hospital_fields(self):
        """Test that context builder includes all required fields."""
        document_date = date(2026, 1, 15)
        fixed_now = timezone.make_aware(datetime(2026, 1, 15, 10, 30))
        with patch("django.utils.timezone.localtime", return_value=fixed_now):
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
        self.assertEqual(context["patient_birth_date"], "01/01/1990")
        self.assertEqual(context["patient_age"], str(self.patient.age))
        self.assertEqual(context["patient_gender"], self.patient.get_gender_display())
        self.assertEqual(context["patient_fiscal_number"], "FISC123")
        self.assertEqual(context["patient_healthcard_number"], "HC123")
        self.assertEqual(context["patient_ward"], "TW")
        self.assertEqual(context["patient_bed"], "B12")
        self.assertEqual(context["patient_status"], self.patient.get_status_display())

        # Doctor fields
        self.assertIn("doctor_name", context)
        self.assertEqual(context["doctor_name"], "Dr. Test Doctor")
        self.assertEqual(context["doctor_profession"], self.user.get_profession_type_display())
        self.assertEqual(context["doctor_registration_number"], "CRM-12345")
        self.assertEqual(context["doctor_specialty"], "Cardiology")

        # Document fields
        self.assertIn("document_date", context)
        self.assertEqual(context["document_date"], "15/01/2026")
        self.assertEqual(context["document_datetime"], "15/01/2026 10:30")

        # Hospital fields
        self.assertEqual(context["hospital_name"], "Test Hospital")
        self.assertEqual(context["hospital_city"], "Test City")
        self.assertEqual(context["hospital_state"], "Test State")
        self.assertEqual(context["hospital_address"], "123 Test Street")

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
