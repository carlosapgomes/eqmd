"""S9 R2/R3: the ward-map tag overlay filters and counts the cached base.

``apps.patients.services.ward_tag_overlay`` rehydrates requester-visible tag
metadata for the bounded patient set of the shared cache and applies the shared
:class:`TagFilterSelection` predicate afterwards. These tests pin the pure
filter/total contract and prove the rehydration stays batched (one query per
concern, never per patient).
"""

from __future__ import annotations

from typing import Any

from django.db import connection
from django.test import SimpleTestCase, TestCase
from django.test.utils import CaptureQueriesContext

from apps.accounts.models import MedicalSpecialty, UserSpecialty
from apps.accounts.tests.helpers import create_navigation_user
from apps.patients.models import AllowedTag, Patient, Tag
from apps.patients.services import tag_filters, ward_tag_overlay


def ward_row(ward_id: str, patients: list[dict[str, Any]]) -> dict[str, Any]:
    """Build one cached ward branch with the structural fields only."""
    return {
        "ward": {"id": ward_id, "name": f"Ala {ward_id}", "abbreviation": ward_id},
        "patient_count": len(patients),
        "capacity_estimate": None,
        "utilization_percentage": None,
        "patients": patients,
    }


def patient_row(
    patient_id: str, name: str, *, bed: str = "101", tag_ids: tuple[int, ...] = ()
) -> dict[str, Any]:
    """Build one cached patient row including its projected tag payload."""
    return {
        "patient": {"pk": patient_id, "name": name},
        "bed": bed,
        "admission_duration": None,
        "tags": [
            {"allowed_tag": {"id": tag_id, "name": f"Tag {tag_id}", "color": "#000000"}}
            for tag_id in tag_ids
        ],
    }


def selection(*tag_ids: int, mode: str = tag_filters.MATCH_ANY) -> Any:
    """Build a resolved manual selection without touching the database."""
    tags = tuple(
        AllowedTag(pk=tag_id, name=f"Tag {tag_id}", color="#000000")
        for tag_id in tag_ids
    )
    return tag_filters.TagFilterSelection(
        tags=tags, mode=mode, source=tag_filters.SOURCE_MANUAL
    )


class WardTagOverlayFilterTests(SimpleTestCase):
    """R3: shared ANY/ALL, search, ward and empty-ward rules on cached rows."""

    def setUp(self) -> None:
        self.ward_data = [
            ward_row(
                "1",
                [
                    patient_row("a", "Paciente Ambas", bed="101", tag_ids=(1, 2)),
                    patient_row("b", "Paciente Um", bed="102", tag_ids=(1,)),
                ],
            ),
            ward_row(
                "2",
                [patient_row("c", "Paciente Dois", bed="201", tag_ids=(2,))],
            ),
            ward_row("3", []),
        ]

    def filter(self, **kwargs: Any) -> list[dict[str, Any]]:
        filters = ward_tag_overlay.WardMapFilters(
            selection=kwargs.pop("selection", selection()),
            **kwargs,
        )
        return ward_tag_overlay.apply_filters(self.ward_data, filters)

    def patient_ids(self, rows: list[dict[str, Any]]) -> set[str]:
        return {
            patient["patient"]["pk"] for ward in rows for patient in ward["patients"]
        }

    def test_no_predicate_keeps_every_patient_and_hides_empty_wards(self) -> None:
        rows = self.filter()

        self.assertEqual(self.patient_ids(rows), {"a", "b", "c"})
        self.assertEqual([ward["ward"]["id"] for ward in rows], ["1", "2"])

    def test_any_matches_at_least_one_selected_identity(self) -> None:
        rows = self.filter(selection=selection(1, 2, mode=tag_filters.MATCH_ANY))

        self.assertEqual(self.patient_ids(rows), {"a", "b", "c"})

    def test_all_requires_every_selected_identity(self) -> None:
        rows = self.filter(selection=selection(1, 2, mode=tag_filters.MATCH_ALL))

        self.assertEqual(self.patient_ids(rows), {"a"})

    def test_search_matches_name_without_accents_and_the_bed(self) -> None:
        by_name = self.filter(search_query="paciente amba")
        by_bed = self.filter(search_query="201")

        self.assertEqual(self.patient_ids(by_name), {"a"})
        self.assertEqual(self.patient_ids(by_bed), {"c"})

    def test_search_and_tag_predicates_stay_conjunctive(self) -> None:
        rows = self.filter(
            search_query="Paciente", selection=selection(2, mode=tag_filters.MATCH_ANY)
        )

        self.assertEqual(self.patient_ids(rows), {"a", "c"})

    def test_ward_filter_limits_the_rendered_branches(self) -> None:
        rows = self.filter(ward_id="2")

        self.assertEqual([ward["ward"]["id"] for ward in rows], ["2"])
        self.assertEqual(self.patient_ids(rows), {"c"})

    def test_show_empty_wards_keeps_a_branch_without_matches(self) -> None:
        rows = self.filter(
            selection=selection(2, mode=tag_filters.MATCH_ALL), show_empty_wards=True
        )

        self.assertEqual([ward["ward"]["id"] for ward in rows], ["1", "2", "3"])
        self.assertEqual(self.patient_ids(rows), {"a", "c"})
        self.assertEqual([ward["patient_count"] for ward in rows], [1, 1, 0])

    def test_patient_count_is_recomputed_from_the_rendered_rows(self) -> None:
        rows = self.filter(selection=selection(2, mode=tag_filters.MATCH_ALL))

        self.assertEqual(rows[0]["patient_count"], 1)
        self.assertEqual(len(rows[0]["patients"]), 1)

    def test_totals_match_the_rendered_rows(self) -> None:
        rows = self.filter(selection=selection(1, 2, mode=tag_filters.MATCH_ALL))

        self.assertEqual(
            ward_tag_overlay.map_totals(rows),
            {"total_patients": 1, "total_wards": 1},
        )
        self.assertEqual(
            ward_tag_overlay.map_totals([]),
            {"total_patients": 0, "total_wards": 0},
        )

    def test_apply_filters_does_not_mutate_the_cached_payload(self) -> None:
        self.filter(
            selection=selection(1, mode=tag_filters.MATCH_ALL), show_empty_wards=True
        )

        self.assertEqual(self.ward_data[0]["patient_count"], 2)
        self.assertEqual(len(self.ward_data[0]["patients"]), 2)
        self.assertEqual(self.ward_data[2]["patients"], [])


