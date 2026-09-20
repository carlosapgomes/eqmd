"""Regression tests for discharge-report PDF patient headers."""

from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.dischargereports.models import DischargeReport
from apps.dischargereports.services.pdf_generator import DischargeReportPDFGenerator
from apps.patients.models import Patient

User = get_user_model()


class DischargeReportPDFHeaderTests(TestCase):
    """Ensure discharge PDFs remain valid with complete long names."""

    def test_long_patient_name_produces_valid_pdf(self):
        user = User.objects.create_user(
            username="headerdoctor",
            email="headerdoctor@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
        )
        patient = Patient.objects.create(
            name="Áurea Conceição Montenegro de Oliveira",
            birthday=date(1990, 1, 1),
            created_by=user,
            updated_by=user,
        )
        report = DischargeReport.objects.create(
            patient=patient,
            event_datetime=timezone.now(),
            description="Relatório sintético",
            admission_date=date(2025, 1, 1),
            discharge_date=date(2025, 1, 2),
            created_by=user,
            updated_by=user,
        )

        pdf = DischargeReportPDFGenerator().generate_from_report(report)

        self.assertEqual(pdf.read(4), b"%PDF")
