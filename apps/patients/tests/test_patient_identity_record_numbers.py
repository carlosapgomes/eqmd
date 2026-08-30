"""Record-number reservation tests (slices 003 and 004)."""

import importlib.util
import threading
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

from django.apps import apps as global_apps
from django.contrib.admin import site
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import (
    IntegrityError,
    close_old_connections,
    connection,
    transaction,
)
from django.db.models import UniqueConstraint
from django.db.models.functions import Lower, Trim
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import EqmdCustomUser
from apps.accounts.tests.helpers import create_navigation_user

from ..admin import PatientRecordNumberAdmin
from ..forms import PatientForm, PatientRecordNumberForm
from ..models import Patient, PatientRecordNumber
from ..services.patient_identity import (
    find_record_number_conflict,
    is_record_constraint_violation,
    normalize_record_number,
)

CONSTRAINT_NAME = "unique_patient_record_number_lifetime"
MIGRATION_FILENAME = "0002_patient_record_number_lifetime_unique.py"
BIRTHDAY = timezone.now().date() - timedelta(days=365 * 30)


def _create_doctor(username: str = "recorddoc"):
    """Create a doctor with full patient record-tracking permissions."""
    user = create_navigation_user(
        username=username,
        email=f"{username}@example.com",
        password="testpassword",
        profession_type=EqmdCustomUser.MEDICAL_DOCTOR,
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


def _load_record_constraint_migration() -> ModuleType:
    """Load the 0002 migration module via importlib (not registered)."""
    migration_path = (
        Path(__file__).resolve().parents[1] / "migrations" / MIGRATION_FILENAME
    )
    spec = importlib.util.spec_from_file_location(
        "patients_0002_preflight_probe", migration_path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"unreadable migration module: {migration_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@dataclass(frozen=True)
class _ContestedInsertRace:
    """Shared context and outcome sink for one contested-insert race."""

    user: object
    contested_number: str
    barrier: threading.Barrier
    lock: threading.Lock
    outcomes: list[str]


def _attempt_contested_insert(patient: Patient, race: _ContestedInsertRace) -> None:
    """Insert the contested number from this thread's own connection."""
    close_old_connections()
    try:
        race.barrier.wait()
        _create_record(patient, race.contested_number, race.user)
    except IntegrityError as error:
        outcome = (
            "duplicate"
            if is_record_constraint_violation(error)
            else "unknown-integrity-error"
        )
    else:
        outcome = "created"
    finally:
        close_old_connections()
    with race.lock:
        race.outcomes.append(outcome)


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
            profession_type=EqmdCustomUser.MEDICAL_DOCTOR,
        )
        self.client.force_login(plain)
        response = self._quick_post()
        self.assertEqual(response.status_code, 403)
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.current_record_number, "REC100")


class LifetimeConstraintDatabaseTests(TestCase):
    """Slice 004 R1/R2: the database reserves canonical numbers for ORM writes."""

    def setUp(self):
        self.user = _create_doctor()
        self.patient = _create_patient(self.user, name="Holder Alpha")
        self.other = _create_patient(self.user, name="Holder Beta")

    def test_direct_orm_duplicate_across_patients_is_rejected(self):
        _create_record(self.patient, "REC800", self.user)
        with (
            self.assertRaises(IntegrityError) as ctx,
            transaction.atomic(),
        ):
            _create_record(self.other, "REC800", self.user)
        self.assertIn(CONSTRAINT_NAME, str(ctx.exception))

    def test_case_and_whitespace_equivalents_are_rejected(self):
        _create_record(self.patient, " REC800 ", self.user)
        with self.assertRaises(IntegrityError), transaction.atomic():
            _create_record(self.other, "rec800", self.user)

    def test_same_patient_repeat_is_rejected(self):
        self.patient.update_current_record_number("REC810", self.user, "Initial")
        with self.assertRaises(IntegrityError), transaction.atomic():
            _create_record(self.patient, "REC810", self.user)

    def test_same_patient_historical_repeat_is_rejected(self):
        self.patient.update_current_record_number("REC820", self.user, "Initial")
        self.patient.update_current_record_number("REC821", self.user, "Transfer")
        with self.assertRaises(IntegrityError), transaction.atomic():
            _create_record(self.patient, "rec820", self.user, is_current=False)

    def test_soft_deleted_owner_keeps_number_reserved(self):
        _create_record(self.patient, "REC830", self.user)
        self.patient.delete(deleted_by=self.user, reason="constraint test")
        with self.assertRaises(IntegrityError), transaction.atomic():
            _create_record(self.other, "REC830", self.user)

    def test_distinct_numbers_remain_allowed(self):
        _create_record(self.patient, "REC840", self.user)
        _create_record(self.other, "REC841", self.user)
        self.assertEqual(PatientRecordNumber.objects.count(), 2)