class WardTagOverlayProjectionTests(TestCase):
    """R2: requester visibility is applied before serialization and filtering."""

    cirger: MedicalSpecialty
    owner: Any
    public_tag: AllowedTag
    restricted_tag: AllowedTag
    member: Any
    outsider: Any
    patients: list[Patient]

    @classmethod
    def setUpTestData(cls) -> None:
        cls.cirger = MedicalSpecialty.objects.create(
            name="Equipe CIRGER", abbreviation="CIRGER"
        )
        cls.owner = create_navigation_user(
            username="overlay-owner",
            email="overlay-owner@example.com",
            password="overlay-pass",
        )
        cls.public_tag = AllowedTag.objects.create(
            name="Prioridade Global",
            color="#111111",
            created_by=cls.owner,
            updated_by=cls.owner,
        )
        cls.restricted_tag = AllowedTag.objects.create(
            name="Estável CIRGER",
            color="#222222",
            specialty=cls.cirger,
            visibility=AllowedTag.Visibility.RESTRICTED,
            created_by=cls.owner,
            updated_by=cls.owner,
        )
        cls.member = create_navigation_user(
            username="overlay-member",
            email="overlay-member@example.com",
            password="overlay-pass",
        )
        UserSpecialty.objects.create(
            user=cls.member, specialty=cls.cirger, is_active=True
        )
        cls.outsider = create_navigation_user(
            username="overlay-outsider",
            email="overlay-outsider@example.com",
            password="overlay-pass",
        )
        cls.patients = [
            Patient.objects.create(
                name=f"Paciente Overlay {index}",
                birthday="1980-01-01",
                status=Patient.Status.INPATIENT,
                created_by=cls.owner,
                updated_by=cls.owner,
            )
            for index in range(3)
        ]
        for patient in cls.patients:
            Tag.objects.create(
                allowed_tag=cls.public_tag,
                patient=patient,
                created_by=cls.owner,
                updated_by=cls.owner,
            )
        Tag.objects.create(
            allowed_tag=cls.restricted_tag,
            patient=cls.patients[0],
            created_by=cls.owner,
            updated_by=cls.owner,
        )

    def cached_rows(self) -> list[dict[str, Any]]:
        return [
            ward_row(
                "1",
                [
                    patient_row(str(patient.pk), patient.name, tag_ids=(999,))
                    for patient in self.patients
                ],
            )
        ]

    def test_projection_replaces_the_stale_payload_with_live_visible_tags(self) -> None:
        rows = ward_tag_overlay.project_patients(self.cached_rows(), actor=self.member)

        tag_ids = {
            tag["allowed_tag"]["id"]
            for patient in rows[0]["patients"]
            for tag in patient["tags"]
        }
        self.assertEqual(tag_ids, {self.public_tag.pk, self.restricted_tag.pk})

    def test_projection_hides_restricted_metadata_from_an_outsider(self) -> None:
        rows = ward_tag_overlay.project_patients(
            self.cached_rows(), actor=self.outsider
        )

        tag_ids = {
            tag["allowed_tag"]["id"]
            for patient in rows[0]["patients"]
            for tag in patient["tags"]
        }
        self.assertEqual(tag_ids, {self.public_tag.pk})
        self.assertNotIn(self.restricted_tag.name, str(rows))

    def test_projection_queries_do_not_grow_with_the_patient_count(self) -> None:
        one_patient = [
            ward_row(
                "1", [patient_row(str(self.patients[0].pk), self.patients[0].name)]
            )
        ]
        with CaptureQueriesContext(connection) as single:
            ward_tag_overlay.project_patients(one_patient, actor=self.member)
        with CaptureQueriesContext(connection) as many:
            ward_tag_overlay.project_patients(self.cached_rows(), actor=self.member)

        self.assertEqual(len(single), len(many))
        self.assertLessEqual(len(many), 6)

    def test_projection_keeps_the_cached_structure_untouched(self) -> None:
        cached = self.cached_rows()

        ward_tag_overlay.project_patients(cached, actor=self.member)

        self.assertEqual(
            cached[0]["patients"][0]["tags"],
            [{"allowed_tag": {"id": 999, "name": "Tag 999", "color": "#000000"}}],
        )
