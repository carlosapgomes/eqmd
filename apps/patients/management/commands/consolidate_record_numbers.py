"""Audited consolidation of canonical record-number collisions.

Transport only: prints the aggregate audit by default, per-group detail
under ``--show-records``, clinical context (name and birthday per row)
under ``--show-patients`` for the operator console, and a fillable
decision scaffold via ``--emit-skeleton``. Plan runs are dry-run by
default (atomic rollback) or ``--execute`` (single transaction with a
zero-collision post-check). CPF and CNS are never printed.
"""

import json
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.patients.services.consolidation_prefill import prefill_document
from apps.patients.services.patient_identity import (
    find_record_number_collision_groups,
    summarize_record_number_collisions,
)
from apps.patients.services.patient_record_consolidation import (
    ConsolidationPlan,
    ConsolidationPlanError,
    ResidualCollisionError,
    apply_consolidation_actions,
    build_collision_review,
    execute_consolidation_plan,
    parse_consolidation_plan,
    skeleton_document,
    validate_consolidation_plan,
)


class Command(BaseCommand):
    help = (
        "Audited consolidation of canonical record-number collision groups: "
        "aggregate audit by default; operator JSON plan for dry-run and "
        "execute; no automatic clinical decisions."
    )

    def add_arguments(self, parser):
        self._add_output_arguments(parser)
        self._add_plan_arguments(parser)

    def _add_output_arguments(self, parser) -> None:
        parser.add_argument(
            "--show-records",
            action="store_true",
            help="Print per-group detail (canonical number, assignment and "
            "patient ids) for the operator console",
        )
        parser.add_argument(
            "--show-patients",
            action="store_true",
            help="Operator-console clinical context per row: name, "
            "birthday, current flag, and a likely-same-person marker "
            "(CPF/CNS are never printed)",
        )
        parser.add_argument(
            "--emit-skeleton",
            type=str,
            metavar="PATH",
            help="Write a fillable decision scaffold (groups, ids, and "
            "clinical context) to PATH; keep the file outside the "
            "repository",
        )

    def _add_plan_arguments(self, parser) -> None:
        parser.add_argument(
            "--prefill",
            action="store_true",
            help="With --emit-skeleton: draft decisions for groups whose "
            "every row matches the owner's same-person criterion "
            "(normalized name plus birthday); other groups keep "
            "placeholders",
        )
        parser.add_argument(
            "--plan",
            type=str,
            help="Path to the operator-authored JSON decision plan "
            "(never committed to the repository)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Attempt the plan inside a rolled-back transaction "
            "(default behavior when --plan is given)",
        )
        parser.add_argument(
            "--execute",
            action="store_true",
            help="Execute the plan in one transaction with a zero-collision post-check",
        )
        parser.add_argument(
            "--user",
            type=str,
            help="Operator username (required with --plan; recorded as "
            "updated_by on every touched row)",
        )

    def handle(self, *args, **options):
        summary = summarize_record_number_collisions()
        self.stdout.write(
            f"{summary.group_count} canonical record-number collision group(s) "
            f"involving {summary.involved_rows} row(s)."
        )
        if options["show_records"]:
            self._print_group_details()
        if options["show_patients"]:
            self._print_patient_details()
        if options["emit_skeleton"]:
            self._write_skeleton(options["emit_skeleton"], options["prefill"])
        elif options["prefill"]:
            raise CommandError("--prefill requires --emit-skeleton")
        if options["plan"] is None:
            return
        plan = self._load_validated_plan(options["plan"])
        operator = self._resolve_operator(options["user"])
        if options["execute"]:
            self._execute(plan, operator)
        else:
            self._dry_run(plan, operator)

    def _print_group_details(self) -> None:
        """Operator-console detail: canonical number and id references only."""
        for group in find_record_number_collision_groups():
            assignments = ", ".join(str(pk) for pk in group.assignment_ids)
            patients = ", ".join(str(pk) for pk in group.patient_ids)
            self.stdout.write(
                f"group canonical='{group.canonical}' "
                f"assignments=[{assignments}] patients=[{patients}]"
            )

    def _print_patient_details(self) -> None:
        """Operator-console clinical context for every collision row."""
        for group in build_collision_review():
            self.stdout.write(
                f"group canonical='{group.canonical}' ({len(group.rows)} rows)"
            )
            for row in group.rows:
                self._print_reviewed_row(row)

    def _print_reviewed_row(self, row) -> None:
        """One reviewed row: state, number, ids, name, birthday, marker."""
        state = "CORRENTE" if row.is_current else "histórico"
        marker = " [provável mesma pessoa]" if row.same_person_likely else ""
        self.stdout.write(
            f"  [{state}] {row.record_number!r} assignment={row.assignment_id} "
            f"patient={row.patient_id} nome={row.patient_name!r} "
            f"nascimento={row.birthday}{marker}"
        )

    def _write_skeleton(self, path: str, prefill: bool) -> None:
        """Write the decision scaffold, optionally pre-drafting."""
        reviews = build_collision_review()
        document = prefill_document(reviews) if prefill else skeleton_document(reviews)
        payload = json.dumps(document, ensure_ascii=False, indent=2)
        Path(path).write_text(payload, encoding="utf-8")
        groups = document["groups"]
        drafted = sum(1 for group in groups if group["keep"] != "PREENCHA")
        manual = len(groups) - drafted
        self.stdout.write(
            f"skeleton with {len(groups)} group(s) written to {path}; "
            f"{drafted} pre-filled (same person), {manual} need manual "
            "decision; review, edit, and keep the file outside the repository"
        )

    def _load_validated_plan(self, path: str) -> ConsolidationPlan:
        """Read the plan file and refuse anything unknown, stale, or partial."""
        try:
            text = Path(path).read_text(encoding="utf-8")
        except OSError as exc:
            raise CommandError(f"unreadable plan file: {exc}") from exc
        try:
            plan = parse_consolidation_plan(text)
            validate_consolidation_plan(plan, find_record_number_collision_groups())
        except ConsolidationPlanError as exc:
            raise CommandError(f"plan refused: {exc}") from exc
        return plan

    def _resolve_operator(self, username: str | None):
        """Require and resolve the explicit operator recorded on every row."""
        if not username:
            raise CommandError("--user <username> is required with --plan")
        user_model = get_user_model()
        try:
            return user_model.objects.get(username=username)
        except user_model.DoesNotExist as exc:
            raise CommandError(f"unknown operator user: {username}") from exc

    def _execute(self, plan: ConsolidationPlan, operator) -> None:
        """Run the whole plan in one transaction, then verify zero collisions."""
        try:
            with transaction.atomic():
                summary = execute_consolidation_plan(plan, operator)
        except (ResidualCollisionError, ValidationError) as exc:
            raise CommandError(f"execution rolled back: {exc}") from exc
        actions = sum(len(group.actions) for group in plan.groups)
        self.stdout.write(
            self.style.SUCCESS(
                f"executed plan '{plan.plan_ref}': {actions} action(s); "
                f"post-check: {summary.group_count} collision group(s) remaining"
            )
        )

    def _dry_run(self, plan: ConsolidationPlan, operator) -> None:
        """Attempt the plan inside a rolled-back transaction, print the state."""
        try:
            with transaction.atomic():
                apply_consolidation_actions(plan, operator)
                summary = summarize_record_number_collisions()
                transaction.set_rollback(True)
        except ValidationError as exc:
            raise CommandError(f"dry run failed: {exc}") from exc
        actions = sum(len(group.actions) for group in plan.groups)
        self.stdout.write(
            f"DRY RUN plan '{plan.plan_ref}': {actions} action(s) attempted "
            f"inside a rolled-back transaction; would leave "
            f"{summary.group_count} collision group(s) involving "
            f"{summary.involved_rows} row(s)"
        )
        if summary.group_count:
            raise CommandError(
                f"dry run leaves {summary.group_count} collision group(s); "
                "plan coverage is incomplete"
            )
