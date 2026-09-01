"""Parse and validation of operator-authored consolidation plans.

Pure decision layer: structurally parses the JSON plan, then refuses
unknown, stale, incomplete, or badly targeted decisions before any
mutation happens. No writes live here; execution belongs to
``patient_record_consolidation``.
"""

import json
from dataclasses import dataclass
from json import JSONDecodeError
from uuid import UUID

from django.core.exceptions import ValidationError

from apps.patients.models import PatientRecordNumber
from apps.patients.services.patient_identity import RecordNumberCollisionGroup
from apps.patients.validators import validate_record_number_format

# Plan action vocabulary (parse-level contract).
ACTION_VOID = "void"
ACTION_RENUMBER = "renumber"


class ConsolidationPlanError(Exception):
    """Operator plan is malformed, stale, unknown, or incomplete."""


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


def _require_groups(payload: dict[str, object]) -> list[object]:
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
