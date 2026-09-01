"""Temporary record-number generation for patients without a definitive one."""

from uuid import uuid4

from apps.patients.services.patient_identity import find_record_number_conflict
from apps.patients.validators import TEMPORARY_RECORD_PREFIX

MAX_GENERATION_ATTEMPTS = 5


def generate_temporary_record_number() -> str:
    """Return a unique server-generated temporary record number.

    Candidates follow ``TMP-`` + 8 uppercase hex chars. Each candidate is
    checked against ``find_record_number_conflict`` for at most
    ``MAX_GENERATION_ATTEMPTS`` attempts; if every candidate collides, the
    last one is returned and the lifetime database constraint surfaces as
    the form's standard conflict error.
    """
    candidate = _new_candidate()
    for _ in range(MAX_GENERATION_ATTEMPTS - 1):
        if find_record_number_conflict(candidate) is None:
            return candidate
        candidate = _new_candidate()
    return candidate


def is_temporary_record_number(value: str) -> bool:
    """True when the value carries the reserved temporary prefix."""
    return value.strip().upper().startswith(TEMPORARY_RECORD_PREFIX)


def _new_candidate() -> str:
    """Shape one ``uuid4`` into a temporary record number candidate."""
    return f"{TEMPORARY_RECORD_PREFIX}{uuid4().hex[:8].upper()}"
