"""S6 R7: prescription document output denies drafts (design D10).

The prescription PDF and print endpoints deny drafts for every user and keep
serving definitive prescriptions as today.
"""

import io
from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.tests.helpers import create_navigation_user
from apps.patients.models import Patient

from ..models import OutpatientPrescription, PrescriptionItem

User = get_user_model()


def create_profession_user(username, profession_type):
    """Create a lifecycle-ready user; the profession signal assigns the group."""
    return create_navigation_user(
        username=username,
        email=f"{username}@example.com",
        password="testpass123",
        profession_type=profession_type,
    )


class PrescriptionDraftOutputGatingTests(TestCase):
    """R7: no document output for draft prescriptions."""

    @classmethod
    def setUpTestData(cls):
        call_command("setup_groups", stdout=StringIO())
        cls.student = create_profession_user("rx-output-student", User.STUDENT)
        cls.doctor = create_profession_user("rx-output-doctor", User.MEDICAL_DOCTOR)
        cls.patient = Patient.objects.create(
            name="Prescription Output Patient",
            birthday="1990-01-01",
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

    def setUp(self):
        cache.clear()

    def _create_prescription(self, *, author=None, is_draft=False):
        author = author or self.doctor
        prescription = OutpatientPrescription.objects.create(
            patient=self.patient,
            event_datetime=timezone.now() - timedelta(hours=1),
            prescription_date=timezone.localdate(),
            instructions="Uso oral.",
            status="draft",
            is_draft=is_draft,
            description="Receita",
            created_by=author,
            updated_by=author,
        )
        PrescriptionItem.objects.create(
            prescription=prescription,
            drug_name="Paracetamol",
            presentation="500mg comprimidos",
            usage_instructions="Tomar 1 comprimido de 8 em 8 horas.",
            quantity="21 comprimidos",
            order=1,
        )
        return prescription

    def _pdf_url(self, prescription):
        return reverse(
            "outpatientprescriptions:outpatientprescription_pdf",
            kwargs={"pk": prescription.pk},
        )

    def _print_url(self, prescription):
        return reverse(
            "outpatientprescriptions:outpatientprescription_print",
            kwargs={"pk": prescription.pk},
        )

    def test_pdf_denies_a_human_draft_for_every_user(self):
        draft = self._create_prescription(author=self.student, is_draft=True)

        for user in (self.student, self.doctor):
            self.client.force_login(user)
            self.assertEqual(self.client.get(self._pdf_url(draft)).status_code, 404)

    def test_print_denies_a_human_draft_for_every_user(self):
        draft = self._create_prescription(author=self.student, is_draft=True)

        for user in (self.student, self.doctor):
            self.client.force_login(user)
            self.assertEqual(self.client.get(self._print_url(draft)).status_code, 404)

    @patch(
        "apps.pdfgenerator.services.pdf_generator.HospitalLetterheadGenerator.create_prescription_pdf"
    )
    def test_pdf_serves_a_definitive_prescription(self, mock_create_pdf):
        mock_create_pdf.return_value = io.BytesIO(b"%PDF-1.4")
        final = self._create_prescription(author=self.doctor)
        self.client.force_login(self.doctor)

        response = self.client.get(self._pdf_url(final))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        mock_create_pdf.assert_called_once()

    def test_print_serves_a_definitive_prescription(self):
        final = self._create_prescription(author=self.doctor)
        self.client.force_login(self.doctor)

        response = self.client.get(self._print_url(final))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "outpatientprescriptions/outpatientprescription_print.html"
        )
