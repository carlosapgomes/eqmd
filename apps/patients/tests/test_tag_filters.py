"""S7 R1/R2/R4: explicit multi-tag list filters and their URL state.

The shared parser is exercised directly for the repeated/legacy/empty
distinctions, then through the patient list for ANY/ALL result semantics and
for URL preservation across pagination, refresh and badge removal.
"""

from __future__ import annotations

import html
import re
from typing import Any
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth.models import Permission
from django.http import QueryDict
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import (
    MedicalSpecialty,
    UserSpecialty,
    UserSpecialtyTagPreference,
)
from apps.accounts.services import tag_preferences, team_membership
from apps.accounts.tests.helpers import create_navigation_user
from apps.patients.models import AllowedTag, Patient, Tag


def make_user(
    username: str,
    *,
    is_staff: bool = False,
    is_superuser: bool = False,
) -> Any:
    """Create an active account allowed to read the patient list."""
    user = create_navigation_user(
        username=username,
        email=f"{username}@example.com",
        password="tag-filter-pass",
        is_staff=is_staff,
        is_superuser=is_superuser,
    )
    user.user_permissions.add(Permission.objects.get(codename="view_patient"))
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


def make_query(**params: Any) -> QueryDict:
    """Build an immutable-equivalent QueryDict with repeated-value support."""
    query = QueryDict("", mutable=True)
    for key, value in params.items():
        values = value if isinstance(value, list) else [value]
        query.setlist(key, [str(item) for item in values])
    return query


def make_patient(actor: Any, name: str, **overrides: Any) -> Patient:
    return Patient.objects.create(
        name=name,
        birthday="1980-01-01",
        created_by=actor,
        updated_by=actor,
        **overrides,
    )


