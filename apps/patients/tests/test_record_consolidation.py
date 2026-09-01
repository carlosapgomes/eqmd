"""Audited record-number consolidation tests on synthetic data only."""

import json
import os
import uuid
from base64 import urlsafe_b64encode
from datetime import date
from io import StringIO
from tempfile import NamedTemporaryFile

from django.core.management import CommandError, call_command
from django.db import connection, transaction
from django.test import SimpleTestCase, TestCase

from apps.accounts.models import EqmdCustomUser
from apps.accounts.tests.helpers import create_navigation_user

from ..models import Patient, PatientRecordNumber
from ..services.patient_identity import (
    find_record_number_collision_groups,
    summarize_record_number_collisions,
)

CONSTRAINT_NAME = "unique_patient_record_number_lifetime"
PLAN_REF = "consol-01"
RATIONALE = "Número atribuído ao paciente errado no cadastro"


def _consolidation_service():
    from ..services import patient_record_consolidation as service

    return service


def _create_operator(username: str) -> EqmdCustomUser:
    return create_navigation_user(
        username=username,
        email=f"{username}@example.com",
        password="testpassword",
        profession_type=EqmdCustomUser.MEDICAL_DOCTOR,
    )


def _create_patient(user: EqmdCustomUser, name: str) -> Patient:
    """Create a plain patient row without a record assignment."""
    return Patient.objects.create(
        name=name, birthday=date(1995, 3, 10), created_by=user, updated_by=user
    )


def _create_record(
    patient: Patient, record_number: str, user: EqmdCustomUser, is_current: bool = True
) -> PatientRecordNumber:
    return PatientRecordNumber.objects.create(
        patient=patient,
        record_number=record_number,
        is_current=is_current,
        created_by=user,
        updated_by=user,
    )


def _drop_lifetime_index() -> None:
    """Drop the slice-004 index so synthetic collisions can exist (rolled back)."""
    with connection.cursor() as cursor:
        table = PatientRecordNumber._meta.db_table
        if CONSTRAINT_NAME in connection.introspection.get_constraints(cursor, table):
            cursor.execute(f'DROP INDEX "{CONSTRAINT_NAME}"')


def _create_collision_rows(
    user: EqmdCustomUser, number: str, error_specs: list[bool]
) -> list[PatientRecordNumber]:
    """Keeper row plus erroneous rows all sharing one canonical number."""
    _drop_lifetime_index()
    rows = [_create_record(_create_patient(user, f"Titular {number}"), number, user)]
    for index, is_current in enumerate(error_specs):
        name = f"Errôneo {index} {number}"
        value = number.lower() if index == 0 else number
        rows.append(
            _create_record(
                _create_patient(user, name), value, user, is_current=is_current
            )
        )
    return rows


def _create_collision_pair(
    user: EqmdCustomUser, number: str, error_is_current: bool
) -> tuple[PatientRecordNumber, PatientRecordNumber]:
    """Create two patients sharing one canonical number (dirty data)."""
    keeper, error_row = _create_collision_rows(user, number, [error_is_current])
    return keeper, error_row


def _void_action(error_row) -> dict:
    return {"assignment": str(error_row.pk), "action": "void", "rationale": RATIONALE}


def _renumber_action(error_row, new_number: str) -> dict:
    action = _void_action(error_row)
    action["action"] = "renumber"
    action["new_record_number"] = new_number
    return action


def _group(canonical: str, keep_row, actions: list[dict]) -> dict:
    return {"canonical": canonical, "keep": str(keep_row.pk), "actions": actions}


def _plan(groups: list[dict]) -> dict:
    return {"plan_ref": PLAN_REF, "groups": groups}


def _void_plan(canonical: str, keep_row, error_row) -> dict:
    return _plan([_group(canonical, keep_row, [_void_action(error_row)])])


def _two_group_plan(group_a: dict, group_b: dict) -> dict:
    return _plan([group_a, group_b])


