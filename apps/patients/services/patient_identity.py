"""Advisory patient-identity review for duplicate prevention (slice 001).

This service owns name normalization, candidate search, threshold, ordering,
and result shaping. It never persists, merges, updates, or deletes patients.
"""

import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from django.contrib.postgres.lookups import Unaccent
from django.contrib.postgres.search import TrigramSimilarity
from django.db import IntegrityError
from django.db.models import QuerySet
from django.db.models.functions import Lower, Trim

from apps.patients.models import Patient, PatientRecordNumber
from apps.patients.validators import (
    is_valid_cns,
    is_valid_cpf,
    normalize_cns,
    normalize_cpf,
)

NAME_SIMILARITY_THRESHOLD = 0.80

EVIDENCE_EXACT = "exact"
EVIDENCE_SIMILAR = "similar"
EVIDENCE_CPF = "cpf"
EVIDENCE_CNS = "cns"

# Planned slice-004 functional constraint over Lower(Trim(record_number)).
RECORD_CONSTRAINT_NAME = "unique_patient_record_number_lifetime"
RECORD_NUMBER_CONFLICT_MESSAGE = (
    "Este número de prontuário já está reservado (atual ou histórico). "
    "Escolha um número diferente."
)
RECORD_NUMBER_CHANGE_MESSAGE = (
    "O número de uma atribuição existente não pode ser alterado. "
    "Registre um novo número de prontuário para representar a mudança."
)
RECORD_NUMBER_DELETE_MESSAGE = (
    "Número de prontuário não pode ser removido: o histórico é imutável."
)

_NON_ALPHANUMERIC = re.compile(r"[\W_]+", re.UNICODE)
_REPEATED_SPACES = re.compile(r"\s+")


@dataclass(frozen=True)
class DuplicateCandidate:
    """Minimal disclosure DTO for one advisory duplicate candidate."""

    patient_id: UUID
    name: str
    birthday: date
    current_record_number: str
    is_deleted: bool
    evidence_type: str
    similarity: float


def normalize_name(name: str) -> str:
    """Lowercase a name ignoring accents, punctuation, and repeated spaces."""
    decomposed = unicodedata.normalize("NFKD", name)
    without_accents = "".join(
        char for char in decomposed if not unicodedata.combining(char)
    )
    without_punctuation = _NON_ALPHANUMERIC.sub(" ", without_accents)
    collapsed = _REPEATED_SPACES.sub(" ", without_punctuation)
    return collapsed.strip().lower()


def normalize_record_number(value: str) -> str:
    """Trim external whitespace for canonical record-number comparison."""
    return value.strip()


def find_record_number_conflict(record_number: str) -> PatientRecordNumber | None:
    """Return the first retained assignment with the same canonical number.

    The comparison mirrors the planned slice-004 functional constraint
    ``Lower(Trim(record_number))`` and covers current, historical, and
    soft-deleted-owner rows alike.
    """
    canonical = normalize_record_number(record_number).lower()
    if not canonical:
        return None
    return (
        PatientRecordNumber.objects.annotate(
            canonical_number=Lower(Trim("record_number")),
        )
        .filter(canonical_number=canonical)
        .first()
    )


def is_record_constraint_violation(error: IntegrityError) -> bool:
    """True when the integrity error names the planned lifetime constraint."""
    return RECORD_CONSTRAINT_NAME in str(error)


def find_duplicate_candidates(name: str, birthday: date) -> list[DuplicateCandidate]:
    """Return advisory name-and-birthday candidates for the given submission."""
    normalized_query = normalize_name(name)
    if not normalized_query:
        return []
    cohort = (
        Patient.all_objects.filter(birthday=birthday)
        .annotate(
            similarity=TrigramSimilarity(Unaccent(Lower("name")), normalized_query),
        )
        .order_by("name", "id")
    )
    return [
        _to_candidate(patient, normalized_query)
        for patient in cohort
        if _similarity_of(patient) >= NAME_SIMILARITY_THRESHOLD
        or normalize_name(patient.name) == normalized_query
    ]


def _to_candidate(patient: Patient, normalized_query: str) -> DuplicateCandidate:
    """Shape one patient row into a minimal disclosure candidate DTO."""
    is_exact = normalize_name(patient.name) == normalized_query
    return DuplicateCandidate(
        patient_id=patient.pk,
        name=patient.name,
        birthday=patient.birthday,
        current_record_number=patient.current_record_number,
        is_deleted=patient.is_deleted,
        evidence_type=EVIDENCE_EXACT if is_exact else EVIDENCE_SIMILAR,
        similarity=_similarity_of(patient),
    )


def _similarity_of(patient: Patient) -> float:
    """Read the annotated trigram similarity from a patient row."""
    return float(getattr(patient, "similarity", 0.0))


def find_strong_identifier_conflicts(
    *,
    cpf: str = "",
    cns: str = "",
    exclude_patient_id: UUID | None = None,
) -> list[DuplicateCandidate]:
    """Return patients owning the same valid canonical CPF or CNS."""
    canonical_cpf = normalize_cpf(cpf)
    canonical_cns = normalize_cns(cns)
    conflicts: list[DuplicateCandidate] = []
    if is_valid_cpf(canonical_cpf):
        conflicts.extend(_cpf_conflicts(canonical_cpf, exclude_patient_id))
    if is_valid_cns(canonical_cns):
        conflicts.extend(_cns_conflicts(canonical_cns, exclude_patient_id))
    return conflicts


def _cpf_conflicts(
    canonical_cpf: str, exclude_patient_id: UUID | None
) -> list[DuplicateCandidate]:
    """Find patients storing the same canonical CPF."""
    queryset = Patient.all_objects.filter(fiscal_number=canonical_cpf)
    return _conflicts_for(queryset, EVIDENCE_CPF, exclude_patient_id)


def _cns_conflicts(
    canonical_cns: str, exclude_patient_id: UUID | None
) -> list[DuplicateCandidate]:
    """Find patients storing the same canonical CNS."""
    queryset = Patient.all_objects.filter(healthcard_number=canonical_cns)
    return _conflicts_for(queryset, EVIDENCE_CNS, exclude_patient_id)


def _conflicts_for(
    queryset: QuerySet[Patient],
    evidence_type: str,
    exclude_patient_id: UUID | None,
) -> list[DuplicateCandidate]:
    """Shape matching rows into minimal strong-conflict candidate DTOs."""
    if exclude_patient_id:
        queryset = queryset.exclude(pk=exclude_patient_id)
    return [
        DuplicateCandidate(
            patient_id=patient.pk,
            name=patient.name,
            birthday=patient.birthday,
            current_record_number=patient.current_record_number,
            is_deleted=patient.is_deleted,
            evidence_type=evidence_type,
            similarity=0.0,
        )
        for patient in queryset.order_by("name", "id")
    ]
