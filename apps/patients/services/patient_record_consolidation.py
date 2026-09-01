"""Audited consolidation service for record-number collisions (slice R2).

Operator-decided, plan-driven resolution: the decided assignment keeps
the number untouched; erroneous rows are renumbered through the audited
append flow or voided in place with a marker that preserves the original
value verbatim and is unique per row. No deletion, no automatic clinical
decisions.
"""

import json
from base64 import urlsafe_b64encode
from dataclasses import dataclass
from datetime import date, datetime
from json import JSONDecodeError
from uuid import UUID

from django.contrib.auth.base_user import AbstractBaseUser
from django.core.exceptions import ValidationError

from apps.patients.models import PatientRecordNumber
from apps.patients.services.patient_identity import (
    RecordNumberCollisionGroup,
    RecordNumberCollisionSummary,
    find_record_number_collision_groups,
    normalize_name,
    summarize_record_number_collisions,
)
from apps.patients.validators import validate_record_number_format

# Audited consolidation decision constants (design D2/D3).
VOID_MARKER = "::voided::"
ACTION_VOID = "void"
ACTION_RENUMBER = "renumber"


class ConsolidationPlanError(Exception):
    """Operator plan is malformed, stale, unknown, or incomplete."""


class ResidualCollisionError(Exception):
    """Applied consolidation still leaves canonical collision groups."""


@dataclass(frozen=True)
class PlanAction:
    """One operator decision for one assignment inside a group."""

    assignment_id: UUID
    action: str
    rationale: str
    new_record_number: str = ""


@dataclass(frozen=True)
class PlanGroup:
    """One decided collision group: the kept row plus every action."""

    canonical: str
    keep_id: UUID
    actions: list[PlanAction]


@dataclass(frozen=True)
class ConsolidationPlan:
    """Operator-authored decision plan (never committed to the repo)."""

    plan_ref: str
    groups: list[PlanGroup]


@dataclass(frozen=True)
class CollisionRowReview:
    """Clinical context for one collision row (operator console only)."""

    assignment_id: UUID
    patient_id: UUID
    record_number: str
    is_current: bool
    patient_name: str
    birthday: date
    patient_created_at: datetime
    same_person_likely: bool


@dataclass(frozen=True)
class CollisionGroupReview:
    """One collision group annotated with operator clinical context."""

    canonical: str
    rows: list[CollisionRowReview]