def _marker_for(canonical: str, row) -> str:
    """Amended D2 marker: verbatim original, plan reference, per-row id."""
    token = urlsafe_b64encode(row.pk.bytes).decode("ascii").rstrip("=")
    return f"{canonical}::voided::{PLAN_REF}:{token}"


# Packed string avoids a one-per-line list under ruff format (SIM905 waived).
_SNAPSHOT_FIELDS = (  # noqa: SIM905
    "id patient_id record_number is_current previous_record_number "
    "change_reason effective_date created_by_id updated_by_id "
    "created_at updated_at"
).split()


def _assignment_snapshot() -> list[tuple]:
    rows = PatientRecordNumber.objects.order_by("id").values_list(*_SNAPSHOT_FIELDS)
    return list(rows) + list(
        Patient.objects.order_by("id").values_list("id", "current_record_number")
    )


def _run_command(**options) -> str:
    out = StringIO()
    call_command("consolidate_record_numbers", stdout=out, **options)
    return out.getvalue()


class PlanFileMixin(SimpleTestCase):
    def write_plan_file(self, payload: dict) -> str:
        with NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump(payload, handle)
            self.addCleanup(os.remove, handle.name)
        return handle.name

    def run_plan(self, payload: dict, operator=None, **options) -> str:
        options["plan"] = self.write_plan_file(payload)
        if operator is not None:
            options["user"] = operator.username
        return _run_command(**options)

    def assertRunRefused(self, payload, operator, message: str, **options) -> None:
        """The plan is refused with the expected message and mutates nothing."""
        before = _assignment_snapshot()
        with self.assertRaisesMessage(CommandError, message):
            self.run_plan(payload, operator, **options)
        self.assertEqual(_assignment_snapshot(), before)

    def execute_service_plan(self, payload: dict, operator) -> None:
        service = _consolidation_service()
        plan = service.parse_consolidation_plan(json.dumps(payload))
        with transaction.atomic():
            service.execute_consolidation_plan(plan, operator)


class CollisionDiscoveryTests(TestCase):
    """R1: canonical grouping, aggregate counts, and id-only detail."""

    def setUp(self):
        self.operator = _create_operator("discovery-op")

    def test_discovery_aggregate_reports_groups_and_involved_rows(self):
        _create_collision_pair(self.operator, "REC100", error_is_current=False)
        _create_collision_pair(self.operator, "REC300", error_is_current=True)
        summary = summarize_record_number_collisions()
        self.assertEqual((summary.group_count, summary.involved_rows), (2, 4))

    def test_discovery_groups_case_and_whitespace_equivalents(self):
        _drop_lifetime_index()
        holder = _create_patient(self.operator, "Titular Espaços")
        duplicate = _create_patient(self.operator, "Duplicado Caixa")
        _create_record(holder, " REC100 ", self.operator)
        _create_record(duplicate, "rec100", self.operator)
        groups = find_record_number_collision_groups()
        self.assertEqual([group.canonical for group in groups], ["rec100"])
        self.assertEqual(groups[0].row_count, 2)

    def test_discovery_detail_exposes_ids_only(self):
        keep_row, error_row = _create_collision_pair(
            self.operator, "REC100", error_is_current=False
        )
        group = find_record_number_collision_groups()[0]
        self.assertEqual(group.canonical, "rec100")
        ids = [str(keep_row.pk), str(error_row.pk)]
        self.assertCountEqual(map(str, group.assignment_ids), ids)
        self.assertEqual((len(group.patient_ids), group.row_count), (2, 2))

    def test_no_collisions_yield_empty_discovery(self):
        holder = _create_patient(self.operator, "Solitário")
        _create_record(holder, "REC001", self.operator)
        self.assertEqual(find_record_number_collision_groups(), [])
        self.assertEqual(summarize_record_number_collisions().group_count, 0)


