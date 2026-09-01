"""Read-only clinical review and skeleton presentation for collisions.

Annotates discovery groups with operator context (name, birthday,
same-person likelihood) and renders the fillable decision scaffold.
Console-only disclosure; never writes, never logs PII.
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from uuid import UUID

from apps.patients.models import PatientRecordNumber
from apps.patients.services.patient_identity import (
    RecordNumberCollisionGroup,
    find_record_number_collision_groups,
    normalize_name,
)


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


def _review_rows(group: RecordNumberCollisionGroup) -> list[dict[str, Any]]:
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


def skeleton_document(reviews: list[CollisionGroupReview]) -> dict[str, Any]:
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


def _skeleton_row(row: CollisionRowReview) -> dict[str, Any]:
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
