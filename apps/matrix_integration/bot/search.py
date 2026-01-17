from dataclasses import dataclass
from typing import List, Optional

from django.db.models import Q
from django.utils import timezone

from apps.patients.models import Patient, PatientAdmission


PREFIX_MAP = {
    "reg": "record_number",
    "registro": "record_number",
    "leito": "bed",
    "cama": "bed",
    "enf": "ward",
    "enfermaria": "ward",
    "setor": "ward",
}


@dataclass(frozen=True)
class SearchQuery:
    name_terms: List[str]
    record_number: Optional[str]
    bed: Optional[str]
    ward: Optional[str]


def parse_search_query(raw_query: str) -> SearchQuery:
    name_terms = []
    record_number = None
    bed = None
    ward = None

    parts = raw_query.strip().split()
    for part in parts:
        if ":" in part:
            prefix, value = part.split(":", 1)
            prefix = prefix.lower().strip()
            value = value.strip()
            if prefix in PREFIX_MAP:
                if not value or len(value) > 50:
                    continue
                field = PREFIX_MAP[prefix]
                if field == "record_number":
                    record_number = value
                elif field == "bed":
                    bed = value
                elif field == "ward":
                    ward = value
                continue
        name_terms.append(part)

    return SearchQuery(
        name_terms=name_terms,
        record_number=record_number,
        bed=bed,
        ward=ward,
    )


def search_inpatients(query: SearchQuery):
    qs = (
        PatientAdmission.objects.filter(
            is_active=True,
            patient__is_deleted=False,
            patient__status__in=[Patient.Status.INPATIENT, Patient.Status.EMERGENCY],
        )
        .select_related("patient", "ward", "patient__ward")
        .distinct()
    )

    if query.record_number:
        qs = qs.filter(
            Q(patient__current_record_number__icontains=query.record_number)
            | Q(patient__record_numbers__record_number__icontains=query.record_number)
        )

    if query.bed:
        qs = qs.filter(
            Q(initial_bed__icontains=query.bed)
            | Q(final_bed__icontains=query.bed)
            | Q(patient__bed__icontains=query.bed)
        )

    if query.ward:
        qs = qs.filter(
            Q(ward__name__icontains=query.ward)
            | Q(ward__abbreviation__icontains=query.ward)
            | Q(patient__ward__name__icontains=query.ward)
            | Q(patient__ward__abbreviation__icontains=query.ward)
        )

    for term in query.name_terms:
        qs = qs.filter(patient__name__icontains=term)

    return list(qs)


def _score_candidate(admission: PatientAdmission, query: SearchQuery) -> int:
    score = 0
    patient = admission.patient
    record_number = (patient.get_current_record_number() or "").strip()
    record_lower = record_number.lower()

    if query.record_number:
        query_lower = query.record_number.lower()
        if record_lower == query_lower:
            score += 1000
        elif query_lower in record_lower:
            score += 500

    bed_value = (
        (admission.initial_bed or "")
        or (admission.final_bed or "")
        or (patient.bed or "")
    ).strip()
    bed_lower = bed_value.lower()
    if query.bed:
        bed_query = query.bed.lower()
        if bed_lower == bed_query:
            score += 800
        elif bed_query in bed_lower:
            score += 400

    ward_obj = admission.ward or patient.ward
    ward_name = ward_obj.name if ward_obj else ""
    ward_abbreviation = ward_obj.abbreviation if ward_obj else ""
    ward_name_lower = ward_name.lower()
    ward_abbrev_lower = ward_abbreviation.lower()
    if query.ward:
        ward_query = query.ward.lower()
        if ward_name_lower == ward_query or ward_abbrev_lower == ward_query:
            score += 600
        elif ward_query in ward_name_lower or ward_query in ward_abbrev_lower:
            score += 300

    if query.name_terms:
        name_lower = (patient.name or "").lower()
        for term in query.name_terms:
            if term.lower() in name_lower:
                score += 200

    if admission.admission_datetime:
        days_since = (timezone.now() - admission.admission_datetime).days
        if days_since >= 0:
            score += max(0, 50 - days_since)

    return score


def rank_patient_candidates(candidates: List[PatientAdmission], query: SearchQuery):
    scored = []
    for admission in candidates:
        score = _score_candidate(admission, query)
        scored.append((score, admission))

    def sort_key(item):
        score, admission = item
        admission_ts = 0
        if admission.admission_datetime:
            admission_ts = admission.admission_datetime.timestamp()
        return (-score, -admission_ts)

    scored.sort(key=sort_key)
    return [admission for _score, admission in scored]
