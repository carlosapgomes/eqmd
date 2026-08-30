"""Slice 003 tests: managed record-number reservation and immutable history."""

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.admin import site
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.tests.helpers import create_navigation_user

from ..admin import PatientRecordNumberAdmin
from ..forms import PatientForm, PatientRecordNumberForm
from ..models import Patient, PatientRecordNumber
from ..services.patient_identity import (
    find_record_number_conflict,
    normalize_record_number,
)

User = get_user_model()

CONSTRAINT_NAME = "unique_patient_record_number_lifetime"
BIRTHDAY = timezone.now().date() - timedelta(days=365 * 30)


def _create_doctor(username: str = "recorddoc"):
    """Create a doctor with full patient record-tracking permissions."""
    user = create_navigation_user(
        username=username,
        email=f"{username}@example.com",
        password="testpassword",
        profession_type=User.MEDICAL_DOCTOR,
    )
    for model in (Patient, PatientRecordNumber):
        content_type = ContentType.objects.get_for_model(model)
        user.user_permissions.add(*Permission.objects.filter(content_type=content_type))
    return user


def _create_patient(user, name: str = "Reservation Patient") -> Patient:
    """Create a plain patient row without a record assignment."""
    return Patient.objects.create(
        name=name,
        birthday=BIRTHDAY,
        created_by=user,
        updated_by=user,
    )


def _create_record(
    patient: Patient, record_number: str, user, is_current: bool = True
) -> PatientRecordNumber:
    """Create a persisted record assignment directly (out-of-band)."""
    return PatientRecordNumber.objects.create(
        patient=patient,
        record_number=record_number,
        is_current=is_current,
        created_by=user,
        updated_by=user,
    )


class RecordNumberServiceTests(TestCase):
    """R1: single-source canonical normalization and all-row lookup."""

    def setUp(self):
        self.user = _create_doctor()
        self.patient = _create_patient(self.user)

    def test_normalize_record_number_trims_external_whitespace_only(self):
        self.assertEqual(normalize_record_number("  REC-001  "), "REC-001")
        self.assertEqual(normalize_record_number("REC-001"), "REC-001")

    def test_conflict_lookup_ignores_case_and_outer_whitespace(self):
        _create_record(self.patient, " REC001 ", self.user)
        self.assertIsNotNone(find_record_number_conflict("rec001"))
        self.assertIsNone(find_record_number_conflict("REC002"))

    def test_conflict_lookup_includes_historical_rows(self):
        self.patient.update_current_record_number("REC001", self.user, "Initial")
        self.patient.update_current_record_number("REC002", self.user, "Transfer")
        self.assertIsNotNone(find_record_number_conflict("rec001"))

    def test_conflict_lookup_includes_soft_deleted_patients(self):
        owner = _create_patient(self.user, name="Soft Deleted Owner")
        _create_record(owner, "REC700", self.user)
        owner.delete(deleted_by=self.user, reason="reservation test")
        self.assertIsNotNone(find_record_number_conflict("rec700"))


class PatientCreationReservationTests(TestCase):
    """R2: initial creation rejects any retained canonical number."""

    def setUp(self):
        self.user = _create_doctor()
        self.owner = _create_patient(self.user, name="Number Owner")

    def _creation_form(self, record_number: str) -> PatientForm:
        return PatientForm(
            {
                "name": "New Patient",
                "birthday": BIRTHDAY.isoformat(),
                "gender": Patient.GenderChoices.NOT_INFORMED,
                "initial_record_number": record_number,
            }
        )

    def test_creation_rejects_current_number_owned_by_another_patient(self):
        _create_record(self.owner, "REC100", self.user)
        form = self._creation_form("REC100")
        self.assertFalse(form.is_valid())
        self.assertIn("initial_record_number", form.errors)
        self.assertEqual(PatientRecordNumber.objects.count(), 1)

    def test_creation_rejects_historical_number(self):
        self.owner.update_current_record_number("REC100", self.user, "Initial")
        self.owner.update_current_record_number("REC200", self.user, "Transfer")
        form = self._creation_form("REC100")
        self.assertFalse(form.is_valid())
        self.assertIn("initial_record_number", form.errors)

    def test_creation_rejects_case_and_whitespace_equivalent(self):
        _create_record(self.owner, " REC100 ", self.user)
        form = self._creation_form("rec100")
        self.assertFalse(form.is_valid())
        self.assertIn("initial_record_number", form.errors)

    def test_soft_deleted_patient_record_stays_reserved(self):
        _create_record(self.owner, "REC100", self.user)
        self.owner.delete(deleted_by=self.user, reason="reservation test")
        form = self._creation_form("REC100")
        self.assertFalse(form.is_valid())
        self.assertIn("initial_record_number", form.errors)


