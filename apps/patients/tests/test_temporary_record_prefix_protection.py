"""Prefix protection and regularization tests (slice 002).

The ``TMP-`` prefix is reserved for server-generated temporary record
numbers. Every manual write door must reject typed ``TMP-`` values, and
regularizing a temporary number must preserve the temporary row as
history.
"""

from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from ..forms import (
    PatientForm,
    PatientRecordNumberForm,
    QuickRecordNumberUpdateForm,
)
from ..models import Patient, PatientRecordNumber
from .test_patient_record_constraint_database import (
    _create_doctor,
    _create_patient,
    _create_record,
)

TEMPORARY_NUMBER = "TMP-3F2A9C1B"
DEFINITIVE_NUMBER = "REC999"
PREFIX_RESERVATION_MESSAGE = (
    "Números iniciados em TMP- são reservados para registros temporários "
    "gerados pelo sistema."
)
BANNER_ACTION_TEXT = "Regularizar número do prontuário"


def _temporary_patient(user, name: str = "Temporary Patient") -> Patient:
    """Create a patient whose current number is a generated temporary."""
    patient = _create_patient(user, name=name)
    _create_record(patient, TEMPORARY_NUMBER, user)
    patient.current_record_number = TEMPORARY_NUMBER
    patient.save(update_fields=["current_record_number"])
    return patient


class PermanentRecordNumberValidatorTests(TestCase):
    """R1: the pure prefix validator is case-insensitive and trim-tolerant."""

    def test_validator_rejects_lowercase_tmp_prefix(self):
        """The reservation check normalizes case before matching."""
        from ..validators import validate_permanent_record_number

        with self.assertRaises(ValidationError):
            validate_permanent_record_number("tmp-abc")

    def test_validator_rejects_padded_uppercase_prefix(self):
        """Outer whitespace is ignored before matching the prefix."""
        from ..validators import validate_permanent_record_number

        with self.assertRaises(ValidationError):
            validate_permanent_record_number("  TMP-123  ")

    def test_validator_accepts_permanent_numbers(self):
        """Values without the reserved prefix pass untouched."""
        from ..validators import validate_permanent_record_number

        validate_permanent_record_number("REC001")


class PatientFormPrefixProtectionTests(TestCase):
    """R2 door 1: typed TMP- numbers are rejected at patient creation."""

    @classmethod
    def setUpTestData(cls):
        cls.user = _create_doctor("prefixdoc")

    def _base_data(self):
        return {
            "name": "Prefix Patient",
            "birthday": "1990-01-01",
            "gender": Patient.GenderChoices.MALE,
        }

    def test_patient_form_rejects_typed_temporary_number(self):
        """A typed TMP- number fails validation citing the reservation."""
        data = self._base_data()
        data["initial_record_number"] = "TMP-12345678"

        form = PatientForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn("initial_record_number", form.errors)
        self.assertIn(
            PREFIX_RESERVATION_MESSAGE,
            str(form.errors["initial_record_number"]),
        )


