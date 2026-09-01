"""Audited consolidation executor for record-number collisions.

Mutating layer: applies operator-decided plans (renumber through the
audited append flow, void in place with a per-row reversible marker)
and enforces the zero-collision post-check. Also the public facade
re-exporting the plan and review layers so importers keep a single
entry point.
"""

from base64 import urlsafe_b64encode
from uuid import UUID

from django.contrib.auth.base_user import AbstractBaseUser

from apps.patients.models import PatientRecordNumber
from apps.patients.services.consolidation_plan import (
    ACTION_RENUMBER,
    ACTION_VOID,
    ConsolidationPlan,
    ConsolidationPlanError,
    PlanAction,
    PlanGroup,
    parse_consolidation_plan,
    validate_consolidation_plan,
)
from apps.patients.services.consolidation_review import (
    CollisionGroupReview,
    CollisionRowReview,
    build_collision_review,
    skeleton_document,
)
from apps.patients.services.patient_identity import (
    RecordNumberCollisionSummary,
    summarize_record_number_collisions,
)

# Void marker separator (executor owns the marker format).
VOID_MARKER = "::voided::"


class ResidualCollisionError(Exception):
    """Applied consolidation still leaves canonical collision groups."""


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


def _apply_action(
    action: PlanAction, plan_ref: str, operator: AbstractBaseUser
) -> None:
    """Renumber decided current rows; void every other decided row."""
    if action.action == ACTION_RENUMBER:
        _renumber_and_void(action, plan_ref, operator)
    else:
        _void_assignment_by_id(
            action.assignment_id, plan_ref, action.rationale, operator
        )


def _renumber_and_void(
    action: PlanAction, plan_ref: str, operator: AbstractBaseUser
) -> None:
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
    assignment_id: UUID,
    plan_ref: str,
    rationale: str,
    operator: AbstractBaseUser,
) -> None:
    assignment = PatientRecordNumber.objects.get(pk=assignment_id)
    _void_assignment(assignment, plan_ref, rationale, operator)


def _void_assignment(
    assignment: PatientRecordNumber,
    plan_ref: str,
    rationale: str,
    operator: AbstractBaseUser,
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


# Public facade surface (backward compatibility; see design D2).
__all__ = [
    "ACTION_RENUMBER",
    "ACTION_VOID",
    "VOID_MARKER",
    "CollisionGroupReview",
    "CollisionRowReview",
    "ConsolidationPlan",
    "ConsolidationPlanError",
    "PlanAction",
    "PlanGroup",
    "ResidualCollisionError",
    "apply_consolidation_actions",
    "build_collision_review",
    "enforce_zero_collisions",
    "execute_consolidation_plan",
    "parse_consolidation_plan",
    "skeleton_document",
    "validate_consolidation_plan",
]
