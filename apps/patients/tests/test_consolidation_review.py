"""Operator clinical review helper for collision groups (slice 03).

Covers --show-patients (name, birthday, current flag, likely-same-person
marker; never CPF/CNS) and --emit-skeleton (decision scaffold with the
same clinical context, fillable into a valid plan).
"""

import json
import os
from io import StringIO
from tempfile import NamedTemporaryFile

from django.core.management import call_command
from django.test import TestCase

from apps.patients.services.patient_record_consolidation import (
    build_collision_review,
    parse_consolidation_plan,
    skeleton_document,
)

from .test_record_consolidation import (
    _create_operator,
    _create_patient,
    _create_record,
    _drop_lifetime_index,
)

SAME_NAME = "Paciente Duplicado Silva"
OTHER_NAME = "Outro Paciente Souza"


def _run_command(**options) -> str:
    """Run the consolidation command capturing stdout."""
    out = StringIO()
    call_command("consolidate_record_numbers", stdout=out, **options)
    return out.getvalue()


class CollisionReviewTests(TestCase):
    """--show-patients: clinical context on the operator console only."""

    def setUp(self):
        self.operator = _create_operator("review-op")
        _drop_lifetime_index()
        self.same_a = _create_patient(self.operator, SAME_NAME)
        self.same_b = _create_patient(self.operator, SAME_NAME)
        self.other = _create_patient(self.operator, OTHER_NAME)
        _create_record(self.same_a, "REC100", self.operator)
        _create_record(self.same_b, "rec100", self.operator, is_current=False)
        _create_record(self.other, "REC300", self.operator)
        _create_record(
            _create_patient(self.operator, "Terceiro Paciente Lima"),
            "rec300",
            self.operator,
            is_current=False,
        )

    def test_show_patients_prints_name_and_birthday_per_row(self):
        output = _run_command(show_patients=True)
        self.assertIn(SAME_NAME, output)
        self.assertIn(OTHER_NAME, output)
        self.assertIn("REC100", output)
        self.assertIn("nascimento=", output)
        self.assertIn("CORRENTE", output)
        self.assertIn("histórico", output)

    def test_show_patients_marks_likely_same_person_rows(self):
        output = _run_command(show_patients=True)
        self.assertIn("provável mesma pessoa", output)
        review = build_collision_review()
        by_canonical = {group.canonical: group for group in review}
        rec100 = by_canonical["rec100"]
        self.assertTrue(all(row.same_person_likely for row in rec100.rows))
        rec300 = by_canonical["rec300"]
        self.assertFalse(any(row.same_person_likely for row in rec300.rows))

    def test_show_patients_never_prints_cpf_or_cns(self):
        from apps.patients.models import Patient

        Patient.objects.filter(pk=self.same_a.pk).update(
            fiscal_number="52998224725", healthcard_number="92897695123"
        )
        output = _run_command(show_patients=True)
        self.assertNotIn("52998224725", output)
        self.assertNotIn("92897695123", output)

    def test_default_output_still_hides_clinical_detail(self):
        output = _run_command()
        self.assertNotIn(SAME_NAME, output)
        self.assertNotIn("nascimento=", output)


class SkeletonTests(TestCase):
    """--emit-skeleton: decision scaffold, fillable into a valid plan."""

    def setUp(self):
        self.operator = _create_operator("skeleton-op")
        _drop_lifetime_index()
        keeper = _create_patient(self.operator, "Guardiã Do Numero")
        stale = _create_patient(self.operator, "Repetida Do Numero")
        self.keeper_row = _create_record(keeper, "REC700", self.operator)
        self.stale_row = _create_record(
            stale, "rec700", self.operator, is_current=False
        )

    def _emit(self) -> dict:
        with NamedTemporaryFile("r", suffix=".json", delete=False) as handle:
            path = handle.name
        self.addCleanup(os.remove, path)
        output = _run_command(emit_skeleton=path)
        self.assertIn(path, output)
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)

    def test_skeleton_carries_context_and_empty_decisions(self):
        document = self._emit()
        self.assertEqual(len(document["groups"]), 1)
        group = document["groups"][0]
        self.assertEqual(group["canonical"], "rec700")
        self.assertEqual(group["keep"], "PREENCHA")
        self.assertEqual(group["actions"], [])
        rows = group["context"]["rows"]
        self.assertEqual(len(rows), 2)
        by_assignment = {row["assignment"]: row for row in rows}
        self.assertIn(str(self.keeper_row.pk), by_assignment)
        self.assertIn(str(self.stale_row.pk), by_assignment)
        row = by_assignment[str(self.stale_row.pk)]
        self.assertEqual(row["record_number"], "rec700")
        self.assertFalse(row["is_current"])
        self.assertIn("Repetida", row["name"])
        self.assertIn("birthday", row)

    def test_filled_skeleton_parses_as_a_plan(self):
        document = self._emit()
        document["plan_ref"] = "consol-03"
        group = document["groups"][0]
        group["keep"] = str(self.keeper_row.pk)
        group["actions"] = [
            {
                "assignment": str(self.stale_row.pk),
                "action": "void",
                "rationale": "lançamento duplicado do mesmo número",
            }
        ]
        plan = parse_consolidation_plan(json.dumps(document))
        self.assertEqual(plan.groups[0].keep_id, self.keeper_row.pk)

    def test_skeleton_document_shape_is_stable(self):
        document = skeleton_document(build_collision_review())
        self.assertEqual(document["plan_ref"], "PREENCHA-REF")
        for group in document["groups"]:
            self.assertIn("keep", group)
            self.assertIn("actions", group)
            self.assertIn("context", group)