def parse_consolidation_plan(text: str) -> ConsolidationPlan:
    """Parse and structurally validate an operator-authored JSON plan."""
    try:
        payload = json.loads(text)
    except JSONDecodeError as exc:
        raise ConsolidationPlanError(f"invalid plan JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ConsolidationPlanError("plan root must be a JSON object")
    return ConsolidationPlan(
        plan_ref=_require_non_empty_str(payload.get("plan_ref"), "plan_ref"),
        groups=[
            _parse_plan_group(raw, index)
            for index, raw in enumerate(_require_groups(payload))
        ],
    )


def validate_consolidation_plan(
    plan: ConsolidationPlan, live_groups: list[RecordNumberCollisionGroup]
) -> None:
    """Refuse unknown, stale, or incomplete plans before any mutation."""
    live_by_canonical = {group.canonical: group for group in live_groups}
    _refuse_unmatched_canonicals(plan, live_by_canonical)
    for group in plan.groups:
        _validate_group_against_live(group, live_by_canonical[group.canonical])


def apply_consolidation_actions(
    plan: ConsolidationPlan, operator: AbstractBaseUser
) -> None:
    """Apply every decided action inside the caller's atomic transaction."""
    for group in plan.groups:
        for action in group.actions:
            _apply_action(action, plan.plan_ref, operator)


def enforce_zero_collisions() -> RecordNumberCollisionSummary:
    """Re-run discovery and raise unless zero collision groups remain."""
    summary = summarize_record_number_collisions()
    if summary.group_count:
        raise ResidualCollisionError(_residual_message(summary))
    return summary


def build_collision_review() -> list[CollisionGroupReview]:
    """Annotate every collision row with name, birthday, and same-person."""
    reviews: list[CollisionGroupReview] = []
    for group in find_record_number_collision_groups():
        rows = _review_rows(group)
        normalized = [normalize_name(row["patient__name"]) for row in rows]
        reviews.append(
            CollisionGroupReview(
                canonical=group.canonical,
                rows=[
                    CollisionRowReview(
                        assignment_id=row["id"],
                        patient_id=row["patient_id"],
                        record_number=row["record_number"],
                        is_current=row["is_current"],
                        patient_name=row["patient__name"],
                        birthday=row["patient__birthday"],
                        patient_created_at=row["patient__created_at"],
                        same_person_likely=normalized.count(
                            normalize_name(row["patient__name"])
                        )
                        > 1,
                    )
                    for row in rows
                ],
            )
        )
    return reviews


def _review_rows(group: RecordNumberCollisionGroup) -> list[dict]:
    """Collision rows with patient context, discovery-ordered (ids only)."""
    rows = list(
        PatientRecordNumber.objects.filter(id__in=group.assignment_ids)
        .order_by("id")
        .values(
            "id",
            "patient_id",
            "record_number",
            "is_current",
            "patient__name",
            "patient__birthday",
            "patient__created_at",
        )
    )
    return sorted(rows, key=lambda row: group.assignment_ids.index(row["id"]))


def skeleton_document(reviews: list[CollisionGroupReview]) -> dict:
    """Fillable decision scaffold carrying the clinical context."""
    return {
        "plan_ref": "PREENCHA-REF",
        "groups": [
            {
                "canonical": group.canonical,
                "keep": "PREENCHA",
                "actions": [],
                "context": {"rows": [_skeleton_row(row) for row in group.rows]},
            }
            for group in reviews
        ],
    }


def _skeleton_row(row: CollisionRowReview) -> dict:
    """One scaffold row: ids, stored number, and clinical context."""
    return {
        "assignment": str(row.assignment_id),
        "patient": str(row.patient_id),
        "record_number": row.record_number,
        "is_current": row.is_current,
        "name": row.patient_name,
        "birthday": str(row.birthday),
        "same_person_likely": row.same_person_likely,
    }


def execute_consolidation_plan(
    plan: ConsolidationPlan, operator: AbstractBaseUser
) -> RecordNumberCollisionSummary:
    """Apply the whole plan, then verify zero collisions (post-check)."""
    apply_consolidation_actions(plan, operator)
    return enforce_zero_collisions()


def _residual_message(summary: RecordNumberCollisionSummary) -> str:
    """Aggregate-only residual report (no values, no identifiers)."""
    return (
        f"{summary.group_count} collision group(s) involving "
        f"{summary.involved_rows} row(s) still remain after the plan; "
        "nothing was committed"
    )


def _require_groups(payload: dict) -> list:
    groups = payload.get("groups")
    if not isinstance(groups, list):
        raise ConsolidationPlanError("groups must be a list")
    return groups


def _require_non_empty_str(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConsolidationPlanError(f"{label} must be a non-empty string")
    return value


def _parse_uuid(value: object, label: str) -> UUID:
    try:
        return UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise ConsolidationPlanError(f"{label} must be a valid UUID") from exc


def _parse_plan_group(raw: object, index: int) -> PlanGroup:
    if not isinstance(raw, dict):
        raise ConsolidationPlanError(f"group #{index} must be an object")
    return PlanGroup(
        canonical=_require_non_empty_str(
            raw.get("canonical"), f"group #{index} canonical"
        ),
        keep_id=_parse_uuid(raw.get("keep"), f"group #{index} keep"),
        actions=[_parse_plan_action(item) for item in raw.get("actions", [])],
    )


def _parse_plan_action(raw: object) -> PlanAction:
    if not isinstance(raw, dict):
        raise ConsolidationPlanError("each action must be an object")
    action = raw.get("action")
    if action not in (ACTION_VOID, ACTION_RENUMBER):
        raise ConsolidationPlanError(f"unsupported action: {action!r}")
    assignment_id = _parse_uuid(raw.get("assignment"), "action assignment")
    new_number = raw.get("new_record_number", "")
    if action == ACTION_RENUMBER:
        _require_non_empty_str(new_number, "renumber new_record_number")
        try:
            validate_record_number_format(new_number)
        except ValidationError as exc:
            raise ConsolidationPlanError(
                f"renumber for assignment {assignment_id} targets an invalid "
                f"record number: {exc.messages[0]}"
            ) from exc
    return PlanAction(
        assignment_id=assignment_id,
        action=action,
        rationale=_require_non_empty_str(raw.get("rationale"), "rationale"),
        new_record_number=new_number,
    )


def _refuse_unmatched_canonicals(
    plan: ConsolidationPlan, live_by_canonical: dict[str, RecordNumberCollisionGroup]
) -> None:
    """Refuse duplicated, unknown, or uncovered canonical groups."""
    planned = [group.canonical for group in plan.groups]
    if len(set(planned)) != len(planned):
        raise ConsolidationPlanError("plan repeats a canonical group")
    unknown = [c for c in planned if c not in live_by_canonical]
    if unknown:
        raise ConsolidationPlanError(
            f"plan canonical number(s) {unknown} have no live collision group; "
            "re-run discovery before executing"
        )
    missing = [c for c in live_by_canonical if c not in planned]
    if missing:
        raise ConsolidationPlanError(
            f"{len(missing)} live collision group(s) are missing from the plan; "
            "cover every group before executing"
        )


def _validate_group_against_live(
    group: PlanGroup, live: RecordNumberCollisionGroup
) -> None:
    """Keep and action ids must match the live group exactly, once each."""
    live_ids = set(live.assignment_ids)
    if group.keep_id not in live_ids:
        raise ConsolidationPlanError(
            f"keep id {group.keep_id} is not part of live group '{group.canonical}'"
        )
    seen: set[UUID] = set()
    for action in group.actions:
        _validate_action_reference(action, group, live_ids, seen)
        seen.add(action.assignment_id)
        _validate_action_targets_live_row(action, group.canonical)


def _validate_action_reference(
    action: PlanAction, group: PlanGroup, live_ids: set[UUID], seen: set[UUID]
) -> None:
    """The action must reference a live, unduplicated, non-kept assignment."""
    if action.assignment_id == group.keep_id:
        raise ConsolidationPlanError("the kept assignment must not carry actions")
    if action.assignment_id not in live_ids:
        raise ConsolidationPlanError(
            f"assignment {action.assignment_id} no longer matches live "
            f"group '{group.canonical}'"
        )
    if action.assignment_id in seen:
        raise ConsolidationPlanError(
            f"duplicate action for assignment {action.assignment_id}"
        )


def _validate_action_targets_live_row(action: PlanAction, canonical: str) -> None:
    """Current rows renumber via the append flow; historical rows void."""
    assignment = PatientRecordNumber.objects.get(pk=action.assignment_id)
    if action.action == ACTION_RENUMBER and not assignment.is_current:
        raise ConsolidationPlanError(
            f"assignment {action.assignment_id} in '{canonical}' is historical; "
            "historical rows are voided, not renumbered"
        )
    if action.action == ACTION_VOID and assignment.is_current:
        raise ConsolidationPlanError(
            f"assignment {action.assignment_id} in '{canonical}' is the patient's "
            "current number; decide a renumber instead"
        )


def _apply_action(action: PlanAction, plan_ref: str, operator) -> None:
    """Renumber decided current rows; void every other decided row."""
    if action.action == ACTION_RENUMBER:
        _renumber_and_void(action, plan_ref, operator)
    else:
        _void_assignment_by_id(
            action.assignment_id, plan_ref, action.rationale, operator
        )


def _renumber_and_void(action: PlanAction, plan_ref: str, operator) -> None:
    """Append-flow the decided number, then void the deactivated old row."""
    assignment = PatientRecordNumber.objects.get(pk=action.assignment_id)
    assignment.patient.update_current_record_number(
        action.new_record_number,
        operator,
        reason=_decision_reason(action.rationale, plan_ref),
    )
    assignment.refresh_from_db()
    _void_assignment(assignment, plan_ref, action.rationale, operator)


def _void_assignment_by_id(
    assignment_id: UUID, plan_ref: str, rationale: str, operator
) -> None:
    assignment = PatientRecordNumber.objects.get(pk=assignment_id)
    _void_assignment(assignment, plan_ref, rationale, operator)


def _void_assignment(
    assignment: PatientRecordNumber, plan_ref: str, rationale: str, operator
) -> None:
    """Void in place: marker preserves the original and is unique per row."""
    assignment.record_number = _void_marker(assignment, plan_ref)
    assignment.change_reason = _decision_reason(rationale, plan_ref)
    assignment.updated_by = operator
    assignment.save(
        update_fields=["record_number", "change_reason", "updated_by", "updated_at"]
    )


def _void_marker(assignment: PatientRecordNumber, plan_ref: str) -> str:
    """Marker: original verbatim, plan-referenced, unique reversible pk token."""
    token = urlsafe_b64encode(assignment.pk.bytes).decode("ascii").rstrip("=")
    return f"{assignment.record_number}{VOID_MARKER}{plan_ref}:{token}"


def _decision_reason(rationale: str, plan_ref: str) -> str:
    """Recorded audit reason: clinical rationale plus plan reference."""
    return f"{rationale} [plan: {plan_ref}]"
