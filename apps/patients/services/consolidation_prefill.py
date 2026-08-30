"""Operator-criterion pre-drafting of consolidation decisions.

The owner authorized the matching criterion (normalized name plus
birthday equality, 2026-08-30): groups whose every row matches get
keep and void/renumber decisions drafted for operator review; any
group with a non-matching row keeps its placeholders. Drafting only:
execution remains the operator's reviewed plan, and nothing here
mutates the database.
"""

from apps.patients.services.patient_identity import (
    find_record_number_conflict,
)
from apps.patients.services.patient_record_consolidation import (
    CollisionGroupReview,
    CollisionRowReview,
    skeleton_document,
)

SERIES_PREFIX = "DUP-"
PREFILL_RATIONALE = (
    "mesma pessoa (nome e nascimento idênticos) - lançamento duplicado"
)


def prefill_document(reviews: list[CollisionGroupReview]) -> dict:
    """Draft decisions for fully same-person groups on top of the
    scaffold; groups with any non-matching row stay placeholders."""
    document = skeleton_document(reviews)
    taken: set[str] = set()
    for group, source in zip(document["groups"], reviews, strict=True):
        if _all_same_person(source):
            _draft_group(group, source, taken)
    return document


def _all_same_person(group: CollisionGroupReview) -> bool:
    """True when every row of the group matches the criterion."""
    return bool(group.rows) and all(row.same_person_likely for row in group.rows)


def _draft_group(group: dict, source: CollisionGroupReview, taken: set) -> None:
    """Fill keep and actions for one same-person group."""
    keep_row = _keep_row(source.rows)
    group["keep"] = str(keep_row.assignment_id)
    group["actions"] = [
        _draft_action(row, taken)
        for row in source.rows
        if row.assignment_id != keep_row.assignment_id
    ]


def _keep_row(rows: list[CollisionRowReview]) -> CollisionRowReview:
    """Prefer a current row from the earliest-created patient."""
    current = [row for row in rows if row.is_current]
    pool = current or rows
    return min(pool, key=lambda row: (row.patient_created_at, str(row.patient_id)))


def _draft_action(row: CollisionRowReview, taken: set) -> dict:
    """Current rows renumber into the duplicate series; others void."""
    action = {
        "assignment": str(row.assignment_id),
        "rationale": PREFILL_RATIONALE,
    }
    if row.is_current:
        action["action"] = "renumber"
        action["new_record_number"] = _next_series_number(taken)
    else:
        action["action"] = "void"
    return action


def _next_series_number(taken: set) -> str:
    """Next free series number: unique in this run and in the database."""
    counter = 1
    while True:
        candidate = f"{SERIES_PREFIX}{counter:04d}"
        counter += 1
        if candidate in taken:
            continue
        if find_record_number_conflict(candidate) is not None:
            continue
        taken.add(candidate)
        return candidate