class ConsolidationCommandAuditTests(PlanFileMixin, TestCase):
    """R3 output discipline: aggregate by default, detail only on flag."""

    def setUp(self):
        self.operator = _create_operator("audit-op")
        self.keep_row, self.error_row = _create_collision_pair(
            self.operator, "REC100", error_is_current=False
        )

    def test_bare_command_prints_aggregate_audit_without_detail(self):
        output = _run_command()
        self.assertIn(
            "1 canonical record-number collision group(s) involving 2 row(s)", output
        )
        self.assertNotIn("rec100", output)
        self.assertNotIn(str(self.keep_row.pk), output)

    def test_show_records_prints_per_group_id_detail(self):
        output = _run_command(show_records=True)
        self.assertIn("rec100", output)
        self.assertIn(str(self.keep_row.pk), output)
        self.assertIn(str(self.error_row.patient_id), output)

    def test_command_output_is_free_of_names_cpf_and_cns(self):
        Patient.objects.filter(
            pk__in=[self.keep_row.patient_id, self.error_row.patient_id]
        ).update(
            name="Maria Confidencial de Souza",
            fiscal_number="52998224725",
            healthcard_number="92897695123",
        )
        plan = _void_plan("rec100", self.keep_row, self.error_row)
        outputs = [
            _run_command(),
            _run_command(show_records=True),
            self.run_plan(plan, self.operator),
        ]
        for output in outputs:
            for secret in ("Maria Confidencial de Souza", "52998224725", "92897695123"):
                self.assertNotIn(secret, output)


class VoidConsolidationTests(PlanFileMixin, TestCase):
    """R2 void semantics: verbatim marker, recorded audit, row retained."""

    def setUp(self):
        self.operator = _create_operator("void-op")
        self.keep_row, self.error_row = _create_collision_pair(
            self.operator, "REC100", error_is_current=False
        )
        self.plan = _void_plan("rec100", self.keep_row, self.error_row)

    def test_void_marker_preserves_original_verbatim_with_plan_reference(self):
        self.execute_service_plan(self.plan, self.operator)
        self.error_row.refresh_from_db()
        marker = _marker_for("rec100", self.error_row)
        self.assertEqual(self.error_row.record_number, marker)

    def test_void_records_rationale_operator_and_retains_row(self):
        effective_date = self.error_row.effective_date
        self.execute_service_plan(self.plan, self.operator)
        self.error_row.refresh_from_db()
        change = f"{RATIONALE} [plan: {PLAN_REF}]"
        self.assertEqual(self.error_row.change_reason, change)
        self.assertEqual(self.error_row.updated_by, self.operator)
        self.assertFalse(self.error_row.is_current)
        self.assertEqual(self.error_row.effective_date, effective_date)
        self.assertTrue(PatientRecordNumber.objects.filter(pk=self.error_row.pk))

    def test_void_leaves_the_decided_keep_row_untouched(self):
        self.execute_service_plan(self.plan, self.operator)
        self.keep_row.refresh_from_db()
        self.assertEqual(self.keep_row.record_number, "REC100")
        self.assertTrue(self.keep_row.is_current)
        self.assertEqual(self.keep_row.change_reason, "")


class RenumberConsolidationTests(PlanFileMixin, TestCase):
    """R2 renumber semantics: append flow plus void of the deactivated row."""

    def setUp(self):
        self.operator = _create_operator("renumber-op")
        self.keep_row, self.error_row = _create_collision_pair(
            self.operator, "REC100", error_is_current=True
        )

    def _renumber_payload(self, new_number: str) -> dict:
        action = [_renumber_action(self.error_row, new_number)]
        return _plan([_group("rec100", self.keep_row, action)])

    def test_renumber_appends_new_current_and_voids_old_row(self):
        self.execute_service_plan(self._renumber_payload("REC900"), self.operator)
        self.error_row.refresh_from_db()
        new_row = PatientRecordNumber.objects.get(record_number="REC900")
        self.assertTrue(new_row.is_current)
        self.assertEqual(new_row.previous_record_number, "rec100")
        self.assertFalse(self.error_row.is_current)
        marker = _marker_for("rec100", self.error_row)
        self.assertEqual(self.error_row.record_number, marker)

    def test_renumber_syncs_denormalized_field_and_records_audit(self):
        self.execute_service_plan(self._renumber_payload("REC900"), self.operator)
        new_row = PatientRecordNumber.objects.get(record_number="REC900")
        self.error_row.patient.refresh_from_db()
        self.assertEqual(self.error_row.patient.current_record_number, "REC900")
        self.assertEqual(new_row.created_by, self.operator)
        self.assertEqual(new_row.change_reason, f"{RATIONALE} [plan: {PLAN_REF}]")


