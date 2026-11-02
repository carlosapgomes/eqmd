"""Requester-aware tag overlay and filtering for the cached ward map (S9).

The shared ward-mapping cache is a structural base only: ward, bed, patient
identity and admission duration. Catalogue metadata and patient associations
are rehydrated here for the bounded set of patients that base references, in
batched queries, and the shared :class:`TagFilterSelection` is applied
afterwards (design D7). Requester visibility therefore runs before
serialization and before filtering, so a warm payload can never delay a
revocation, a reclassification or an assignment change.

The cached rows are untyped JSON persisted by the background command, so ``Any``
marks row values only; the keys read here are the documented payload contract.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from apps.core.utils.text import normalize_text_for_search
from apps.patients.services import tag_projection
from apps.patients.services.tag_filters import TagFilterSelection

if TYPE_CHECKING:
    from apps.accounts.models import EqmdCustomUser


@dataclass(frozen=True)
class WardMapFilters:
    """The effective filter state of one ward-map request.

    ``selection`` is the same resolved state the patient list renders, so both
    surfaces share ANY/ALL semantics and the manual/saved/principal precedence.
    """

    selection: TagFilterSelection
    search_query: str = ""
    ward_id: str = ""
    show_empty_wards: bool = False


def _cached_patient_ids(ward_data: Sequence[Mapping[str, Any]]) -> list[uuid.UUID]:
    """Return the distinct patient identifiers referenced by the cached base."""
    identifiers: dict[str, uuid.UUID] = {}
    for ward_info in ward_data:
        for patient_info in ward_info.get("patients", []):
            raw_id = str(patient_info["patient"]["pk"]).strip()
            if raw_id and raw_id not in identifiers:
                identifiers[raw_id] = uuid.UUID(raw_id)
    return list(identifiers.values())


def project_patients(
    ward_data: Sequence[Mapping[str, Any]], *, actor: EqmdCustomUser | None
) -> list[dict[str, Any]]:
    """Rebuild cached ward rows with current, requester-visible tag metadata.

    Tag names, colours, identifiers, lifecycle labels and associations are
    re-read for this viewer from the current catalogue; the cached structure is
    only copied, never mutated. Every patient of the bounded set is rehydrated
    through one batched projection, so no query runs per patient or per ward.
    """
    identifiers = _cached_patient_ids(ward_data)
    badges_by_patient = tag_projection.patient_tag_badges_by_patient(actor, identifiers)
    projected: list[dict[str, Any]] = []
    for ward_info in ward_data:
        ward_copy = dict(ward_info)
        patients = []
        for patient_info in ward_info.get("patients", []):
            patient_copy = dict(patient_info)
            patient_id = uuid.UUID(str(patient_info["patient"]["pk"]))
            patient_copy["tags"] = [
                {
                    "allowed_tag": {
                        "id": badge.tag_id,
                        "name": badge.name,
                        "color": badge.color,
                    },
                    "state": badge.state,
                    "state_label": badge.state_label,
                }
                for badge in badges_by_patient.get(patient_id, [])
            ]
            patients.append(patient_copy)
        ward_copy["patients"] = patients
        projected.append(ward_copy)
    return projected


def _matches_search(patient_info: Mapping[str, Any], search_query: str) -> bool:
    """Return whether the cached name or bed contains the normalized term."""
    needle = normalize_text_for_search(search_query)
    if not needle:
        return True
    candidates = (
        patient_info["patient"]["name"],
        patient_info.get("bed") or "",
    )
    return any(needle in normalize_text_for_search(str(value)) for value in candidates)


def _matches_selection(
    patient_info: Mapping[str, Any], selection: TagFilterSelection
) -> bool:
    """Return whether the projected associations satisfy the shared selection."""
    return selection.matches(
        tag["allowed_tag"]["id"] for tag in patient_info.get("tags", [])
    )


def apply_filters(
    ward_data: Sequence[Mapping[str, Any]], filters: WardMapFilters
) -> list[dict[str, Any]]:
    """Apply the request predicates to already projected rows.

    Every surviving ward reports the number of patients actually rendered, and
    a ward without matches is dropped unless the request asked for empty wards.
    """
    filtered: list[dict[str, Any]] = []
    for ward_info in ward_data:
        if filters.ward_id and str(ward_info["ward"]["id"]) != str(filters.ward_id):
            continue
        patients = [
            patient_info
            for patient_info in ward_info.get("patients", [])
            if _matches_search(patient_info, filters.search_query)
            and _matches_selection(patient_info, filters.selection)
        ]
        if not patients and not filters.show_empty_wards:
            continue
        ward_copy = dict(ward_info)
        ward_copy["patients"] = patients
        ward_copy["patient_count"] = len(patients)
        filtered.append(ward_copy)
    return filtered


def map_totals(ward_data: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    """Return page totals computed from the rows the map actually renders."""
    return {
        "total_patients": sum(
            int(ward_info["patient_count"]) for ward_info in ward_data
        ),
        "total_wards": len(ward_data),
    }