class TagFilterSelectionFixture(TestCase):
    """Two-team catalogue with public, restricted, inactive and archived rows."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.cirger = make_specialty("CIRGER")
        cls.cardio = make_specialty("CARDIO")
        cls.owner = make_user("tag-filter-owner", is_superuser=True, is_staff=True)
        cls.member = make_user("tag-filter-member")
        join_team(cls.member, cls.cirger)
        join_team(cls.member, cls.cardio)
        cls.outsider = make_user("tag-filter-outsider")
        join_team(cls.outsider, cls.cardio)

        cls.public_tag = make_tag(cls.owner, "Prioridade Global")
        cls.cirger_tag = make_tag(
            cls.owner,
            "Estável CIRGER",
            specialty=cls.cirger,
            visibility=AllowedTag.Visibility.RESTRICTED,
        )
        cls.cardio_tag = make_tag(
            cls.owner,
            "Estável CARDIO",
            specialty=cls.cardio,
            visibility=AllowedTag.Visibility.RESTRICTED,
        )
        cls.cirger_inactive = make_tag(
            cls.owner,
            "Inativa CIRGER",
            specialty=cls.cirger,
            visibility=AllowedTag.Visibility.RESTRICTED,
            is_active=False,
        )
        cls.cirger_archived = make_tag(
            cls.owner,
            "Arquivada CIRGER",
            specialty=cls.cirger,
            visibility=AllowedTag.Visibility.RESTRICTED,
            is_active=False,
            is_deleted=True,
        )
        cls.cardio_archived = make_tag(
            cls.owner,
            "Arquivada CARDIO",
            specialty=cls.cardio,
            visibility=AllowedTag.Visibility.RESTRICTED,
            is_active=False,
            is_deleted=True,
        )

        cls.patient_both = make_patient(
            cls.owner, "Paciente Ambas", status=Patient.Status.OUTPATIENT
        )
        cls.patient_cirger = make_patient(
            cls.owner, "Paciente CIRGER", status=Patient.Status.INPATIENT
        )
        cls.patient_cardio = make_patient(
            cls.owner, "Paciente CARDIO", status=Patient.Status.INPATIENT
        )
        cls.patient_public = make_patient(
            cls.owner, "Paciente Público", status=Patient.Status.OUTPATIENT
        )
        cls.patient_archived = make_patient(
            cls.owner, "Paciente Arquivado", status=Patient.Status.OUTPATIENT
        )

        for patient, tag in (
            (cls.patient_both, cls.cirger_tag),
            (cls.patient_both, cls.cardio_tag),
            (cls.patient_cirger, cls.cirger_tag),
            (cls.patient_cardio, cls.cardio_tag),
            (cls.patient_public, cls.public_tag),
            (cls.patient_archived, cls.cirger_archived),
            (cls.patient_archived, cls.cardio_archived),
            (cls.patient_archived, cls.cirger_inactive),
        ):
            Tag.objects.create(
                allowed_tag=tag,
                patient=patient,
                created_by=cls.owner,
                updated_by=cls.owner,
            )

    def login(self, actor: Any) -> None:
        self.client.force_login(actor)

    def selection(self, query: QueryDict) -> Any:
        from apps.patients.services import tag_filters

        return tag_filters.parse_tag_selection(self.member, query)


class TagFilterParserTests(TagFilterSelectionFixture):
    """R1: one parser preserves repeated, mode, empty and legacy distinctions."""

    def test_empty_query_is_initial_state_without_flag(self) -> None:
        selection = self.selection(make_query())

        self.assertFalse(selection.is_manual)
        self.assertEqual(selection.tag_ids, ())
        self.assertEqual(selection.mode, "any")
        self.assertFalse(selection.has_predicate)

    def test_legacy_single_tag_is_manual_any(self) -> None:
        selection = self.selection(make_query(tag=self.cirger_tag.pk))

        self.assertTrue(selection.is_manual)
        self.assertEqual(selection.tag_ids, (self.cirger_tag.pk,))
        self.assertEqual(selection.mode, "any")
        self.assertTrue(selection.has_predicate)

    def test_present_empty_legacy_tag_is_manual_empty(self) -> None:
        selection = self.selection(make_query(tag=""))

        self.assertTrue(selection.is_manual)
        self.assertEqual(selection.tag_ids, ())
        self.assertFalse(selection.has_predicate)

    def test_manual_marker_without_tags_is_manual_empty(self) -> None:
        selection = self.selection(make_query(tag_filter="manual"))

        self.assertTrue(selection.is_manual)
        self.assertEqual(selection.tag_ids, ())
        self.assertFalse(selection.has_predicate)

    def test_repeated_tags_are_deduplicated_in_order(self) -> None:
        selection = self.selection(
            make_query(tags=[self.cirger_tag.pk, self.cardio_tag.pk, self.cirger_tag.pk])
        )

        self.assertEqual(selection.tag_ids, (self.cirger_tag.pk, self.cardio_tag.pk))
        self.assertTrue(selection.is_manual)

    def test_all_mode_is_preserved(self) -> None:
        selection = self.selection(
            make_query(
                tags=[self.cirger_tag.pk, self.cardio_tag.pk], tag_mode="all"
            )
        )

        self.assertEqual(selection.mode, "all")
        self.assertEqual(selection.mode_label, "Todas as tags")

    def test_tags_take_precedence_over_legacy_tag(self) -> None:
        selection = self.selection(
            make_query(tags=[self.cirger_tag.pk], tag=self.cardio_tag.pk)
        )

        self.assertEqual(selection.tag_ids, (self.cirger_tag.pk,))
        self.assertEqual(selection.mode, "any")

    def test_archived_visible_tag_is_selectable_for_historical_filtering(self) -> None:
        selection = self.selection(make_query(tags=[self.cirger_archived.pk]))

        self.assertEqual(selection.tag_ids, (self.cirger_archived.pk,))
        self.assertEqual(selection.tags[0].lifecycle_state, "archived")

    def test_unknown_id_raises_the_generic_error(self) -> None:
        from apps.patients.services import tag_filters, tag_projection

        with self.assertRaisesMessage(
            tag_projection.InvalidTagFilter,
            tag_projection.INVALID_TAG_FILTER_MESSAGE,
        ):
            tag_filters.parse_tag_selection(
                self.member, make_query(tags=["999999"])
            )

    def test_malformed_id_raises_the_generic_error_without_echo(self) -> None:
        from apps.patients.services import tag_filters, tag_projection

        with self.assertRaisesMessage(
            tag_projection.InvalidTagFilter,
            tag_projection.INVALID_TAG_FILTER_MESSAGE,
        ) as caught:
            tag_filters.parse_tag_selection(
                self.member, make_query(tags=["not-a-tag"])
            )
        self.assertNotIn("not-a-tag", str(caught.exception))

    def test_invalid_mode_raises_the_generic_error(self) -> None:
        from apps.patients.services import tag_filters, tag_projection

        with self.assertRaisesMessage(
            tag_projection.InvalidTagFilter,
            tag_projection.INVALID_TAG_FILTER_MESSAGE,
        ):
            tag_filters.parse_tag_selection(
                self.member, make_query(tags=[self.cirger_tag.pk], tag_mode="some")
            )

    def test_invalid_manual_marker_raises_the_generic_error(self) -> None:
        from apps.patients.services import tag_filters, tag_projection

        with self.assertRaisesMessage(
            tag_projection.InvalidTagFilter,
            tag_projection.INVALID_TAG_FILTER_MESSAGE,
        ):
            tag_filters.parse_tag_selection(
                self.member, make_query(tag_filter="automatic")
            )

    def test_inaccessible_restricted_id_raises_the_generic_error(self) -> None:
        from apps.patients.services import tag_filters, tag_projection

        with self.assertRaisesMessage(
            tag_projection.InvalidTagFilter,
            tag_projection.INVALID_TAG_FILTER_MESSAGE,
        ):
            tag_filters.parse_tag_selection(
                self.outsider, make_query(tags=[self.cirger_archived.pk])
            )


class PatientListMultiTagTests(TagFilterSelectionFixture):
    """R2: ANY/ALL semantics stay conjunctive with existing predicates."""

    def list_ids(self, **params: Any) -> list[Any]:
        self.login(self.member)
        response = self.client.get(reverse("patients:patient_list"), params)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["tag_filter_error"], "")
        return [patient.pk for patient in response.context["patients"]]

    def test_any_returns_union_once(self) -> None:
        ids = self.list_ids(
            tags=[self.cirger_tag.pk, self.cardio_tag.pk], tag_mode="any"
        )

        self.assertEqual(
            sorted(ids),
            sorted(
                [self.patient_both.pk, self.patient_cirger.pk, self.patient_cardio.pk]
            ),
        )
        self.assertEqual(len(ids), len(set(ids)))

    def test_all_requires_every_selected_identity(self) -> None:
        ids = self.list_ids(
            tags=[self.cirger_tag.pk, self.cardio_tag.pk], tag_mode="all"
        )

        self.assertEqual(ids, [self.patient_both.pk])

    def test_repeated_duplicate_ids_do_not_duplicate_rows(self) -> None:
        ids = self.list_ids(tags=[self.cirger_tag.pk, self.cirger_tag.pk])

        self.assertEqual(set(ids), {self.patient_both.pk, self.patient_cirger.pk})
        self.assertEqual(len(ids), len(set(ids)))

    def test_status_predicate_remains_conjunctive(self) -> None:
        ids = self.list_ids(
            tags=[self.cirger_tag.pk, self.cardio_tag.pk],
            tag_mode="all",
            status=str(Patient.Status.INPATIENT),
        )

        self.assertEqual(ids, [])

    def test_legacy_tag_is_any_and_overrides_nothing(self) -> None:
        ids = self.list_ids(tag=self.cirger_tag.pk)

        self.assertEqual(
            sorted(ids), sorted([self.patient_both.pk, self.patient_cirger.pk])
        )

    def test_legacy_empty_tag_is_manual_empty_without_predicate(self) -> None:
        self.login(self.member)
        response = self.client.get(reverse("patients:patient_list"), {"tag": ""})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["tag_filter_is_manual"])
        self.assertFalse(response.context["tag_selection"].has_predicate)
        self.assertEqual(
            {patient.pk for patient in response.context["patients"]},
            {
                self.patient_both.pk,
                self.patient_cirger.pk,
                self.patient_cardio.pk,
                self.patient_public.pk,
                self.patient_archived.pk,
            },
        )

    def test_archived_visible_tag_filters_the_list(self) -> None:
        ids = self.list_ids(tags=[self.cirger_archived.pk])

        self.assertEqual(ids, [self.patient_archived.pk])

    def test_inaccessible_restricted_selection_yields_generic_error(self) -> None:
        self.login(self.outsider)
        response = self.client.get(
            reverse("patients:patient_list"),
            {"tags": [self.cirger_tag.pk]},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["patients"]), [])
        self.assertTrue(response.context["tag_filter_error"])
        self.assertNotIn(str(self.cirger_tag.pk), response.context["tag_filter_error"])
        self.assertNotContains(response, self.cirger_tag.name)

    def test_invalid_mode_yields_generic_error_without_widening(self) -> None:
        self.login(self.member)
        response = self.client.get(
            reverse("patients:patient_list"),
            {"tags": [self.cirger_tag.pk], "tag_mode": "some"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["patients"]), [])
        self.assertTrue(response.context["tag_filter_error"])
        self.assertNotContains(response, self.patient_both.name)

    def test_unknown_selection_yields_generic_error_without_widening(self) -> None:
        self.login(self.member)
        response = self.client.get(
            reverse("patients:patient_list"), {"tags": ["999999"]}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["patients"]), [])
        self.assertTrue(response.context["tag_filter_error"])
        self.assertNotIn("999999", response.context["tag_filter_error"])


class PatientListFilterStateTests(TagFilterSelectionFixture):
    """R4: rendered controls and links preserve the effective filter state."""

    def test_form_renders_repeated_values_marker_and_mode(self) -> None:
        self.login(self.member)
        response = self.client.get(
            reverse("patients:patient_list"),
            {"tags": [self.cirger_tag.pk, self.cardio_tag.pk], "tag_mode": "all"},
        )

        body = response.content.decode()
        self.assertEqual(body.count('name="tags"'), 1)
        self.assertEqual(
            len(re.findall(rf'<option value="{self.cirger_tag.pk}"\s+selected', body)),
            1,
        )
        self.assertEqual(
            len(re.findall(rf'<option value="{self.cardio_tag.pk}"\s+selected', body)),
            1,
        )
        self.assertIn('data-lookup-url=', body)
        self.assertIn('name="tag_filter"', body)
        self.assertIn('value="manual"', body)
        self.assertIn('name="tag_mode"', body)
        self.assertIn('value="all" selected', body)

    def test_filter_querystring_uses_urlencoded_repeated_parameters(self) -> None:
        self.login(self.member)
        response = self.client.get(
            reverse("patients:patient_list"),
            {
                "q": "Paciente & Cia",
                "tags": [self.cirger_tag.pk, self.cardio_tag.pk],
                "tag_mode": "all",
            },
        )

        parsed = parse_qs(response.context["filter_querystring"], keep_blank_values=True)
        self.assertEqual(parsed["q"], ["Paciente & Cia"])
        self.assertEqual(
            sorted(parsed["tags"]), sorted([str(self.cirger_tag.pk), str(self.cardio_tag.pk)])
        )
        self.assertEqual(parsed["tag_mode"], ["all"])
        self.assertEqual(parsed["tag_filter"], ["manual"])

    def test_pagination_link_preserves_repeated_tags_and_mode(self) -> None:
        for index in range(20):
            patient = make_patient(self.owner, f"Paciente Extra {index}")
            for tag in (self.cirger_tag, self.cardio_tag):
                Tag.objects.create(
                    allowed_tag=tag,
                    patient=patient,
                    created_by=self.owner,
                    updated_by=self.owner,
                )

        self.login(self.member)
        response = self.client.get(
            reverse("patients:patient_list"),
            {"tags": [self.cirger_tag.pk, self.cardio_tag.pk], "tag_mode": "all"},
        )

        self.assertTrue(response.context["is_paginated"])
        hrefs = re.findall(r'href="\?([^"]*page=2[^"]*)"', response.content.decode())
        self.assertTrue(hrefs)
        parsed = parse_qs(html.unescape(hrefs[0]), keep_blank_values=True)
        self.assertEqual(
            sorted(parsed["tags"]), sorted([str(self.cirger_tag.pk), str(self.cardio_tag.pk)])
        )
        self.assertEqual(parsed["tag_mode"], ["all"])
        self.assertEqual(parsed["page"], ["2"])

    def test_badge_removal_preserves_the_other_selection(self) -> None:
        self.login(self.member)
        response = self.client.get(
            reverse("patients:patient_list"),
            {"tags": [self.cirger_tag.pk, self.cardio_tag.pk], "tag_mode": "all"},
        )

        badges = {entry["badge"].tag_id: entry for entry in response.context["selected_tags"]}
        parsed = parse_qs(
            badges[self.cirger_tag.pk]["remove_querystring"], keep_blank_values=True
        )
        self.assertEqual(parsed["tags"], [str(self.cardio_tag.pk)])
        self.assertEqual(parsed["tag_mode"], ["all"])
        self.assertEqual(parsed["tag_filter"], ["manual"])

    def test_clear_action_emits_manual_empty_state(self) -> None:
        self.login(self.member)
        response = self.client.get(
            reverse("patients:patient_list"),
            {"tags": [self.cirger_tag.pk], "status": str(Patient.Status.INPATIENT)},
        )

        parsed = parse_qs(
            response.context["clear_tags_querystring"], keep_blank_values=True
        )
        self.assertEqual(parsed["tag_filter"], ["manual"])
        self.assertEqual(parsed["status"], [str(Patient.Status.INPATIENT)])
        self.assertNotIn("tags", parsed)

    def test_manual_empty_state_survives_navigation_links(self) -> None:
        self.login(self.member)
        response = self.client.get(
            reverse("patients:patient_list"),
            {"tag_filter": "manual", "status": str(Patient.Status.OUTPATIENT)},
        )

        self.assertTrue(response.context["tag_filter_is_manual"])
        self.assertEqual(response.context["tag_filter_state_label"], "Sem tags (filtro manual)")
        parsed = parse_qs(
            response.context["filter_querystring"], keep_blank_values=True
        )
        self.assertEqual(parsed["tag_filter"], ["manual"])
        self.assertEqual(parsed["status"], [str(Patient.Status.OUTPATIENT)])
        self.assertNotIn("tags", parsed)
        self.assertNotIn("tag", parsed)

    def test_legacy_bookmark_renders_effective_repeated_parameters(self) -> None:
        self.login(self.member)
        response = self.client.get(
            reverse("patients:patient_list"), {"tag": self.cirger_tag.pk}
        )

        selection = response.context["tag_selection"]
        self.assertTrue(selection.is_manual)
        self.assertEqual(selection.mode, "any")
        parsed = parse_qs(
            response.context["filter_querystring"], keep_blank_values=True
        )
        self.assertEqual(parsed["tags"], [str(self.cirger_tag.pk)])
        self.assertEqual(parsed["tag_mode"], ["any"])
        self.assertEqual(parsed["tag_filter"], ["manual"])

    def test_initial_state_has_no_explicit_tag_parameters(self) -> None:
        self.login(self.member)
        response = self.client.get(reverse("patients:patient_list"))

        selection = response.context["tag_selection"]
        self.assertFalse(selection.is_manual)
        self.assertFalse(selection.has_predicate)
        self.assertEqual(response.context["filter_querystring"], "")


class NoJavaScriptTagStateTests(TagFilterSelectionFixture):
    """R4/D6: the native form resubmits selected tags outside the options list.

    A visible archived tag is reachable through the explicit historical lookup
    but never appears in ``available_tags`` (active tags already used by a
    patient). Without JavaScript the native multi-select is the only transport,
    so it must still carry that identity on the next form submission.
    """

    member: Any
    patient_archived: Patient
    cirger_archived: AllowedTag

    def selected_option_values(self, body: str) -> list[str]:
        """Return the selected values of the native multi-tag select only."""
        select = re.search(r'<select id="tag".*?</select>', body, re.DOTALL)
        if select is None:
            self.fail("native tag select not rendered")
        return re.findall(r'<option value="([^"]+)"\s+selected', select.group(0))

    def test_no_javascript_submit_keeps_selected_archived_tag(self) -> None:
        self.login(self.member)
        list_url = reverse("patients:patient_list")
        filtered = self.client.get(
            list_url,
            {
                "tags": [self.cirger_archived.pk],
                "tag_mode": "any",
                "tag_filter": "manual",
            },
        )
        self.assertEqual(
            [patient.pk for patient in filtered.context["patients"]],
            [self.patient_archived.pk],
        )
        self.assertEqual(
            parse_qs(filtered.context["filter_querystring"], keep_blank_values=True)[
                "tags"
            ],
            [str(self.cirger_archived.pk)],
        )

        options = self.selected_option_values(filtered.content.decode())
        self.assertEqual(options.count(str(self.cirger_archived.pk)), 1)

        followed = self.client.get(
            list_url,
            {
                "q": "Paciente",
                "tags": options,
                "tag_mode": "any",
                "tag_filter": "manual",
            },
        )
        self.assertEqual(
            followed.context["tag_selection"].tag_ids, (self.cirger_archived.pk,)
        )
        self.assertEqual(
            [patient.pk for patient in followed.context["patients"]],
            [self.patient_archived.pk],
        )
        self.assertEqual(
            parse_qs(followed.context["filter_querystring"], keep_blank_values=True)[
                "tags"
            ],
            [str(self.cirger_archived.pk)],
        )


class LegacySingleTagRegressionTests(TagFilterSelectionFixture):
    """S5 regression: legacy single-tag privacy checks must stay green."""

    def test_forged_single_tag_is_denied_for_outsider(self) -> None:
        self.login(self.outsider)
        response = self.client.get(
            reverse("patients:patient_list"), {"tag": self.cirger_tag.pk}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["patients"]), [])
        self.assertTrue(response.context["tag_filter_error"])
        self.assertNotContains(response, self.cirger_tag.name)

    def test_malformed_single_tag_is_denied(self) -> None:
        self.login(self.member)
        response = self.client.get(
            reverse("patients:patient_list"), {"tag": "not-a-tag"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["patients"]), [])
        self.assertTrue(response.context["tag_filter_error"])
        self.assertNotIn("not-a-tag", response.context["tag_filter_error"])


class PatientListTagFilterFlowTests(TagFilterSelectionFixture):
    """R4 journey: search, select two, toggle mode, historical, clear, legacy."""

    def test_mobile_journey_keeps_effective_state(self) -> None:
        self.login(self.member)
        lookup_url = reverse("patients:tag_lookup")

        search = self.client.get(lookup_url, {"q": "Estável"})
        self.assertEqual(search.status_code, 200)
        self.assertEqual(
            {row["name"] for row in search.json()["results"]},
            {self.cirger_tag.name, self.cardio_tag.name},
        )

        list_url = reverse("patients:patient_list")
        both_all = self.client.get(
            list_url,
            {"tags": [self.cirger_tag.pk, self.cardio_tag.pk], "tag_mode": "all"},
        )
        self.assertEqual(
            [patient.pk for patient in both_all.context["patients"]],
            [self.patient_both.pk],
        )
        self.assertEqual(len(both_all.context["selected_tags"]), 2)
        self.assertIn("Todas as tags", both_all.content.decode())

        both_any = self.client.get(
            list_url,
            {"tags": [self.cirger_tag.pk, self.cardio_tag.pk], "tag_mode": "any"},
        )
        self.assertEqual(
            {patient.pk for patient in both_any.context["patients"]},
            {self.patient_both.pk, self.patient_cirger.pk, self.patient_cardio.pk},
        )

        historical = self.client.get(
            lookup_url, {"include_historical": "1", "q": "Arquivada CIRGER"}
        )
        self.assertEqual(historical.status_code, 200)
        self.assertEqual(
            [row["state"] for row in historical.json()["results"]], ["archived"]
        )
        archived_id = historical.json()["results"][0]["id"]

        archived = self.client.get(list_url, {"tags": [archived_id]})
        self.assertEqual(
            [patient.pk for patient in archived.context["patients"]],
            [self.patient_archived.pk],
        )

        cleared = self.client.get(
            list_url, parse_qs(archived.context["clear_tags_querystring"])
        )
        self.assertTrue(cleared.context["tag_filter_is_manual"])
        self.assertFalse(cleared.context["tag_selection"].has_predicate)
        self.assertEqual(len(cleared.context["patients"]), 5)

        refreshed = self.client.get(
            list_url,
            {"tags": [self.cirger_tag.pk, self.cardio_tag.pk], "tag_mode": "all"},
        )
        self.assertEqual(
            refreshed.context["filter_querystring"],
            both_all.context["filter_querystring"],
        )

        legacy = self.client.get(list_url, {"tag": self.cirger_tag.pk})
        self.assertEqual(legacy.context["tag_selection"].mode, "any")
        self.assertEqual(
            {patient.pk for patient in legacy.context["patients"]},
            {self.patient_both.pk, self.patient_cirger.pk},
        )


class SpecialtyPreferenceDefaultTests(TagFilterSelectionFixture):
    """S8 R1/R2/R4: retained defaults, manual precedence and revalidation."""

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.cirger_principal = make_tag(
            cls.owner, "Principal CIRGER", specialty=cls.cirger
        )
        cls.cardio_principal = make_tag(
            cls.owner, "Principal CARDIO", specialty=cls.cardio
        )
        cls.cirger.principal_tag = cls.cirger_principal
        cls.cirger.save(update_fields=["principal_tag"])
        cls.cardio.principal_tag = cls.cardio_principal
        cls.cardio.save(update_fields=["principal_tag"])
        for patient, tag in (
            (cls.patient_cirger, cls.cirger_principal),
            (cls.patient_cardio, cls.cardio_principal),
        ):
            Tag.objects.create(
                allowed_tag=tag,
                patient=patient,
                created_by=cls.owner,
                updated_by=cls.owner,
            )

    def setUp(self) -> None:
        self.set_current(self.member, self.cirger)

    def set_current(self, user: Any, specialty: MedicalSpecialty) -> None:
        profile = user.profile
        profile.current_specialty = specialty
        profile.save(update_fields=["current_specialty"])

    def membership(self, specialty: MedicalSpecialty) -> UserSpecialty:
        return UserSpecialty.objects.get(user=self.member, specialty=specialty)

    def save_preference(
        self, specialty: MedicalSpecialty, tags: tuple[AllowedTag, ...] = (), mode: str = "any"
    ) -> UserSpecialtyTagPreference:
        preference = UserSpecialtyTagPreference.objects.create(
            membership=self.membership(specialty), mode=mode
        )
        preference.tags.set(tags)
        return preference

    def list_response(self, **params: Any) -> Any:
        self.login(self.member)
        return self.client.get(reverse("patients:patient_list"), params)

    def test_first_entry_applies_principal_tag_with_any_mode(self) -> None:
        response = self.list_response()

        selection = response.context["tag_selection"]
        self.assertFalse(selection.is_manual)
        self.assertEqual(selection.tag_ids, (self.cirger_principal.pk,))
        self.assertEqual(selection.mode, "any")
        self.assertEqual(
            [patient.pk for patient in response.context["patients"]],
            [self.patient_cirger.pk],
        )
        self.assertEqual(
            response.context["tag_filter_state_label"],
            "Padrão inicial da especialidade",
        )
        self.assertEqual(response.context["tag_preference_warning"], "")

    def test_saved_preference_replaces_principal_default(self) -> None:
        self.save_preference(self.cirger, (self.cardio_tag,), mode="all")

        response = self.list_response()

        selection = response.context["tag_selection"]
        self.assertEqual(selection.tag_ids, (self.cardio_tag.pk,))
        self.assertEqual(selection.mode, "all")
        self.assertTrue(response.context["tag_preference_has_saved"])
        self.assertEqual(
            {patient.pk for patient in response.context["patients"]},
            {self.patient_both.pk, self.patient_cardio.pk},
        )

    def test_saved_empty_preference_suppresses_principal_fallback(self) -> None:
        self.save_preference(self.cirger)

        response = self.list_response()

        self.assertFalse(response.context["tag_selection"].has_predicate)
        self.assertTrue(response.context["tag_preference_has_saved"])
        self.assertEqual(
            response.context["tag_filter_state_label"],
            "Sem tags (padrão salvo)",
        )
        self.assertEqual(len(response.context["patients"]), 5)
        self.assertNotIn(
            self.cirger_principal.pk,
            response.context["tag_selection"].tag_ids,
        )

    def test_manual_selection_overrides_saved_preference_without_writing(
        self,
    ) -> None:
        preference = self.save_preference(self.cirger, (self.cirger_tag,))

        response = self.list_response(
            tags=[self.public_tag.pk], tag_mode="any", tag_filter="manual"
        )

        selection = response.context["tag_selection"]
        self.assertTrue(selection.is_manual)
        self.assertEqual(selection.tag_ids, (self.public_tag.pk,))
        self.assertEqual(
            set(preference.tags.values_list("pk", flat=True)),
            {self.cirger_tag.pk},
        )
        self.assertFalse(UserSpecialtyTagPreference.objects.filter(
            membership=self.membership(self.cardio)
        ).exists())

    def test_manual_clear_survives_refresh_without_database_write(self) -> None:
        self.save_preference(self.cirger, (self.cirger_tag,))
        initial = self.list_response(status=str(Patient.Status.OUTPATIENT))
        self.assertEqual(
            initial.context["tag_selection"].tag_ids, (self.cirger_tag.pk,)
        )
        preference_count = UserSpecialtyTagPreference.objects.count()

        cleared_params = parse_qs(
            initial.context["clear_tags_querystring"], keep_blank_values=True
        )
        cleared = self.client.get(reverse("patients:patient_list"), cleared_params)
        refreshed = self.client.get(reverse("patients:patient_list"), cleared_params)

        for response in (cleared, refreshed):
            self.assertTrue(response.context["tag_filter_is_manual"])
            self.assertFalse(response.context["tag_selection"].has_predicate)
            self.assertEqual(cleared_params["status"], [str(Patient.Status.OUTPATIENT)])
        self.assertEqual(
            UserSpecialtyTagPreference.objects.count(), preference_count
        )
        self.assertFalse(cleared_params.get("tags"))

    def test_reapply_link_restores_automatic_defaults(self) -> None:
        self.save_preference(self.cirger, (self.cirger_tag,))
        manual = self.list_response(
            tag_filter="manual", status=str(Patient.Status.OUTPATIENT)
        )
        self.assertFalse(manual.context["tag_selection"].has_predicate)

        reapplied_params = parse_qs(
            urlsplit(manual.context["tag_preference_next"]).query,
            keep_blank_values=True,
        )
        reapplied = self.client.get(
            reverse("patients:patient_list"), reapplied_params
        )

        self.assertEqual(
            reapplied.context["tag_selection"].tag_ids, (self.cirger_tag.pk,)
        )
        self.assertFalse(reapplied.context["tag_filter_is_manual"])
        self.assertIn("Reaplicar preferências", manual.content.decode())

    def test_unavailable_saved_tag_is_omitted_with_generic_warning(self) -> None:
        preference = self.save_preference(
            self.cirger, (self.cirger_tag, self.public_tag)
        )
        self.cirger_tag.is_active = False
        self.cirger_tag.save(update_fields=["is_active"])

        response = self.list_response()

        self.assertEqual(
            response.context["tag_selection"].tag_ids, (self.public_tag.pk,)
        )
        self.assertEqual(
            response.context["tag_preference_warning"],
            tag_preferences.UNAVAILABLE_DEFAULTS_WARNING,
        )
        self.assertContains(
            response, tag_preferences.UNAVAILABLE_DEFAULTS_WARNING
        )
        self.assertEqual(
            set(preference.tags.values_list("pk", flat=True)),
            {self.cirger_tag.pk, self.public_tag.pk},
        )

    def test_all_saved_tags_unavailable_means_no_predicate(self) -> None:
        preference = self.save_preference(self.cirger, (self.cirger_tag,))
        self.cirger_tag.is_active = False
        self.cirger_tag.save(update_fields=["is_active"])

        response = self.list_response()

        self.assertFalse(response.context["tag_selection"].has_predicate)
        self.assertEqual(len(response.context["patients"]), 5)
        self.assertContains(
            response, tag_preferences.UNAVAILABLE_DEFAULTS_WARNING
        )
        self.assertEqual(
            list(preference.tags.values_list("pk", flat=True)),
            [self.cirger_tag.pk],
        )

        self.cirger_tag.is_active = True
        self.cirger_tag.save(update_fields=["is_active"])

        restored = self.list_response()

        self.assertEqual(
            restored.context["tag_selection"].tag_ids, (self.cirger_tag.pk,)
        )
        self.assertEqual(restored.context["tag_preference_warning"], "")

    def test_invalid_principal_warns_without_predicate(self) -> None:
        self.cirger_principal.is_active = False
        self.cirger_principal.save(update_fields=["is_active"])

        response = self.list_response()

        self.assertFalse(response.context["tag_selection"].has_predicate)
        self.assertEqual(
            response.context["tag_preference_warning"],
            tag_preferences.UNAVAILABLE_DEFAULTS_WARNING,
        )
        self.assertEqual(len(response.context["patients"]), 5)

    def test_invalid_manual_selection_stays_an_error_with_defaults(self) -> None:
        self.save_preference(self.cirger, (self.cirger_tag,))

        response = self.list_response(tags=["999999"])

        self.assertEqual(list(response.context["patients"]), [])
        self.assertTrue(response.context["tag_filter_error"])
        self.assertFalse(response.context["tag_selection"].has_predicate)

    def test_without_valid_specialty_no_default_is_applied(self) -> None:
        profile = self.member.profile
        profile.current_specialty = None
        profile.save(update_fields=["current_specialty"])

        response = self.list_response()

        self.assertFalse(response.context["tag_selection"].has_predicate)
        self.assertFalse(response.context["tag_filter_is_manual"])
        self.assertEqual(response.context["tag_preference_warning"], "")
        self.assertEqual(len(response.context["patients"]), 5)

    def test_each_specialty_uses_its_own_saved_preference(self) -> None:
        self.save_preference(self.cirger, (self.cirger_tag,))
        self.save_preference(self.cardio, (self.cardio_tag,), mode="all")

        cirger_response = self.list_response()
        self.assertEqual(
            cirger_response.context["tag_selection"].tag_ids,
            (self.cirger_tag.pk,),
        )

        self.set_current(self.member, self.cardio)
        cardio_response = self.client.get(reverse("patients:patient_list"))

        self.assertEqual(
            cardio_response.context["tag_selection"].tag_ids,
            (self.cardio_tag.pk,),
        )
        self.assertEqual(cardio_response.context["tag_selection"].mode, "all")

    def test_revoked_membership_retains_preference_without_using_it(self) -> None:
        preference = self.save_preference(self.cirger, (self.cirger_tag,))
        team_membership.revoke_membership(
            actor=self.owner, membership=self.membership(self.cirger)
        )

        revoked = self.list_response()

        self.assertFalse(revoked.context["tag_selection"].has_predicate)
        self.assertEqual(revoked.context["tag_preference_warning"], "")
        self.assertTrue(
            UserSpecialtyTagPreference.objects.filter(pk=preference.pk).exists()
        )

        membership = self.membership(self.cirger)
        team_membership.grant_membership(
            actor=self.owner, user=self.member, specialty=self.cirger
        )
        self.set_current(self.member, self.cirger)
        rejoined = self.client.get(reverse("patients:patient_list"))

        self.assertEqual(
            rejoined.context["tag_selection"].tag_ids, (self.cirger_tag.pk,)
        )
        self.assertFalse(membership.is_leader)

    def test_save_form_renders_the_effective_selection(self) -> None:
        response = self.list_response()

        bodies = response.content.decode()
        self.assertIn(reverse("apps.accounts:tag_preference_save"), bodies)
        self.assertEqual(
            response.context["tag_preference_specialty"].pk, self.cirger.pk
        )
        self.assertEqual(response.context["tag_preference_mode"], "any")
        self.assertEqual(
            response.context["tag_preference_tags"],
            (self.cirger_principal.pk,),
        )
        self.assertIn('name="specialty_id"', bodies)
        self.assertIn('name="csrfmiddlewaretoken"', bodies)

    def test_automatic_defaults_do_not_enter_the_filter_querystring(self) -> None:
        response = self.list_response(q="Paciente")

        parsed = parse_qs(
            response.context["filter_querystring"], keep_blank_values=True
        )
        self.assertEqual(parsed, {"q": ["Paciente"]})
        self.assertFalse(response.context["tag_filter_is_manual"])