class PlanValidationRefusalTests(PlanFileMixin, TestCase):
    """R3 validation: unknown, stale, incomplete, and routing refusals."""

    def setUp(self):
        self.operator = _create_operator("refusal-op")
        self.keep_row, self.error_row = _create_collision_pair(
            self.operator, "REC100", error_is_current=False
        )

    def test_unknown_canonical_group_is_refused_without_mutation(self):
        plan = _void_plan("rec100", self.keep_row, self.error_row)
        plan["groups"][0]["canonical"] = "rec999"
        self.assertRunRefused(plan, self.operator, "have no live collision group")

    def test_incomplete_coverage_is_refused_without_mutation(self):
        _create_collision_pair(self.operator, "REC300", False)
        plan = _void_plan("rec100", self.keep_row, self.error_row)
        self.assertRunRefused(plan, self.operator, "are missing from the plan")

    def test_stale_assignment_reference_is_refused_without_mutation(self):
        plan = _void_plan("rec100", self.keep_row, self.error_row)
        plan["groups"][0]["actions"][0]["assignment"] = str(uuid.uuid4())
        self.assertRunRefused(plan, self.operator, "no longer matches live group")

    def test_void_on_current_row_is_refused(self):
        current_keep, current_error = _create_collision_pair(
            self.operator, "REC500", error_is_current=True
        )
        plan = _two_group_plan(
            _group("rec100", self.keep_row, [_void_action(self.error_row)]),
            _group("rec500", current_keep, [_void_action(current_error)]),
        )
        self.assertRunRefused(plan, self.operator, "is the patient's current number")

    def test_renumber_on_historical_row_is_refused(self):
        action = [_renumber_action(self.error_row, "REC900")]
        plan = _plan([_group("rec100", self.keep_row, action)])
        self.assertRunRefused(plan, self.operator, "is historical")

    def test_renumber_to_placeholder_target_is_refused(self):
        """R3: plan renumbering to a junk number is refused at parse time"""
        current_keep, current_error = _create_collision_pair(
            self.operator, "REC600", error_is_current=True
        )
        action = [_renumber_action(current_error, "---")]
        plan = _two_group_plan(
            _group("rec100", self.keep_row, [_void_action(self.error_row)]),
            _group("rec600", current_keep, action),
        )
        self.assertRunRefused(
            plan, self.operator, "targets an invalid record number"
        )

    def test_renumber_to_placeholder_is_refused_even_in_single_group_plan(self):
        """R3: refusal is independent of plan size; assignment is named"""
        current_keep, current_error = _create_collision_pair(
            self.operator, "REC700", error_is_current=True
        )
        action = [_renumber_action(current_error, "___")]
        plan = _plan([_group("rec700", current_keep, action)])
        self.assertRunRefused(
            plan, self.operator, f"assignment {current_error.pk}"
        )

    def test_execute_requires_an_explicit_operator_user(self):
        plan = _void_plan("rec100", self.keep_row, self.error_row)
        self.assertRunRefused(plan, None, "--user", execute=True)