class PrefillTests(TestCase):
    """--prefill: same-person groups drafted under the owner's criterion."""

    def setUp(self):
        self.operator = _create_operator("prefill-op")
        _drop_lifetime_index()
        self.earlier = _create_patient(self.operator, SAME_NAME)
        self.later = _create_patient(self.operator, SAME_NAME)
        from apps.patients.models import Patient

        Patient.objects.filter(pk=self.later.pk).update(
            created_at="2026-01-02T00:00:00Z"
        )
        Patient.objects.filter(pk=self.earlier.pk).update(
            created_at="2026-01-01T00:00:00Z"
        )
        self.keep_row = _create_record(self.earlier, "REC100", self.operator)
        self.dup_current = _create_record(self.later, "rec100", self.operator)

    def _emit(self, **options) -> dict:
        with NamedTemporaryFile("r", suffix=".json", delete=False) as handle:
            path = handle.name
        self.addCleanup(os.remove, path)
        _run_command(emit_skeleton=path, **options)
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)

    def test_same_person_group_is_fully_drafted(self):
        document = self._emit(prefill=True)
        group = document["groups"][0]
        self.assertEqual(group["keep"], str(self.keep_row.pk))
        action = group["actions"][0]
        self.assertEqual(action["assignment"], str(self.dup_current.pk))
        self.assertEqual(action["action"], "renumber")
        self.assertRegex(action["new_record_number"], r"^DUP-\d{4}$")
        self.assertIn("mesma pessoa", action["rationale"])

    def test_historical_row_of_same_person_is_voided(self):
        from apps.patients.models import PatientRecordNumber

        PatientRecordNumber.objects.filter(pk=self.dup_current.pk).update(
            is_current=False
        )
        document = self._emit(prefill=True)
        action = document["groups"][0]["actions"][0]
        self.assertEqual(action["action"], "void")
        self.assertNotIn("new_record_number", action)

    def test_mixed_group_stays_placeholder(self):
        from apps.patients.models import Patient

        Patient.objects.filter(pk=self.later.pk).update(name=OTHER_NAME)
        document = self._emit(prefill=True)
        group = document["groups"][0]
        self.assertEqual(group["keep"], "PREENCHA")
        self.assertEqual(group["actions"], [])

    def test_series_skips_numbers_already_in_use(self):
        holder = _create_patient(self.operator, "Titular Serie")
        _create_record(holder, "DUP-0001", self.operator)
        document = self._emit(prefill=True)
        action = document["groups"][0]["actions"][0]
        self.assertEqual(action["new_record_number"], "DUP-0002")

    def test_fully_drafted_plan_parses_and_reports_counts(self):
        with NamedTemporaryFile("r", suffix=".json", delete=False) as handle:
            path = handle.name
        self.addCleanup(os.remove, path)
        output = _run_command(emit_skeleton=path, prefill=True)
        self.assertIn("1 pre-filled", output)
        self.assertIn("0 need manual", output)
        with open(path, encoding="utf-8") as handle:
            document = json.load(handle)
        document["plan_ref"] = "consol-prefill"
        plan = parse_consolidation_plan(json.dumps(document))
        self.assertEqual(plan.groups[0].keep_id, self.keep_row.pk)

    def test_prefill_requires_emit_skeleton(self):
        from django.core.management.base import CommandError

        with self.assertRaisesMessage(CommandError, "--emit-skeleton"):
            _run_command(prefill=True)
