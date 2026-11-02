"""S9: ``get_cached_ward_mapping`` reports totals for the rows it returns.

The cache utility owns staleness, the requester projection hand-off and the
fallback state; filtering and totals come from the shared ward overlay so the
rendered page can never disagree with its header.
"""

from __future__ import annotations

from typing import Any

from django.test import TestCase
from django.utils import timezone

from apps.accounts.tests.helpers import create_navigation_user
from apps.core.models import WardMappingCache
from apps.core.utils.cache import get_cached_ward_mapping
from apps.patients.models import AllowedTag, Patient, Tag, Ward
from apps.patients.services import tag_filters, ward_tag_overlay


def build_cached_wards(wards: list[tuple[Ward, list[Patient]]]) -> dict[str, Any]:
    """Return the structural payload the background command writes."""
    ward_rows = []
    total_patients = 0
    for ward, patients in wards:
        patient_rows: list[dict[str, Any]] = [
            {
                "patient": {"pk": str(patient.pk), "name": patient.name},
                "bed": patient.bed or "Sem leito",
                "admission_duration": None,
                "tags": [],
            }
            for patient in patients
        ]
        total_patients += len(patient_rows)
        ward_rows.append(
            {
                "ward": {
                    "id": str(ward.pk),
                    "name": ward.name,
                    "abbreviation": ward.abbreviation,
                    "floor": None,
                },
                "patient_count": len(patient_rows),
                "capacity_estimate": None,
                "utilization_percentage": None,
                "patients": patient_rows,
            }
        )
    return {
        "ward_data": ward_rows,
        "total_patients": total_patients,
        "total_wards": len(ward_rows),
        "updated_at": timezone.now().isoformat(),
    }


class CachedWardMappingTests(TestCase):
    """Totals, search and fallback states of the cached ward mapping."""

    user: Any
    tag: AllowedTag
    ward: Ward
    joao: Patient
    other: Patient

    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = create_navigation_user(
            username="cache-utils-user",
            email="cache-utils-user@example.com",
            password="cache-utils-pass",
        )
        cls.tag = AllowedTag.objects.create(
            name="Prioridade Global",
            color="#123456",
            created_by=cls.user,
            updated_by=cls.user,
        )
        cls.ward = Ward.objects.create(
            name="UTI",
            abbreviation="UTI",
            created_by=cls.user,
            updated_by=cls.user,
        )
        cls.joao = Patient.objects.create(
            name="João da Silva",
            birthday="1980-01-01",
            status=Patient.Status.INPATIENT,
            ward=cls.ward,
            bed="101",
            created_by=cls.user,
            updated_by=cls.user,
        )
        cls.other = Patient.objects.create(
            name="Maria Souza",
            birthday="1985-01-01",
            status=Patient.Status.INPATIENT,
            ward=cls.ward,
            bed="102",
            created_by=cls.user,
            updated_by=cls.user,
        )
        Tag.objects.create(
            allowed_tag=cls.tag,
            patient=cls.joao,
            created_by=cls.user,
            updated_by=cls.user,
        )

    def setUp(self) -> None:
        self.cached = build_cached_wards([(self.ward, [self.joao, self.other])])
        WardMappingCache.objects.update_or_create(
            cache_key="ward_mapping_full", defaults={"ward_data": self.cached}
        )
        WardMappingCache.objects.update_or_create(
            cache_key="ward_filters",
            defaults={
                "ward_data": {
                    "all_wards": [
                        {
                            "id": str(self.ward.pk),
                            "name": self.ward.name,
                            "abbreviation": self.ward.abbreviation,
                        }
                    ],
                    "available_tags": [],
                    "updated_at": timezone.now().isoformat(),
                }
            },
        )

    def filters(self, **kwargs: Any) -> Any:
        return ward_tag_overlay.WardMapFilters(
            selection=kwargs.pop("selection", tag_filters.TagFilterSelection()),
            **kwargs,
        )

    def test_search_matches_patient_name_without_accents(self) -> None:
        result = get_cached_ward_mapping(
            self.filters(search_query="joao"), viewer=self.user
        )

        self.assertEqual(result["total_patients"], 1)
        self.assertEqual(result["total_wards"], 1)
        self.assertEqual(
            result["ward_data"][0]["patients"][0]["patient"]["name"], "João da Silva"
        )

    def test_totals_reflect_the_filtered_rows_not_the_cached_globals(self) -> None:
        selection = tag_filters.TagFilterSelection(
            tags=(self.tag,),
            mode=tag_filters.MATCH_ALL,
            source=tag_filters.SOURCE_MANUAL,
        )

        result = get_cached_ward_mapping(
            self.filters(selection=selection), viewer=self.user
        )

        self.assertEqual(self.cached["total_patients"], 2)
        self.assertEqual(result["total_patients"], 1)
        self.assertEqual(result["ward_data"][0]["patient_count"], 1)

    def test_unfiltered_request_still_reprojects_and_counts(self) -> None:
        result = get_cached_ward_mapping(self.filters(), viewer=self.user)

        self.assertTrue(result["from_cache"])
        self.assertEqual(result["total_patients"], 2)
        self.assertEqual(
            result["ward_data"][0]["patients"][0]["tags"][0]["allowed_tag"]["name"],
            self.tag.name,
        )

    def test_missing_cache_reports_the_updating_fallback(self) -> None:
        WardMappingCache.objects.all().delete()

        result = get_cached_ward_mapping(self.filters(), viewer=self.user)

        self.assertFalse(result["from_cache"])
        self.assertTrue(result["updating"])
        self.assertEqual(result["ward_data"], [])
        self.assertEqual(result["total_patients"], 0)
        self.assertEqual(result["total_wards"], 0)

    def test_request_never_mutates_the_shared_payload(self) -> None:
        get_cached_ward_mapping(self.filters(search_query="joao"), viewer=self.user)

        self.assertEqual(
            WardMappingCache.objects.get(cache_key="ward_mapping_full").ward_data,
            self.cached,
        )