class RecordNumberFormsPrefixProtectionTests(TestCase):
    """R2 doors 2-3: typed TMP- numbers are rejected by both update forms."""

    @classmethod
    def setUpTestData(cls):
        cls.user = _create_doctor("formsdoc")
        cls.patient = _create_patient(cls.user, name="Form Door Patient")

    def test_record_number_form_rejects_typed_temporary_number(self):
        form = PatientRecordNumberForm(
            patient=self.patient,
            user=self.user,
            data={
                "record_number": "TMP-00000001",
                "change_reason": "Troca de número",
                "effective_date": timezone.localtime(timezone.now()).strftime(
                    "%Y-%m-%dT%H:%M"
                ),
            },
        )
        self.assertFalse(form.is_valid())
        self.assertIn("record_number", form.errors)
        self.assertIn(
            PREFIX_RESERVATION_MESSAGE,
            str(form.errors["record_number"]),
        )

    def test_quick_update_form_rejects_typed_temporary_number(self):
        form = QuickRecordNumberUpdateForm(
            data={
                "record_number": "TMP-00000001",
                "change_reason": "Troca rápida",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("record_number", form.errors)
        self.assertIn(
            PREFIX_RESERVATION_MESSAGE,
            str(form.errors["record_number"]),
        )


class ManagedDoorPrefixProtectionTests(TestCase):
    """R2 door 4: the managed model method rejects TMP- without any write."""

    def setUp(self):
        self.user = _create_doctor("managedoc")
        self.patient = _create_patient(self.user, name="Managed Door Patient")
        _create_record(self.patient, "REC001", self.user)
        self.patient.current_record_number = "REC001"
        self.patient.save(update_fields=["current_record_number"])

    def test_update_current_record_number_rejects_temporary_number(self):
        """TMP- is rejected and the current number stays untouched."""
        with self.assertRaises(ValidationError):
            self.patient.update_current_record_number(
                "TMP-00000001", self.user, reason="Deveria ser bloqueado"
            )

        self.patient.refresh_from_db()
        self.assertEqual(self.patient.current_record_number, "REC001")
        rows = PatientRecordNumber.objects.filter(patient=self.patient)
        self.assertEqual(rows.count(), 1)
        self.assertTrue(rows.filter(record_number="REC001", is_current=True).exists())


class RegularizationHistoryTests(TestCase):
    """R5: regularizing a temporary number preserves the full history."""

    def setUp(self):
        self.user = _create_doctor("regularizedoc")
        self.patient = _temporary_patient(self.user)

    def test_regularization_preserves_temporary_history_row(self):
        """TMP- row is kept as history; the new row records the transition."""
        self.patient.update_current_record_number(
            DEFINITIVE_NUMBER,
            self.user,
            reason="Regularização: número definitivo emitido",
        )

        self.patient.refresh_from_db()
        self.assertEqual(self.patient.current_record_number, DEFINITIVE_NUMBER)

        temporary_row = PatientRecordNumber.objects.get(
            patient=self.patient, record_number=TEMPORARY_NUMBER
        )
        self.assertFalse(temporary_row.is_current)

        definitive_row = PatientRecordNumber.objects.get(
            patient=self.patient, record_number=DEFINITIVE_NUMBER
        )
        self.assertTrue(definitive_row.is_current)
        self.assertEqual(definitive_row.previous_record_number, TEMPORARY_NUMBER)


class TemporaryRecordPropertyTests(TestCase):
    """R3: the temporary state derives from the current number prefix."""

    def setUp(self):
        self.user = _create_doctor("propertydoc")

    def test_is_temporary_record_property(self):
        temporary = _temporary_patient(self.user, name="Property Temp")
        self.assertTrue(temporary.is_temporary_record)

        definitive = _create_patient(self.user, name="Property Definitive")
        _create_record(definitive, "REC001", self.user)
        definitive.current_record_number = "REC001"
        definitive.save(update_fields=["current_record_number"])
        self.assertFalse(definitive.is_temporary_record)


class TemporaryRecordBannerTests(TestCase):
    """R4: the detail page explains the state and links the existing flow."""

    def setUp(self):
        self.user = _create_doctor("bannerdoc")
        self.client = Client()
        self.client.force_login(self.user)
        self.temporary = _temporary_patient(self.user, name="Banner Temp")

    def test_patient_detail_shows_temporary_banner(self):
        """Temporary patients see the warning and the regularization action."""
        response = self.client.get(
            reverse("patients:patient_detail", kwargs={"pk": self.temporary.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Prontuário temporário")
        self.assertContains(response, BANNER_ACTION_TEXT)
        self.assertContains(
            response,
            reverse(
                "patients:quick_record_number_update",
                kwargs={"patient_id": self.temporary.pk},
            ),
        )

    def test_patient_detail_hides_temporary_banner_for_definitive(self):
        """Definitive patients never see the temporary banner."""
        definitive = _create_patient(self.user, name="Banner Definitive")
        _create_record(definitive, "REC001", self.user)
        definitive.current_record_number = "REC001"
        definitive.save(update_fields=["current_record_number"])

        response = self.client.get(
            reverse("patients:patient_detail", kwargs={"pk": definitive.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Prontuário temporário")
        self.assertNotContains(response, BANNER_ACTION_TEXT)
