from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from ..forms import PatientForm
from ..models import Patient, PatientRecordNumber
from ..services.temporary_record import (
    generate_temporary_record_number,
    is_temporary_record_number,
)
from ..validators import TEMPORARY_RECORD_PREFIX

User = get_user_model()

TEMPORARY_NUMBER_PATTERN = r"^TMP-[0-9A-F]{8}$"
TEMPORARY_RECORD_REASON = "Paciente atendido em emergência sem documento"


class TemporaryRecordNumberServiceTests(TestCase):
    """Unit tests for the server-side temporary record number generator."""

    def test_generated_numbers_follow_tmp_format_and_are_unique(self):
        """Two consecutive generations differ and match ^TMP-[0-9A-F]{8}$"""
        first = generate_temporary_record_number()
        second = generate_temporary_record_number()

        self.assertRegex(first, TEMPORARY_NUMBER_PATTERN)
        self.assertRegex(second, TEMPORARY_NUMBER_PATTERN)
        self.assertNotEqual(first, second)

    def test_prefix_constant_is_tmp_dash(self):
        """The reserved prefix constant lives in validators as TMP-"""
        self.assertEqual(TEMPORARY_RECORD_PREFIX, "TMP-")

    def test_is_temporary_record_number_detects_prefix(self):
        """Detection is case-insensitive, trims whitespace, and rejects others"""
        self.assertTrue(is_temporary_record_number("TMP-3F2A9C1B"))
        self.assertTrue(is_temporary_record_number("  tmp-abcdef12  "))
        self.assertFalse(is_temporary_record_number("REC001"))

    def test_generation_returns_candidate_even_after_exhausted_retries(self):
        """When every candidate collides, the last one is returned and the
        lifetime database constraint becomes the final guarantee."""
        with patch(
            "apps.patients.services.temporary_record.find_record_number_conflict",
            return_value=object(),
        ):
            candidate = generate_temporary_record_number()
        self.assertRegex(candidate, TEMPORARY_NUMBER_PATTERN)


class TemporaryRecordPatientFormTests(TestCase):
    """PatientForm flow for creating patients with a temporary record number."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpassword",
            password_change_required=False,
            terms_accepted=True,
        )

    def _base_data(self):
        return {
            "name": "Temp Patient",
            "birthday": "1990-01-01",
            "gender": Patient.GenderChoices.MALE,
        }

    def test_valid_temporary_submission_creates_patient_with_generated_number(self):
        """Checkbox + reason creates a patient with a current TMP- number and
        the reason recorded in the audit trail."""
        data = self._base_data()
        data["use_temporary_record"] = "on"
        data["temporary_record_reason"] = TEMPORARY_RECORD_REASON

        form = PatientForm(data)
        self.assertTrue(form.is_valid())

        form.instance.created_by = self.user
        form.instance.updated_by = self.user
        form.current_user = self.user
        patient = form.save(commit=True)

        patient.refresh_from_db()
        self.assertRegex(patient.current_record_number, TEMPORARY_NUMBER_PATTERN)

        record = PatientRecordNumber.objects.get(patient=patient, is_current=True)
        self.assertEqual(record.record_number, patient.current_record_number)
        self.assertIn(TEMPORARY_RECORD_REASON, record.change_reason)
        self.assertTrue(record.change_reason.startswith("Registro temporário:"))

    def test_temporary_submission_requires_reason(self):
        """Checkbox without a reason is invalid on temporary_record_reason"""
        data = self._base_data()
        data["use_temporary_record"] = "on"

        form = PatientForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn("temporary_record_reason", form.errors)
        self.assertIn(
            "Informe o motivo do registro temporário.",
            form.errors["temporary_record_reason"],
        )

    def test_missing_number_without_temporary_flag_still_required(self):
        """Without the checkbox, an empty number keeps the field required"""
        form = PatientForm(self._base_data())
        self.assertFalse(form.is_valid())
        self.assertIn("initial_record_number", form.errors)

    def test_definitive_flow_is_preserved(self):
        """Without the checkbox, a typed number keeps the classic behavior"""
        data = self._base_data()
        data["initial_record_number"] = "REC001"

        form = PatientForm(data)
        self.assertTrue(form.is_valid())

        form.instance.created_by = self.user
        form.instance.updated_by = self.user
        form.current_user = self.user
        patient = form.save(commit=True)

        patient.refresh_from_db()
        self.assertEqual(patient.current_record_number, "REC001")

        record = PatientRecordNumber.objects.get(patient=patient, is_current=True)
        self.assertEqual(record.record_number, "REC001")
        self.assertEqual(record.change_reason, "Número inicial do prontuário")

    def test_typed_number_is_ignored_when_temporary(self):
        """With the checkbox marked, any typed number is discarded"""
        data = self._base_data()
        data["use_temporary_record"] = "on"
        data["temporary_record_reason"] = TEMPORARY_RECORD_REASON
        data["initial_record_number"] = "REC001"

        form = PatientForm(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["initial_record_number"], "")
