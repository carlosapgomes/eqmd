"""S9 R1-R4: the cached ward map uses the shared tag filter contract.

The map resolves the same selection/default precedence as the patient list,
applies it to requester-visible live associations on top of the structural
cache, recomputes totals from the rendered rows and keeps the effective state
through the full page, the AJAX tree partial and the empty-ward control. Each
case is exercised against both map variants.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import parse_qs

from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import (
    MedicalSpecialty,
    UserSpecialty,
    UserSpecialtyTagPreference,
)
from apps.accounts.tests.helpers import create_navigation_user
from apps.core.models import WardMappingCache
from apps.patients.models import AllowedTag, Patient, Tag, Ward

CLINICAL_PERMISSIONS = ("view_patient", "change_patient")


def make_user(username: str, *, is_staff: bool = False, is_superuser: bool = False):
    """Create an active account allowed to read the ward map."""
    user = create_navigation_user(
        username=username,
        email=f"{username}@example.com",
        password="ward-map-tag-pass",
        is_staff=is_staff,
        is_superuser=is_superuser,
    )
    user.user_permissions.add(
        *[Permission.objects.get(codename=name) for name in CLINICAL_PERMISSIONS]
    )
    return user


def make_specialty(abbreviation: str) -> MedicalSpecialty:
    return MedicalSpecialty.objects.create(
        name=f"Equipe {abbreviation}", abbreviation=abbreviation
    )


def join_team(user: Any, specialty: MedicalSpecialty) -> UserSpecialty:
    return UserSpecialty.objects.create(user=user, specialty=specialty, is_active=True)


def make_tag(actor: Any, name: str, **overrides: Any) -> AllowedTag:
    return AllowedTag.objects.create(
        name=name, created_by=actor, updated_by=actor, **overrides
    )


def make_patient(actor: Any, name: str, **overrides: Any) -> Patient:
    return Patient.objects.create(
        name=name,
        birthday="1980-01-01",
        created_by=actor,
        updated_by=actor,
        **overrides,
    )


def assign(actor: Any, patient: Patient, tag: AllowedTag) -> Tag:
    return Tag.objects.create(
        allowed_tag=tag, patient=patient, created_by=actor, updated_by=actor
    )


def seed_warm_cache(wards: list[tuple[Ward, list[Patient]]]) -> dict[str, Any]:
    """Write the structural base exactly as the background command does.

    The tag payload is deliberately empty and the cached totals are the global
    ones: the map must rehydrate associations per request and recompute totals
    from the rows it actually renders.
    """
    ward_rows: list[dict[str, Any]] = []
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
    ward_data = {
        "ward_data": ward_rows,
        "total_patients": total_patients,
        "total_wards": len(ward_rows),
        "updated_at": timezone.now().isoformat(),
    }
    filter_data = {
        "all_wards": [
            {"id": str(ward.pk), "name": ward.name, "abbreviation": ward.abbreviation}
            for ward, _patients in wards
        ],
        "available_tags": [],
        "updated_at": timezone.now().isoformat(),
    }
    WardMappingCache.objects.update_or_create(
        cache_key="ward_mapping_full", defaults={"ward_data": ward_data}
    )
    WardMappingCache.objects.update_or_create(
        cache_key="ward_filters", defaults={"ward_data": filter_data}
    )
    return ward_data


class WardMapTagFilterFixture(TestCase):
    """Two team namespaces, one public tag and one archived identity."""

    cirger: MedicalSpecialty
    cardio: MedicalSpecialty
    owner: Any
    member: Any
    outsider: Any
    public_tag: AllowedTag
    cirger_tag: AllowedTag
    cardio_tag: AllowedTag
    archived_tag: AllowedTag
    ward_a: Ward
    ward_b: Ward
    patient_both: Patient
    patient_cirger: Patient
    patient_cardio: Patient
    patient_public: Patient
    patient_archived: Patient
    outpatient_tag: AllowedTag
    outpatient: Patient
    inpatients: list[Patient]

    @classmethod
    def setUpTestData(cls) -> None:
        cls.cirger = make_specialty("CIRGER")
        cls.cardio = make_specialty("CARDIO")
        cls.owner = make_user("ward-map-owner", is_staff=True, is_superuser=True)
        cls.member = make_user("ward-map-member")
        join_team(cls.member, cls.cirger)
        join_team(cls.member, cls.cardio)
        cls.outsider = make_user("ward-map-outsider")
        join_team(cls.outsider, cls.cardio)

        cls.public_tag = make_tag(cls.owner, "Prioridade Global", color="#101010")
        cls.cirger_tag = make_tag(
            cls.owner,
            "Estável CIRGER",
            color="#202020",
            specialty=cls.cirger,
            visibility=AllowedTag.Visibility.RESTRICTED,
        )
        cls.cardio_tag = make_tag(
            cls.owner,
            "Estável CARDIO",
            color="#303030",
            specialty=cls.cardio,
            visibility=AllowedTag.Visibility.RESTRICTED,
        )
        cls.archived_tag = make_tag(
            cls.owner,
            "Arquivada CIRGER",
            color="#404040",
            specialty=cls.cirger,
            visibility=AllowedTag.Visibility.RESTRICTED,
            is_active=False,
            is_deleted=True,
        )
        cls.outpatient_tag = make_tag(cls.owner, "Ambulatorial", color="#505050")

        cls.ward_a = Ward.objects.create(
            name="Ala A", abbreviation="ALA", created_by=cls.owner, updated_by=cls.owner
        )
        cls.ward_b = Ward.objects.create(
            name="Ala B", abbreviation="ALB", created_by=cls.owner, updated_by=cls.owner
        )

        cls.patient_both = make_patient(
            cls.owner,
            "Paciente Ambas",
            status=Patient.Status.INPATIENT,
            ward=cls.ward_a,
            bed="101",
        )
        cls.patient_cirger = make_patient(
            cls.owner,
            "Paciente CIRGER",
            status=Patient.Status.INPATIENT,
            ward=cls.ward_a,
            bed="102",
        )
        cls.patient_cardio = make_patient(
            cls.owner,
            "Paciente CARDIO",
            status=Patient.Status.INPATIENT,
            ward=cls.ward_b,
            bed="201",
        )
        cls.patient_public = make_patient(
            cls.owner,
            "Paciente Público",
            status=Patient.Status.INPATIENT,
            ward=cls.ward_b,
            bed="202",
        )
        cls.patient_archived = make_patient(
            cls.owner,
            "Paciente Arquivado",
            status=Patient.Status.INPATIENT,
            ward=cls.ward_b,
            bed="203",
        )
        cls.outpatient = make_patient(
            cls.owner,
            "Paciente Ambulatório",
            status=Patient.Status.OUTPATIENT,
            ward=cls.ward_b,
            bed="",
        )

        for patient, tag in (
            (cls.patient_both, cls.cirger_tag),
            (cls.patient_both, cls.cardio_tag),
            (cls.patient_cirger, cls.cirger_tag),
            (cls.patient_cardio, cls.cardio_tag),
            (cls.patient_public, cls.public_tag),
            (cls.patient_archived, cls.archived_tag),
            (cls.outpatient, cls.outpatient_tag),
        ):
            assign(cls.owner, patient, tag)

        cls.inpatients = [
            cls.patient_both,
            cls.patient_cirger,
            cls.patient_cardio,
            cls.patient_public,
            cls.patient_archived,
        ]

    def setUp(self) -> None:
        self.warm_ward_data = seed_warm_cache(
            [
                (self.ward_a, [self.patient_both, self.patient_cirger]),
                (
                    self.ward_b,
                    [self.patient_cardio, self.patient_public, self.patient_archived],
                ),
            ]
        )
        self.client.force_login(self.member)

    # -- helpers ---------------------------------------------------------

    def map_url(self) -> str:
        return reverse("patients:patient_map")

    def map_response(self, **params: Any) -> Any:
        return self.client.get(self.map_url(), params)

    def ajax_response(self, **params: Any) -> Any:
        return self.client.get(
            self.map_url(), params, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )

    def rendered_patient_names(self, response: Any) -> set[str]:
        """Return the patient names in the rendered rows of either variant."""
        return {
            patient["patient"]["name"]
            for ward_info in response.context["ward_data"]
            for patient in ward_info["patients"]
        }

    def rendered_tag_ids(self, response: Any) -> set[int]:
        """Return every catalogue id serialized into the rendered rows."""
        return {
            tag["allowed_tag"]["id"]
            for ward_info in response.context["ward_data"]
            for patient in ward_info["patients"]
            for tag in patient["tags"]
        }

    def totals_attribute(self, body: str, attribute: str) -> str:
        match = re.search(rf'{attribute}="(\d+)"', body)
        if match is None:
            self.fail(f"{attribute} missing from the map markup")
        return match.group(1)

    def set_current_specialty(self, specialty: MedicalSpecialty) -> None:
        profile = self.member.profile
        profile.current_specialty = specialty
        profile.save(update_fields=["current_specialty"])

    def save_preference(
        self,
        specialty: MedicalSpecialty,
        tags: tuple[AllowedTag, ...] = (),
        mode: str = "any",
    ) -> UserSpecialtyTagPreference:
        membership = UserSpecialty.objects.get(user=self.member, specialty=specialty)
        preference = UserSpecialtyTagPreference.objects.create(
            membership=membership, mode=mode
        )
        preference.tags.set(tags)
        return preference

    def list_patient_names(self, **params: Any) -> set[str]:
        response = self.client.get(reverse("patients:patient_list"), params)
        return {patient.name for patient in response.context["patients"]}


class WardMapMultiTagParityTests(WardMapTagFilterFixture):
    """R1: one ANY/ALL, manual/clear/default contract shared with the list."""

    def test_any_matches_the_same_inpatients_as_the_list(self) -> None:
        params = {"tags": [self.cirger_tag.pk, self.cardio_tag.pk], "tag_mode": "any"}

        response = self.map_response(**params)

        expected = {
            self.patient_both.name,
            self.patient_cirger.name,
            self.patient_cardio.name,
        }
        self.assertEqual(self.rendered_patient_names(response), expected)
        self.assertTrue(expected <= self.list_patient_names(**params))

    def test_all_requires_every_selected_identity(self) -> None:
        params = {"tags": [self.cirger_tag.pk, self.cardio_tag.pk], "tag_mode": "all"}

        response = self.map_response(**params)

        self.assertEqual(
            self.rendered_patient_names(response), {self.patient_both.name}
        )
        self.assertEqual(self.list_patient_names(**params), {self.patient_both.name})

    def test_legacy_single_tag_is_manual_any_on_the_map(self) -> None:
        response = self.map_response(tag=self.cirger_tag.pk)

        selection = response.context["tag_selection"]
        self.assertTrue(selection.is_manual)
        self.assertEqual(selection.mode, "any")
        self.assertEqual(
            self.rendered_patient_names(response),
            {self.patient_both.name, self.patient_cirger.name},
        )

    def test_manual_clear_survives_a_map_refresh(self) -> None:
        cleared = self.map_response(tag_filter="manual")

        self.assertTrue(cleared.context["tag_filter_is_manual"])
        self.assertFalse(cleared.context["tag_selection"].has_predicate)
        self.assertEqual(
            self.rendered_patient_names(cleared),
            {patient.name for patient in self.inpatients},
        )
        parsed = parse_qs(cleared.context["filter_querystring"], keep_blank_values=True)
        self.assertEqual(parsed["tag_filter"], ["manual"])
        self.assertNotIn("tags", parsed)

    def test_initial_entry_applies_the_shared_saved_preference(self) -> None:
        self.set_current_specialty(self.cirger)
        self.save_preference(
            self.cirger, (self.cirger_tag, self.cardio_tag), mode="all"
        )

        map_response = self.map_response()
        list_response = self.client.get(reverse("patients:patient_list"))

        self.assertEqual(
            map_response.context["tag_selection"].tag_ids,
            list_response.context["tag_selection"].tag_ids,
        )
        self.assertEqual(map_response.context["tag_selection"].mode, "all")
        self.assertEqual(
            map_response.context["tag_filter_state_label"],
            "Padrão salvo da especialidade",
        )
        self.assertEqual(
            self.rendered_patient_names(map_response), {self.patient_both.name}
        )

    def test_saved_empty_preference_suppresses_the_principal_fallback(self) -> None:
        self.set_current_specialty(self.cirger)
        self.cirger.principal_tag = self.cirger_tag
        self.cirger.save(update_fields=["principal_tag"])
        self.save_preference(self.cirger, ())

        response = self.map_response()

        self.assertFalse(response.context["tag_selection"].has_predicate)
        self.assertEqual(
            self.rendered_patient_names(response),
            {patient.name for patient in self.inpatients},
        )

    def test_reapply_drops_the_manual_marker_on_the_map(self) -> None:
        response = self.map_response(tags=[self.cirger_tag.pk], q="Paciente")

        parsed = parse_qs(
            response.context["reapply_tags_querystring"], keep_blank_values=True
        )
        self.assertNotIn("tags", parsed)
        self.assertNotIn("tag_filter", parsed)
        self.assertEqual(parsed["q"], ["Paciente"])

    def test_archived_visible_tag_filters_the_map_historically(self) -> None:
        response = self.map_response(tags=[self.archived_tag.pk])

        self.assertEqual(
            self.rendered_patient_names(response), {self.patient_archived.name}
        )
        self.assertEqual(response.context["selected_tag_ids"], (self.archived_tag.pk,))
        self.assertNotIn(
            self.archived_tag.pk,
            [badge.tag_id for badge in response.context["available_tags"]],
        )

    def test_inaccessible_selection_is_a_generic_error_without_rows(self) -> None:
        self.client.force_login(self.outsider)

        response = self.map_response(tags=[self.cirger_tag.pk])

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["tag_filter_error"])
        self.assertEqual(list(response.context["ward_data"]), [])
        self.assertEqual(response.context["total_patients"], 0)
        self.assertEqual(response.context["total_wards"], 0)
        body = response.content.decode()
        self.assertNotIn(self.cirger_tag.name, body)
        self.assertNotIn(
            str(self.cirger_tag.pk), str(response.context["tag_filter_error"])
        )


class WardMapLiveOverlayTests(WardMapTagFilterFixture):
    """R2: the warm base cache cannot delay assignment or lifecycle changes."""

    def test_new_association_appears_without_rebuilding_the_cache(self) -> None:
        assign(self.owner, self.patient_cirger, self.public_tag)

        response = self.map_response(tags=[self.public_tag.pk])

        self.assertEqual(
            self.rendered_patient_names(response),
            {self.patient_cirger.name, self.patient_public.name},
        )
        self.assertIn(self.public_tag.pk, self.rendered_tag_ids(response))

    def test_removed_association_disappears_without_rebuilding_the_cache(self) -> None:
        Tag.objects.filter(
            patient=self.patient_cirger, allowed_tag=self.cirger_tag
        ).delete()

        response = self.map_response(tags=[self.cirger_tag.pk])

        self.assertEqual(
            self.rendered_patient_names(response), {self.patient_both.name}
        )

    def test_archived_tag_keeps_its_labelled_association(self) -> None:
        AllowedTag.all_objects.filter(pk=self.public_tag.pk).update(
            is_active=False, is_deleted=True
        )

        response = self.map_response()

        body = response.content.decode()
        self.assertIn(self.public_tag.name, body)
        self.assertIn("Arquivada", body)
        self.assertNotIn(
            self.public_tag.pk,
            [badge.tag_id for badge in response.context["available_tags"]],
        )

    def test_reclassified_tag_leaves_the_ajax_variant_immediately(self) -> None:
        self.client.force_login(self.outsider)
        AllowedTag.all_objects.filter(pk=self.public_tag.pk).update(
            visibility=AllowedTag.Visibility.RESTRICTED, specialty=self.cirger
        )

        response = self.ajax_response()

        self.assertNotIn(self.public_tag.name, response.content.decode())
        self.assertNotIn(self.public_tag.pk, self.rendered_tag_ids(response))

    def test_warm_cache_payload_is_never_mutated_by_a_filtered_request(self) -> None:
        self.map_response(tags=[self.cirger_tag.pk], tag_mode="all")

        self.assertEqual(
            WardMappingCache.objects.get(cache_key="ward_mapping_full").ward_data,
            self.warm_ward_data,
        )


class WardMapTotalsAndNavigationTests(WardMapTagFilterFixture):
    """R3: totals, links and the AJAX partial reflect the filtered rows."""

    def test_filtered_header_totals_match_the_rendered_rows(self) -> None:
        response = self.map_response(tags=[self.cirger_tag.pk])

        body = response.content.decode()
        self.assertEqual(response.context["total_patients"], 2)
        self.assertEqual(response.context["total_wards"], 1)
        self.assertEqual(self.totals_attribute(body, "data-total-patients"), "2")
        self.assertEqual(self.totals_attribute(body, "data-total-wards"), "1")
        self.assertEqual(response.context["ward_data"][0]["patient_count"], 2)

    def test_ajax_tree_variant_reports_filtered_totals_and_rows(self) -> None:
        response = self.ajax_response(tags=[self.cirger_tag.pk])

        body = response.content.decode()
        self.assertEqual(self.totals_attribute(body, "data-total-patients"), "2")
        self.assertEqual(self.totals_attribute(body, "data-total-wards"), "1")
        self.assertEqual(
            self.rendered_patient_names(response),
            {self.patient_both.name, self.patient_cirger.name},
        )

    def test_ajax_tree_variant_keeps_an_explicit_clear_state(self) -> None:
        response = self.ajax_response(tag_filter="manual")

        self.assertTrue(response.context["tag_filter_is_manual"])
        self.assertEqual(len(response.context["ward_data"]), 2)
        self.assertEqual(
            self.totals_attribute(response.content.decode(), "data-total-patients"), "5"
        )

    def test_empty_ward_control_retains_the_effective_filters(self) -> None:
        response = self.map_response(
            tags=[self.cardio_tag.pk], tag_mode="all", show_empty_wards="true"
        )

        ward_ids = [
            ward_info["ward"]["id"] for ward_info in response.context["ward_data"]
        ]
        self.assertEqual(ward_ids, [str(self.ward_a.pk), str(self.ward_b.pk)])
        self.assertEqual(
            self.rendered_patient_names(response),
            {self.patient_both.name, self.patient_cardio.name},
        )
        self.assertEqual(response.context["total_patients"], 2)
        self.assertEqual(response.context["total_wards"], 2)
        parsed = parse_qs(
            response.context["filter_querystring"], keep_blank_values=True
        )
        self.assertEqual(parsed["tags"], [str(self.cardio_tag.pk)])
        self.assertEqual(parsed["tag_mode"], ["all"])
        self.assertEqual(parsed["tag_filter"], ["manual"])
        self.assertEqual(parsed["show_empty_wards"], ["true"])

    def test_form_renders_the_shared_selector_state(self) -> None:
        response = self.map_response(
            tags=[self.cirger_tag.pk, self.cardio_tag.pk], tag_mode="all"
        )

        body = response.content.decode()
        self.assertEqual(body.count('name="tags"'), 1)
        self.assertIn("data-lookup-url=", body)
        self.assertIn('name="tag_filter"', body)
        self.assertIn('value="manual"', body)
        self.assertIn('name="tag_mode"', body)
        self.assertIn('value="all" selected', body)
        self.assertIn('name="show_empty_wards"', body)
        # Compact selector hooks shared with the patient list (S1 R3).
        self.assertIn('aria-controls="tag-search-results"', body)
        self.assertIn('id="tag-search-results"', body)
        self.assertIn('aria-atomic="true"', body)

    def test_refresh_querystring_preserves_every_effective_predicate(self) -> None:
        response = self.map_response(
            q="Paciente",
            ward=str(self.ward_a.pk),
            tags=[self.cirger_tag.pk],
            tag_mode="all",
            show_empty_wards="true",
        )

        parsed = parse_qs(
            response.context["filter_querystring"], keep_blank_values=True
        )
        self.assertEqual(parsed["q"], ["Paciente"])
        self.assertEqual(parsed["ward"], [str(self.ward_a.pk)])
        self.assertEqual(parsed["tags"], [str(self.cirger_tag.pk)])
        self.assertEqual(parsed["tag_mode"], ["all"])
        self.assertEqual(parsed["tag_filter"], ["manual"])
        self.assertEqual(parsed["show_empty_wards"], ["true"])

    def test_badge_removal_keeps_the_other_map_selection(self) -> None:
        response = self.map_response(
            tags=[self.cirger_tag.pk, self.cardio_tag.pk], tag_mode="all"
        )

        badges = {
            entry["badge"].tag_id: entry for entry in response.context["selected_tags"]
        }
        parsed = parse_qs(
            badges[self.cirger_tag.pk]["remove_querystring"], keep_blank_values=True
        )
        self.assertEqual(parsed["tags"], [str(self.cardio_tag.pk)])
        self.assertEqual(parsed["tag_mode"], ["all"])
        self.assertEqual(parsed["tag_filter"], ["manual"])


class WardMapEligibilityAndStateTests(WardMapTagFilterFixture):
    """R4: inpatient eligibility and distinguishable empty/invalid/stale states."""

    def test_outpatient_tag_yields_zero_map_rows_but_list_results(self) -> None:
        response = self.map_response(tags=[self.outpatient_tag.pk])

        self.assertEqual(list(response.context["ward_data"]), [])
        self.assertEqual(response.context["total_patients"], 0)
        self.assertEqual(response.context["total_wards"], 0)
        self.assertNotIn(self.outpatient.name, response.content.decode())
        self.assertIn(
            self.outpatient.name, self.list_patient_names(tags=[self.outpatient_tag.pk])
        )

    def test_unavailable_saved_default_warns_without_hiding_patients(self) -> None:
        self.set_current_specialty(self.cirger)
        AllowedTag.all_objects.filter(pk=self.cardio_tag.pk).update(is_active=False)
        self.save_preference(self.cirger, (self.cardio_tag,))

        response = self.map_response()

        self.assertFalse(response.context["tag_selection"].has_predicate)
        self.assertTrue(response.context["tag_preference_warning"])
        self.assertEqual(
            self.rendered_patient_names(response),
            {patient.name for patient in self.inpatients},
        )
        self.assertIn("indisponíveis", response.content.decode())

    def test_missing_cache_reports_updating_distinct_from_zero_results(self) -> None:
        WardMappingCache.objects.all().delete()

        response = self.map_response(tags=[self.cirger_tag.pk])

        self.assertFalse(response.context["from_cache"])
        self.assertTrue(response.context["updating"])
        body = response.content.decode()
        self.assertIn("sendo atualizados", body)
        self.assertNotIn("Nenhum paciente encontrado", body)

    def test_invalid_selection_is_distinct_from_a_zero_result_filter(self) -> None:
        invalid = self.map_response(tags=[self.cirger_tag.pk, "999999"])
        empty = self.map_response(tags=[self.outpatient_tag.pk])

        invalid_body = invalid.content.decode()
        empty_body = empty.content.decode()
        self.assertTrue(invalid.context["tag_filter_error"])
        self.assertIn("Filtro de tag inválido.", invalid_body)
        self.assertNotIn("Nenhum paciente encontrado", invalid_body)
        self.assertNotIn("Filtro de tag inválido.", empty_body)
        self.assertIn("Nenhum paciente encontrado", empty_body)

    def test_tree_only_variant_distinguishes_zero_results(self) -> None:
        response = self.ajax_response(tags=[self.outpatient_tag.pk])

        body = response.content.decode()
        self.assertIn("Nenhum paciente encontrado", body)
        self.assertEqual(self.totals_attribute(body, "data-total-patients"), "0")
