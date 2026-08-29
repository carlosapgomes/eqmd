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
from django.db.models.functions import Lower

from apps.patients.models import Patient

NAME_SIMILARITY_THRESHOLD = 0.80

EVIDENCE_EXACT = "exact"
EVIDENCE_SIMILAR = "similar"

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