class PostCheckRollbackTests(PlanFileMixin, TestCase):
    """R3/R4: residual collisions roll the whole plan back."""

    def test_residual_collision_rolls_back_applied_actions(self):
        operator = _create_operator("rollback-op")
        keep_a, error_a = _create_collision_pair(operator, "REC100", False)
        _create_collision_pair(operator, "REC300", False)
        before = _assignment_snapshot()
        with self.assertRaises(_consolidation_service().ResidualCollisionError):
            self.execute_service_plan(_void_plan("rec100", keep_a, error_a), operator)
        self.assertEqual(_assignment_snapshot(), before)


class ExecuteCommandTests(PlanFileMixin, TestCase):
    """R3 --execute end-to-end with the zero-collision post-check."""

    def test_execute_resolves_every_group_and_reports_zero(self):
        operator = _create_operator("execute-op")
        keep_a, error_a = _create_collision_pair(operator, "REC100", False)
        keep_b, error_b = _create_collision_pair(operator, "REC300", False)
        plan = _two_group_plan(
            _group("rec100", keep_a, [_void_action(error_a)]),
            _group("rec300", keep_b, [_void_action(error_b)]),
        )
        output = self.run_plan(plan, operator, execute=True)
        self.assertIn(f"executed plan '{PLAN_REF}'", output)
        self.assertIn("0 collision group(s) remaining", output)
        summary = summarize_record_number_collisions()
        self.assertEqual((summary.group_count, summary.involved_rows), (0, 0))
        error_a.refresh_from_db()
        self.assertEqual(error_a.record_number, _marker_for("rec100", error_a))

    def test_execute_three_row_group_yields_distinct_per_row_markers(self):
        operator = _create_operator("trio-op")
        keeper, historical, current_error = _create_collision_rows(
            operator, "REC700", [False, True]
        )
        actions = [_void_action(historical), _renumber_action(current_error, "REC910")]
        plan = _plan([_group("rec700", keeper, actions)])
        output = self.run_plan(plan, operator, execute=True)
        self.assertIn("0 collision group(s) remaining", output)
        summary = summarize_record_number_collisions()
        self.assertEqual((summary.group_count, summary.involved_rows), (0, 0))
        historical.refresh_from_db()
        current_error.refresh_from_db()
        markers = [historical.record_number, current_error.record_number]
        self.assertNotEqual(markers[0], markers[1])
        self.assertIn("rec700", markers[0])
        self.assertIn("REC700", markers[1])
        for marker in markers:
            self.assertIn(PLAN_REF, marker)

    def test_execute_supports_eighteen_char_originals_via_widened_column(self):
        operator = _create_operator("wide-op")
        keeper, stale = _create_collision_rows(operator, "SINT-2026-0000ABCD", [False])
        plan = _void_plan("sint-2026-0000abcd", keeper, stale)
        self.run_plan(plan, operator, execute=True)
        stale.refresh_from_db()
        self.assertEqual(summarize_record_number_collisions().group_count, 0)
        self.assertTrue(stale.record_number.startswith("sint-2026-0000abcd::voided::"))
        self.assertIn(PLAN_REF, stale.record_number)


class DryRunCommandTests(PlanFileMixin, TestCase):
    """R3 dry-run default: planned work attempted, byte-identical state."""

    def test_dry_run_leaves_the_database_byte_identical(self):
        operator = _create_operator("dryrun-op")
        keep_a, error_a = _create_collision_pair(operator, "REC100", False)
        keep_b, error_b = _create_collision_pair(operator, "REC300", True)
        plan = _two_group_plan(
            _group("rec100", keep_a, [_void_action(error_a)]),
            _group("rec300", keep_b, [_renumber_action(error_b, "REC900")]),
        )
        before = _assignment_snapshot()
        output = self.run_plan(plan, operator, dry_run=True)
        self.assertIn(f"DRY RUN plan '{PLAN_REF}'", output)
        self.assertIn("2 action(s)", output)
        self.assertIn("would leave 0 collision group(s) involving 0 row(s)", output)
        self.assertEqual(_assignment_snapshot(), before)
        self.run_plan(plan, operator)
        self.assertEqual(_assignment_snapshot(), before)