class RecordConstraintStateTests(TestCase):
    """Slice 004 R1/R4: model state and applied schema carry both constraints."""

    def test_model_state_keeps_old_and_adds_lifetime_constraint(self):
        constraints = PatientRecordNumber._meta.constraints
        names = {constraint.name for constraint in constraints}
        self.assertIn("unique_current_record_per_patient", names)
        lifetime = next(
            (
                constraint
                for constraint in constraints
                if constraint.name == CONSTRAINT_NAME
            ),
            None,
        )
        self.assertIsNotNone(lifetime)
        assert isinstance(lifetime, UniqueConstraint)
        self.assertIsNone(lifetime.condition)
        self.assertFalse(lifetime.fields)
        expressions = " ".join(str(expression) for expression in lifetime.expressions)
        self.assertIn("Lower", expressions)
        self.assertIn("Trim", expressions)
        self.assertIn("record_number", expressions)

    def test_applied_database_has_lifetime_unique_index(self):
        with connection.cursor() as cursor:
            constraints = connection.introspection.get_constraints(
                cursor, PatientRecordNumber._meta.db_table
            )
        lifetime = constraints.get(CONSTRAINT_NAME)
        self.assertIsNotNone(lifetime)
        assert lifetime is not None
        self.assertTrue(lifetime["unique"])


class ConcurrentAssignmentTests(TransactionTestCase):
    """Slice 004 R5: two real transactions produce exactly one winner."""

    def test_concurrent_same_canonical_number_has_exactly_one_winner(self):
        user = _create_doctor()
        patients = [
            _create_patient(user, name="Concurrent Alpha"),
            _create_patient(user, name="Concurrent Beta"),
        ]
        race = _ContestedInsertRace(
            user=user,
            contested_number="REC990",
            barrier=threading.Barrier(len(patients), timeout=10),
            lock=threading.Lock(),
            outcomes=[],
        )
        threads = [
            threading.Thread(target=_attempt_contested_insert, args=(patient, race))
            for patient in patients
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(sorted(race.outcomes), ["created", "duplicate"])
        self._assert_single_canonical_row(race.contested_number)

    def _assert_single_canonical_row(self, contested: str) -> None:
        winner_count = (
            PatientRecordNumber.objects.annotate(
                canonical_number=Lower(Trim("record_number"))
            )
            .filter(canonical_number=contested.lower())
            .count()
        )
        self.assertEqual(winner_count, 1)


class RecordConstraintMigrationTests(TestCase):
    """Slice 004 R3/R4: clean preflight permits the constraint, rows intact."""

    def test_clean_preflight_passes_and_keeps_rows_unchanged(self):
        user = _create_doctor()
        patient = _create_patient(user, name="Clean Preflight Holder")
        _create_record(patient, "REC950", user)
        migration = _load_record_constraint_migration()

        migration.ensure_no_canonical_collisions(
            global_apps, connection.schema_editor()
        )

        self.assertEqual(
            PatientRecordNumber.objects.filter(record_number="REC950").count(),
            1,
        )


class DirtyRecordConstraintMigrationTests(TransactionTestCase):
    """Slice 004 R3/R6: colliding data aborts preflight, aggregates only."""

    def test_dirty_preflight_aborts_before_schema_change(self):
        user = _create_doctor()
        patient_a = _create_patient(user, name="Holder Gamma")
        patient_b = _create_patient(user, name="Holder Delta")
        self._index_was_present = False
        self._drop_lifetime_index()
        self.addCleanup(self._restore_clean_state)
        first = _create_record(patient_a, "SYN-777", user)
        second = _create_record(patient_b, " syn-777 ", user)
        migration = _load_record_constraint_migration()

        with self.assertRaises(RuntimeError) as ctx:
            migration.ensure_no_canonical_collisions(
                global_apps, connection.schema_editor()
            )

        self._assert_aggregate_only_abort(ctx.exception, patient_a, patient_b)
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(first.record_number, "SYN-777")
        self.assertEqual(second.record_number, " syn-777 ")
        self.assertEqual(self._colliding_row_count(), 2)
        self.assertFalse(self._lifetime_index_exists())

    def _assert_aggregate_only_abort(self, error, patient_a, patient_b) -> None:
        """The abort message carries aggregate counts and zero identifiers."""
        message = str(error)
        self.assertIn("1 canonical record-number collision group(s)", message)
        self.assertIn("involving 2 row(s)", message)
        for forbidden in (
            "syn-777",
            str(patient_a.pk),
            str(patient_b.pk),
            patient_a.name,
            patient_b.name,
        ):
            self.assertNotIn(forbidden.lower(), message.lower())

    def _drop_lifetime_index(self) -> None:
        self._index_was_present = self._lifetime_index_exists()
        if self._index_was_present:
            with connection.cursor() as cursor:
                cursor.execute(f'DROP INDEX "{CONSTRAINT_NAME}"')

    def _restore_clean_state(self) -> None:
        """Remove the synthetic collision rows, then re-create the index."""
        PatientRecordNumber.objects.filter(
            record_number__in=["SYN-777", " syn-777 "]
        ).delete()
        if not self._index_was_present:
            return
        with connection.cursor() as cursor:
            cursor.execute(
                f'CREATE UNIQUE INDEX "{CONSTRAINT_NAME}" '
                f'ON "{PatientRecordNumber._meta.db_table}" '
                "((LOWER(TRIM(record_number))))"
            )

    def _colliding_row_count(self) -> int:
        return (
            PatientRecordNumber.objects.annotate(
                canonical_number=Lower(Trim("record_number"))
            )
            .filter(canonical_number="syn-777")
            .count()
        )

    def _lifetime_index_exists(self) -> bool:
        with connection.cursor() as cursor:
            constraints = connection.introspection.get_constraints(
                cursor, PatientRecordNumber._meta.db_table
            )
        return CONSTRAINT_NAME in constraints