class RecordChangeReservationTests(TestCase):
    """R3/R5: regular and quick change guard, same-patient history."""

    def setUp(self):
        self.user = _create_doctor()
        self.client = Client()
        self.client.force_login(self.user)
        self.owner = _create_patient(self.user, name="Number Owner")
        _create_record(self.owner, "REC500", self.user)
        self.patient = _create_patient(self.user, name="Changing Patient")
        self.patient.update_current_record_number("REC100", self.user, "Initial")

    def test_same_patient_cannot_reactivate_own_historical_number(self):
        self.patient.update_current_record_number("REC200", self.user, "Transfer")
        with self.assertRaises(ValidationError) as ctx:
            self.patient.update_current_record_number("REC100", self.user, "Back")
        self.assertIn("reservado", str(ctx.exception))
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.current_record_number, "REC200")
        self.assertEqual(self.patient.record_numbers.filter(is_current=True).count(), 1)
        self.assertEqual(self.patient.record_numbers.count(), 2)

    def test_regular_change_returns_controlled_form_error_and_keeps_old_current(self):
        url = reverse(
            "patients:record_number_create", kwargs={"patient_id": self.patient.pk}
        )
        data = {
            "record_number": "REC500",
            "change_reason": "Attempted reuse",
            "effective_date": timezone.localtime(timezone.now()).strftime(
                "%Y-%m-%dT%H:%M"
            ),
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "reservado")
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.current_record_number, "REC100")
        self.assertEqual(self.patient.record_numbers.filter(is_current=True).count(), 1)

    def test_quick_change_returns_controlled_message_and_keeps_old_current(self):
        url = reverse(
            "patients:quick_record_number_update",
            kwargs={"patient_id": self.patient.pk},
        )
        response = self.client.post(
            url, {"record_number": "REC500", "change_reason": "Attempted reuse"}
        )
        self.assertRedirects(
            response,
            reverse("patients:patient_detail", kwargs={"pk": self.patient.pk}),
        )
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.current_record_number, "REC100")
        self.assertEqual(self.patient.record_numbers.filter(is_current=True).count(), 1)


class AtomicRecordTransitionTests(TestCase):
    """R4: atomic transition, known-race translation, distinct-number flow."""

    def setUp(self):
        self.user = _create_doctor()
        self.patient = _create_patient(self.user)
        self.patient.update_current_record_number("REC001", self.user, "Initial")

    def test_known_constraint_violation_rolls_back_and_becomes_duplicate_outcome(self):
        violation = IntegrityError(
            f'duplicate key value violates unique constraint "{CONSTRAINT_NAME}"'
        )
        with (
            patch(
                "apps.patients.models.PatientRecordNumber.objects.create",
                side_effect=violation,
            ),
            self.assertRaises(ValidationError) as ctx,
        ):
            self.patient.update_current_record_number("REC002", self.user, "Race")
        self.assertIn("reservado", str(ctx.exception))
        self._assert_previous_state_kept("REC001")

    def test_unrelated_integrity_error_rolls_back_and_is_reraised(self):
        violation = IntegrityError(
            'duplicate key value violates unique constraint "some_other_rule"'
        )
        with (
            patch(
                "apps.patients.models.PatientRecordNumber.objects.create",
                side_effect=violation,
            ),
            self.assertRaises(IntegrityError),
        ):
            self.patient.update_current_record_number("REC002", self.user, "Race")
        self._assert_previous_state_kept("REC001")

    def _assert_previous_state_kept(self, record_number: str) -> None:
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.current_record_number, record_number)
        current = self.patient.record_numbers.filter(is_current=True).first()
        self.assertEqual(current.record_number, record_number)
        self.assertEqual(self.patient.record_numbers.count(), 1)

    def test_distinct_new_number_creates_one_current_row_and_syncs_denormalized(self):
        new_record = self.patient.update_current_record_number(
            "REC002", self.user, "Transfer"
        )
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.current_record_number, "REC002")
        self.assertEqual(new_record.previous_record_number, "REC001")
        self.assertEqual(self.patient.record_numbers.filter(is_current=True).count(), 1)
        self.assertEqual(
            self.patient.record_numbers.filter(is_current=False).count(), 1
        )


class ImmutableAssignmentTests(TestCase):
    """R6: persisted assignment number cannot change; metadata edits remain."""

    def setUp(self):
        self.user = _create_doctor()
        self.patient = _create_patient(self.user)
        self.record = _create_record(self.patient, "REC100", self.user)

    def _edit_data(self, record_number: str, reason: str = "Edited reason") -> dict:
        return {
            "record_number": record_number,
            "change_reason": reason,
            "effective_date": timezone.localtime(self.record.effective_date).strftime(
                "%Y-%m-%dT%H:%M"
            ),
        }

    def test_changing_record_number_on_persisted_assignment_is_invalid(self):
        form = PatientRecordNumberForm(
            instance=self.record, data=self._edit_data("REC200")
        )
        self.assertFalse(form.is_valid())
        self.assertIn("record_number", form.errors)
        self.assertIn("alterado", str(form.errors["record_number"]))
        self.record.refresh_from_db()
        self.assertEqual(self.record.record_number, "REC100")

    def test_metadata_edit_on_persisted_assignment_is_allowed(self):
        form = PatientRecordNumberForm(
            instance=self.record, data=self._edit_data("REC100")
        )
        self.assertTrue(form.is_valid())


class DeletionReservationTests(TestCase):
    """R7: ordinary and admin deletion are rejected without data loss."""

    def setUp(self):
        self.user = _create_doctor()
        self.client = Client()
        self.client.force_login(self.user)
        self.patient = _create_patient(self.user)
        self.record = _create_record(
            self.patient, "REC-HIST", self.user, is_current=False
        )

    def test_delete_view_preserves_the_row(self):
        url = reverse("patients:record_number_delete", kwargs={"pk": self.record.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Confirmar Exclusão")
        response = self.client.post(url)
        self.assertRedirects(
            response,
            reverse("patients:patient_detail", kwargs={"pk": self.patient.pk}),
        )
        self.assertTrue(PatientRecordNumber.objects.filter(pk=self.record.pk).exists())
        self.record.refresh_from_db()
        self.assertEqual(self.record.record_number, "REC-HIST")

    def test_admin_reports_no_delete_permission(self):
        admin = PatientRecordNumberAdmin(PatientRecordNumber, site)
        request = SimpleNamespace(user=self.user)
        self.assertFalse(admin.has_delete_permission(request, obj=self.record))
        self.assertFalse(admin.has_delete_permission(request))

    def test_admin_marks_record_number_readonly_on_persisted_assignment(self):
        admin = PatientRecordNumberAdmin(PatientRecordNumber, site)
        request = SimpleNamespace(user=self.user)
        readonly = admin.get_readonly_fields(request, obj=self.record)
        self.assertIn("record_number", readonly)
        self.assertNotIn("record_number", admin.get_readonly_fields(request))


class RecordChangePermissionTests(TestCase):
    """R14: existing authentication and permissions remain enforced."""

    def setUp(self):
        self.user = _create_doctor()
        self.client = Client()
        self.patient = _create_patient(self.user)
        self.patient.update_current_record_number("REC100", self.user, "Initial")

    def _quick_post(self):
        url = reverse(
            "patients:quick_record_number_update",
            kwargs={"patient_id": self.patient.pk},
        )
        return self.client.post(
            url, {"record_number": "REC300", "change_reason": "test"}
        )

    def test_anonymous_user_is_redirected_to_login(self):
        response = self._quick_post()
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login", response.url)

    def test_user_without_permission_gets_403(self):
        plain = create_navigation_user(
            username="plaindoc",
            email="plaindoc@example.com",
            password="testpassword",
            profession_type=User.MEDICAL_DOCTOR,
        )
        self.client.force_login(plain)
        response = self._quick_post()
        self.assertEqual(response.status_code, 403)
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.current_record_number, "REC100")
