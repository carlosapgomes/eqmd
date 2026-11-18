"""S2: catalogue discovery - defaults, ANY/ALL, name search, fragment state."""

from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlsplit

from django.http import QueryDict
from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.models import (
    EqmdCustomUser,
    MedicalSpecialty,
    UserSpecialtyTagPreference,
)
from apps.accounts.services import tag_preferences
from apps.patients.models import AllowedTag
from apps.reports.models import ReportTemplate
from apps.reports.tests.tag_fixtures import (
    join_team,
    make_specialty,
    make_tag,
    make_template,
    make_user,
)

LIST_URL = "reports:template_list"


def link(template: ReportTemplate, tag: AllowedTag) -> None:
    ReportTemplate.tags.through.objects.create(reporttemplate=template, allowedtag=tag)


def make_query(**params) -> QueryDict:
    query = QueryDict("", mutable=True)
    for key, value in params.items():
        values = value if isinstance(value, list) else [value]
        query.setlist(key, [str(item) for item in values])
    return query


class _NativeApplyParser(HTMLParser):
    """Collect successful controls of the discovery form in document order.

    Mimics a browser submitting the form via its Apply button when every
    tag option is deselected: the multi-select contributes no value, an
    unchecked checkbox contributes nothing, and a submit button contributes
    only when it carries a name.
    """

    def __init__(self) -> None:
        super().__init__()
        self.in_form = False
        self.controls: list[tuple[str, str]] = []
        self._select_name: str | None = None
        self._select_options: list[tuple[str, bool]] = []
        self._option_value = ""
        self._option_selected = False

    def handle_starttag(self, tag, attrs) -> None:
        attrs_dict = dict(attrs)
        if tag == "form":
            if "data-discovery-form" in attrs_dict:
                self.in_form = True
            return
        if not self.in_form:
            return
        if tag == "input":
            name = attrs_dict.get("name")
            if not name:
                return
            input_type = (attrs_dict.get("type") or "text").lower()
            if input_type == "checkbox" and "checked" not in attrs_dict:
                return
            self.controls.append((name, attrs_dict.get("value", "")))
        elif tag == "button":
            if (attrs_dict.get("type") or "") == "submit":
                name = attrs_dict.get("name")
                if name:
                    self.controls.append((name, attrs_dict.get("value", "")))
        elif tag == "select":
            self._select_name = attrs_dict.get("name")
            self._select_options = []
        elif tag == "option" and self._select_name is not None:
            self._option_value = attrs_dict.get("value", "")
            self._option_selected = "selected" in attrs_dict

    def handle_endtag(self, tag) -> None:
        if tag == "option" and self._select_name is not None:
            self._select_options.append((self._option_value, self._option_selected))
        elif tag == "select" and self._select_name is not None:
            name = self._select_name
            options = self._select_options
            self._select_name = None
            self._select_options = []
            if name == "tags":
                # Deselected multi-select: a browser submits no tags value.
                return
            if name and options:
                selected = [value for value, is_selected in options if is_selected]
                self.controls.append((name, selected[0] if selected else options[0][0]))
        elif tag == "form":
            self.in_form = False


def native_apply_params(body: str) -> QueryDict:
    """Return the GET parameters a browser sends for a deselected Apply."""
    parser = _NativeApplyParser()
    parser.feed(body)
    params = QueryDict("", mutable=True)
    for key, value in parser.controls:
        params.appendlist(key, value)
    return params


def applied_params(response) -> dict[str, list[str]]:
    """Parse the last-applied canonical state carried on the results root.

    The enhancement builds search and historical-toggle requests from this
    state, never from pending form controls, so unapplied tag/mode changes
    cannot leak into those requests or into the canonical URL.
    """
    match = re.search(r'data-discovery-applied="([^"]*)"', response.content.decode())
    if match is None:
        raise AssertionError("data-discovery-applied attribute missing")
    return parse_qs(html.unescape(match.group(1)), keep_blank_values=True)


class DiscoveryFixturesMixin:
    """Catalogue A={X,Y}, B={X}, C={} plus accented/inactive/private rows."""

    client: Client
    team_a: MedicalSpecialty
    team_b: MedicalSpecialty
    viewer: EqmdCustomUser
    outsider: EqmdCustomUser
    tpl_a: ReportTemplate
    tpl_b: ReportTemplate
    tpl_c: ReportTemplate
    tpl_inactive: ReportTemplate
    tpl_only: ReportTemplate
    tpl_historical: ReportTemplate
    tpl_principal: ReportTemplate
    tpl_private_own: ReportTemplate
    tpl_private_foreign: ReportTemplate
    tag_x: AllowedTag
    tag_y: AllowedTag
    tag_template_only: AllowedTag
    principal_tag: AllowedTag
    restricted_a: AllowedTag
    restricted_b: AllowedTag
    inactive_a: AllowedTag
    archived_a: AllowedTag

    @classmethod
    def setUpTestData(cls) -> None:
        cls.team_a = make_specialty("S2TA")
        cls.team_b = make_specialty("S2TB")
        cls.viewer = make_user("s2-viewer")
        join_team(cls.viewer, cls.team_a)
        cls.outsider = make_user("s2-outsider")
        join_team(cls.outsider, cls.team_b)

        cls.tag_x = make_tag(cls.viewer, "S2 X")
        cls.tag_y = make_tag(cls.viewer, "S2 Y")
        cls.tag_template_only = make_tag(cls.viewer, "S2 Só Template")
        cls.principal_tag = make_tag(
            cls.viewer,
            "S2 Principal",
            specialty=cls.team_a,
            visibility=AllowedTag.Visibility.PUBLIC,
        )
        MedicalSpecialty.objects.filter(pk=cls.team_a.pk).update(
            principal_tag_id=cls.principal_tag.pk
        )
        cls.restricted_a = make_tag(
            cls.viewer,
            "S2 Restrita A",
            specialty=cls.team_a,
            visibility=AllowedTag.Visibility.RESTRICTED,
        )
        cls.restricted_b = make_tag(
            cls.viewer,
            "S2 Restrita B",
            specialty=cls.team_b,
            visibility=AllowedTag.Visibility.RESTRICTED,
        )
        cls.inactive_a = make_tag(
            cls.viewer,
            "S2 Inativa A",
            specialty=cls.team_a,
            visibility=AllowedTag.Visibility.RESTRICTED,
            is_active=False,
        )
        cls.archived_a = make_tag(
            cls.viewer,
            "S2 Arquivada A",
            specialty=cls.team_a,
            visibility=AllowedTag.Visibility.RESTRICTED,
            is_active=False,
            is_deleted=True,
        )

        cls.tpl_a = make_template(cls.viewer, "Avaliação Completa", is_public=True)
        link(cls.tpl_a, cls.tag_x)
        link(cls.tpl_a, cls.tag_y)
        cls.tpl_b = make_template(cls.viewer, "Avaliação Resumida", is_public=True)
        link(cls.tpl_b, cls.tag_x)
        cls.tpl_c = make_template(cls.viewer, "Relatório Simples", is_public=True)
        cls.tpl_inactive = make_template(
            cls.viewer, "Avaliação Inativa", is_public=True, is_active=False
        )
        link(cls.tpl_inactive, cls.tag_x)
        cls.tpl_only = make_template(cls.viewer, "Modelo Só Tags", is_public=True)
        link(cls.tpl_only, cls.tag_template_only)
        cls.tpl_historical = make_template(
            cls.viewer, "Histórico Antigo", is_public=True
        )
        link(cls.tpl_historical, cls.inactive_a)
        link(cls.tpl_historical, cls.archived_a)
        cls.tpl_principal = make_template(
            cls.viewer, "Principal Modelo", is_public=True
        )
        link(cls.tpl_principal, cls.principal_tag)
        cls.tpl_private_own = make_template(
            cls.viewer, "Avaliação Privada Propria", is_public=False
        )
        link(cls.tpl_private_own, cls.tag_y)
        cls.tpl_private_foreign = make_template(
            cls.outsider, "Avaliação Privada Alheia", is_public=False
        )
        link(cls.tpl_private_foreign, cls.tag_x)
        link(cls.tpl_private_foreign, cls.tag_y)

    def setUp(self) -> None:
        self.client.force_login(self.viewer)

    # The viewer has no current specialty unless a test sets one explicitly.
    def set_current(self, specialty: MedicalSpecialty) -> None:
        profile = self.viewer.profile
        profile.current_specialty = specialty
        profile.save(update_fields=["current_specialty"])

    def save_preference(self, tags=(), mode: str = "any"):
        membership = self.viewer.user_specialties.get(specialty=self.team_a)
        preference = UserSpecialtyTagPreference.objects.create(
            membership=membership, mode=mode
        )
        preference.tags.set(list(tags))
        return preference

    def get_list(self, **params):
        return self.client.get(reverse(LIST_URL), params)

    def result_ids(self, response):
        self.assertEqual(response.status_code, 200)
        return [t.pk for t in response.context["object_list"]]

    def all_eligible_ids(self):
        return {
            self.tpl_a.pk,
            self.tpl_b.pk,
            self.tpl_c.pk,
            self.tpl_inactive.pk,
            self.tpl_only.pk,
            self.tpl_historical.pk,
            self.tpl_principal.pk,
            self.tpl_private_own.pk,
        }


class CatalogueMatchingTests(DiscoveryFixturesMixin, TestCase):
    def test_any_matches_union_distinctly(self) -> None:
        ids = self.result_ids(
            self.get_list(tags=[self.tag_x.pk, self.tag_y.pk], tag_mode="any")
        )
        self.assertEqual(
            set(ids),
            {
                self.tpl_a.pk,
                self.tpl_b.pk,
                self.tpl_inactive.pk,
                self.tpl_private_own.pk,
            },
        )
        self.assertEqual(len(ids), len(set(ids)))

    def test_all_requires_every_identity(self) -> None:
        ids = self.result_ids(
            self.get_list(tags=[self.tag_x.pk, self.tag_y.pk], tag_mode="all")
        )
        self.assertEqual(ids, [self.tpl_a.pk])

    def test_duplicate_ids_do_not_duplicate_rows(self) -> None:
        ids = self.result_ids(self.get_list(tags=[self.tag_x.pk, self.tag_x.pk]))
        self.assertEqual(set(ids), {self.tpl_a.pk, self.tpl_b.pk, self.tpl_inactive.pk})
        self.assertEqual(len(ids), len(set(ids)))

    def test_untagged_excluded_from_predicate_and_restored_by_clear(self) -> None:
        filtered = self.result_ids(self.get_list(tags=[self.tag_x.pk]))
        self.assertNotIn(self.tpl_c.pk, filtered)
        cleared_params = parse_qs(
            self.get_list(tags=[self.tag_x.pk]).context["discovery_clear_querystring"],
            keep_blank_values=True,
        )
        cleared = self.result_ids(self.client.get(reverse(LIST_URL), cleared_params))
        self.assertEqual(set(cleared), self.all_eligible_ids())

    def test_inactive_models_and_foreign_private_scope(self) -> None:
        ids = self.result_ids(self.get_list())
        self.assertIn(self.tpl_inactive.pk, ids)
        self.assertNotIn(self.tpl_private_foreign.pk, ids)
        self.assertIn(self.tpl_private_own.pk, ids)
        # Foreign private stays hidden even when its tags match.
        matching = self.result_ids(
            self.get_list(tags=[self.tag_x.pk, self.tag_y.pk], tag_mode="all")
        )
        self.assertNotIn(self.tpl_private_foreign.pk, matching)

    def test_accent_and_case_insensitive_name_search(self) -> None:
        expected = {
            self.tpl_a.pk,
            self.tpl_b.pk,
            self.tpl_inactive.pk,
            self.tpl_private_own.pk,
        }
        for q in ("avaliacao", "AVALIAÇÃO", "  avaliação  "):
            with self.subTest(q=q):
                self.assertEqual(set(self.result_ids(self.get_list(q=q))), expected)

    def test_name_search_is_conjunctive_with_tags(self) -> None:
        ids = self.result_ids(
            self.get_list(q="avaliacao", tags=[self.tag_y.pk], tag_mode="any")
        )
        self.assertEqual(set(ids), {self.tpl_a.pk, self.tpl_private_own.pk})
        ids_all = self.result_ids(
            self.get_list(
                q="avaliacao",
                tags=[self.tag_x.pk, self.tag_y.pk],
                tag_mode="all",
            )
        )
        self.assertEqual(ids_all, [self.tpl_a.pk])

    def test_template_only_tag_matches_and_is_offered(self) -> None:
        ids = self.result_ids(self.get_list(tags=[self.tag_template_only.pk]))
        self.assertEqual(ids, [self.tpl_only.pk])
        response = self.get_list()
        option_ids = [o.tag_id for o in response.context["discovery_tag_options"]]
        self.assertIn(self.tag_template_only.pk, option_ids)

    def test_historical_tags_match_manually(self) -> None:
        for tag in (self.inactive_a, self.archived_a):
            with self.subTest(tag=tag.name):
                ids = self.result_ids(self.get_list(tags=[tag.pk]))
                self.assertEqual(ids, [self.tpl_historical.pk])

    def test_legacy_tag_param_is_manual_any(self) -> None:
        response = self.get_list(tag=self.tag_x.pk)
        selection = response.context["discovery_selection"]
        self.assertTrue(selection.is_manual)
        self.assertEqual(selection.mode, "any")
        self.assertEqual(
            set(self.result_ids(response)),
            {self.tpl_a.pk, self.tpl_b.pk, self.tpl_inactive.pk},
        )

    def test_oversized_name_query_is_generic_400_without_results(self) -> None:
        response = self.get_list(q="x" * 256)
        self.assertEqual(response.status_code, 400)
        body = response.content.decode()
        self.assertNotIn("Avaliação Completa", body)
        self.assertNotIn("Avaliação Privada Alheia", body)


class DiscoveryDefaultsTests(DiscoveryFixturesMixin, TestCase):
    def test_no_specialty_means_no_predicate(self) -> None:
        self.assertEqual(set(self.result_ids(self.get_list())), self.all_eligible_ids())

    def test_principal_fallback_with_any(self) -> None:
        self.set_current(self.team_a)
        response = self.get_list()
        selection = response.context["discovery_selection"]
        self.assertFalse(selection.is_manual)
        self.assertEqual(selection.tag_ids, (self.principal_tag.pk,))
        self.assertEqual(selection.mode, "any")
        self.assertEqual(self.result_ids(response), [self.tpl_principal.pk])
        self.assertContains(response, "Padrão inicial da especialidade")

    def test_saved_preference_applies_tags_and_mode(self) -> None:
        self.set_current(self.team_a)
        self.save_preference((self.tag_x, self.tag_y), mode="all")
        response = self.get_list()
        self.assertEqual(self.result_ids(response), [self.tpl_a.pk])
        self.assertContains(response, "Padrão salvo da especialidade")
        self.assertContains(response, "Todas as selecionadas (E)")

    def test_saved_empty_suppresses_principal(self) -> None:
        self.set_current(self.team_a)
        self.save_preference(())
        response = self.get_list()
        self.assertFalse(response.context["discovery_selection"].has_predicate)
        self.assertEqual(set(self.result_ids(response)), self.all_eligible_ids())
        self.assertContains(response, "Sem filtro de tags (preferência salva)")

    def test_manual_overrides_saved_without_database_write(self) -> None:
        self.set_current(self.team_a)
        preference = self.save_preference((self.tag_x,))
        response = self.get_list(
            tags=[self.tag_y.pk], tag_mode="any", tag_filter="manual"
        )
        self.assertEqual(
            set(self.result_ids(response)),
            {self.tpl_a.pk, self.tpl_private_own.pk},
        )
        preference.refresh_from_db()
        self.assertEqual(
            set(preference.tags.values_list("pk", flat=True)), {self.tag_x.pk}
        )

    def test_unavailable_saved_tag_omitted_with_warning_and_no_rewrite(self) -> None:
        self.set_current(self.team_a)
        preference = self.save_preference((self.tag_x, self.inactive_a))
        response = self.get_list()
        self.assertEqual(
            response.context["discovery_selection"].tag_ids, (self.tag_x.pk,)
        )
        self.assertEqual(
            response.context["discovery_warning"],
            tag_preferences.UNAVAILABLE_DEFAULTS_WARNING,
        )
        self.assertContains(response, tag_preferences.UNAVAILABLE_DEFAULTS_WARNING)
        preference.refresh_from_db()
        self.assertEqual(
            set(preference.tags.values_list("pk", flat=True)),
            {self.tag_x.pk, self.inactive_a.pk},
        )

    def test_all_saved_unavailable_means_no_predicate(self) -> None:
        self.set_current(self.team_a)
        self.save_preference((self.inactive_a,))
        response = self.get_list()
        self.assertFalse(response.context["discovery_selection"].has_predicate)
        self.assertEqual(set(self.result_ids(response)), self.all_eligible_ids())

    def test_invalid_principal_warns_without_predicate(self) -> None:
        self.set_current(self.team_a)
        self.principal_tag.is_active = False
        self.principal_tag.save(update_fields=["is_active"])
        response = self.get_list()
        self.assertFalse(response.context["discovery_selection"].has_predicate)
        self.assertEqual(
            response.context["discovery_warning"],
            tag_preferences.UNAVAILABLE_DEFAULTS_WARNING,
        )

    def test_q_does_not_convert_automatic_defaults_to_manual(self) -> None:
        self.set_current(self.team_a)
        self.save_preference((self.tag_x,))
        response = self.get_list(q="avaliacao")
        selection = response.context["discovery_selection"]
        self.assertFalse(selection.is_manual)
        self.assertEqual(
            set(self.result_ids(response)),
            {self.tpl_a.pk, self.tpl_b.pk, self.tpl_inactive.pk},
        )
        parsed = parse_qs(
            response.context["discovery_filter_querystring"], keep_blank_values=True
        )
        self.assertEqual(parsed, {"q": ["avaliacao"]})

    def test_browsing_never_writes_preferences(self) -> None:
        self.set_current(self.team_a)
        preference = self.save_preference((self.tag_x,))
        before = list(UserSpecialtyTagPreference.objects.values_list("pk", "mode"))
        self.get_list(q="avaliacao")
        self.get_list(tags=[self.tag_y.pk])
        self.get_list(tag_filter="manual")
        self.assertEqual(
            list(UserSpecialtyTagPreference.objects.values_list("pk", "mode")), before
        )
        preference.refresh_from_db()
        self.assertEqual(
            set(preference.tags.values_list("pk", flat=True)), {self.tag_x.pk}
        )


class DiscoveryStateTests(DiscoveryFixturesMixin, TestCase):
    def test_invalid_explicit_filters_are_generic_400(self) -> None:
        cases = (
            {"tags": ["999999"]},
            {"tags": ["not-a-tag"]},
            {"tags": [self.tag_x.pk], "tag_mode": "some"},
            {"tags": [self.restricted_b.pk]},
            {"tag_filter": "automatic"},
            {"tag": "not-a-tag"},
            {"fragment": "results", "tags": ["999999"]},
        )
        for params in cases:
            with self.subTest(params=params):
                response = self.get_list(**params)
                self.assertEqual(response.status_code, 400)
                body = response.content.decode()
                self.assertNotIn("Avaliação Completa", body)
                self.assertNotIn(self.restricted_b.name, body)
                self.assertNotIn("999999", response.content.decode())
                self.assertNotIn("not-a-tag", response.content.decode())

    def test_clear_preserves_q_and_manual_empty_survives_refresh(self) -> None:
        self.set_current(self.team_a)
        self.save_preference((self.tag_x,))
        initial = self.get_list(q="avaliacao")
        cleared_params = parse_qs(
            initial.context["discovery_clear_querystring"], keep_blank_values=True
        )
        self.assertEqual(cleared_params["q"], ["avaliacao"])
        self.assertEqual(cleared_params["tag_filter"], ["manual"])
        self.assertNotIn("tags", cleared_params)
        for _ in range(2):
            response = self.client.get(reverse(LIST_URL), cleared_params)
            selection = response.context["discovery_selection"]
            self.assertTrue(selection.is_manual)
            self.assertFalse(selection.has_predicate)
            self.assertEqual(response.context["discovery_name_query"], "avaliacao")

    def test_reapply_preserves_q_and_restores_defaults(self) -> None:
        self.set_current(self.team_a)
        self.save_preference((self.tag_x,))
        manual = self.get_list(q="avaliacao", tag_filter="manual")
        reapplied_params = parse_qs(
            manual.context["discovery_reapply_querystring"], keep_blank_values=True
        )
        self.assertEqual(reapplied_params["q"], ["avaliacao"])
        self.assertNotIn("tag_filter", reapplied_params)
        self.assertNotIn("tags", reapplied_params)
        response = self.client.get(reverse(LIST_URL), reapplied_params)
        self.assertFalse(response.context["discovery_selection"].is_manual)
        self.assertEqual(
            response.context["discovery_selection"].tag_ids, (self.tag_x.pk,)
        )

    def test_filter_querystring_round_trips_repeated_tags(self) -> None:
        response = self.get_list(
            q="Avaliação & Cia",
            tags=[self.tag_x.pk, self.tag_y.pk],
            tag_mode="all",
        )
        parsed = parse_qs(
            response.context["discovery_filter_querystring"], keep_blank_values=True
        )
        self.assertEqual(parsed["q"], ["Avaliação & Cia"])
        self.assertEqual(
            sorted(parsed["tags"]), sorted([str(self.tag_x.pk), str(self.tag_y.pk)])
        )
        self.assertEqual(parsed["tag_mode"], ["all"])
        self.assertEqual(parsed["tag_filter"], ["manual"])

    def test_fragment_matches_full_page_results(self) -> None:
        params = {"q": "avaliacao", "tags": [self.tag_x.pk], "tag_mode": "any"}
        full = self.get_list(**params)
        fragment = self.get_list(fragment="results", **params)
        self.assertEqual(fragment.status_code, 200)
        self.assertEqual(
            [t.pk for t in fragment.context["object_list"]],
            [t.pk for t in full.context["object_list"]],
        )
        self.assertEqual(
            fragment.context["page_obj"].paginator.count,
            full.context["page_obj"].paginator.count,
        )
        self.assertContains(fragment, "data-discovery-results")

    def test_options_default_active_readable_only(self) -> None:
        response = self.get_list()
        option_ids = [o.tag_id for o in response.context["discovery_tag_options"]]
        for tag in (self.tag_x, self.tag_y, self.restricted_a, self.principal_tag):
            self.assertIn(tag.pk, option_ids)
        for tag in (self.inactive_a, self.archived_a, self.restricted_b):
            self.assertNotIn(tag.pk, option_ids)
        self.assertNotContains(response, self.restricted_b.name)

    def test_historical_options_require_explicit_toggle(self) -> None:
        plain = self.get_list()
        self.assertFalse(plain.context["discovery_include_historical"])
        toggled = self.get_list(include_historical="1")
        self.assertTrue(toggled.context["discovery_include_historical"])
        option_ids = [o.tag_id for o in toggled.context["discovery_tag_options"]]
        self.assertIn(self.inactive_a.pk, option_ids)
        self.assertIn(self.archived_a.pk, option_ids)
        self.assertNotIn(self.restricted_b.pk, option_ids)
        # Toggling alone does not change the tag predicate.
        self.assertEqual(
            toggled.context["discovery_selection"].source,
            plain.context["discovery_selection"].source,
        )

    def test_selected_historical_remains_offered_when_toggle_off(self) -> None:
        response = self.get_list(tags=[self.archived_a.pk])
        options = {o.tag_id: o for o in response.context["discovery_tag_options"]}
        self.assertIn(self.archived_a.pk, options)
        self.assertTrue(options[self.archived_a.pk].is_selected)
        body = response.content.decode()
        self.assertEqual(body.count(f'value="{self.archived_a.pk}"'), 2)
        # Once in the native select and once in the inert options block.
        fragment = self.get_list(tags=[self.archived_a.pk], fragment="results")
        self.assertContains(fragment, f'value="{self.archived_a.pk}"')

    def test_inert_options_block_never_carries_hidden_metadata(self) -> None:
        cases = ((self.viewer, self.restricted_b), (self.outsider, self.restricted_a))
        for actor, hidden in cases:
            self.client.force_login(actor)
            response = self.get_list(include_historical="1")
            match = re.search(
                r"<template data-template-tag-options>(.*?)</template>",
                response.content.decode(),
                re.DOTALL,
            )
            if match is None:
                self.fail("inert options block missing")
            block = match.group(1)
            self.assertNotIn(hidden.name, block)
            self.assertNotIn(f'value="{hidden.pk}"', block)
            self.assertIn(f'value="{self.tag_x.pk}"', block)
        self.client.force_login(self.viewer)

    def test_dynamic_search_markup_present_for_enhancement(self) -> None:
        response = self.get_list()
        body = response.content.decode()
        self.assertIn("data-report-template-discovery", body)
        self.assertIn("data-discovery-q", body)
        self.assertIn("data-discovery-status", body)
        self.assertIn('aria-live="polite"', body)
        self.assertIn("js/report-template-discovery.js", body)
        self.assertIn("data-discovery-results", body)

    def test_zero_results_and_origin_are_visible(self) -> None:
        response = self.get_list(q="zzz-sem-correspondencia")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["object_list"]), [])
        self.assertContains(
            response, "Nenhum modelo corresponde aos filtros atuais"
        )
        self.assertContains(response, "Sem filtro de tag")

    def test_existing_copy_and_view_actions_remain(self) -> None:
        # The outsider does not own the public models, so the read actions show.
        self.client.force_login(self.outsider)
        response = self.get_list()
        self.assertContains(response, "copy-content-btn")
        self.assertContains(response, "templateContentModal-")

    def test_native_apply_with_no_tags_is_manual_empty_from_default(self) -> None:
        # No-JS Apply from a saved-default page with every tag deselected
        # must clear the default (manual-empty), not return it.
        self.set_current(self.team_a)
        self.save_preference((self.tag_x,))
        initial = self.get_list()
        self.assertEqual(
            set(self.result_ids(initial)),
            {self.tpl_a.pk, self.tpl_b.pk, self.tpl_inactive.pk},
        )
        params = native_apply_params(initial.content.decode())
        response = self.client.get(reverse(LIST_URL), params)
        selection = response.context["discovery_selection"]
        self.assertTrue(selection.is_manual)
        self.assertFalse(selection.has_predicate)
        self.assertEqual(set(self.result_ids(response)), self.all_eligible_ids())
        self.assertContains(response, "Sem filtro de tags (personalizado)")

    def test_copy_handler_delegates_from_stable_ancestor(self) -> None:
        # Copy clicks must survive results-fragment replacement, so the
        # handler is delegated instead of bound to initial buttons only.
        response = self.get_list()
        self.assertContains(response, "closest('.copy-content-btn')")

    def test_last_applied_attribute_carries_manual_predicate(self) -> None:
        # Manual-origin seam for P1-A/P1-B: the results root carries the
        # last-applied predicate so search/toggle requests can be built
        # from it (changing only q / include_historical) instead of from
        # pending, unapplied form controls.
        params = {
            "q": "avaliacao",
            "tags": [self.tag_x.pk, self.tag_y.pk],
            "tag_mode": "all",
            "tag_filter": "manual",
        }
        response = self.get_list(**params)
        expected = {
            "q": ["avaliacao"],
            "tags": sorted([str(self.tag_x.pk), str(self.tag_y.pk)]),
            "tag_mode": ["all"],
            "tag_filter": ["manual"],
        }
        parsed = applied_params(response)
        self.assertEqual(sorted(parsed["tags"]), expected["tags"])
        for key in ("q", "tag_mode", "tag_filter"):
            self.assertEqual(parsed[key], expected[key], key)
        self.assertNotIn("include_historical", parsed)
        self.assertNotIn("page", parsed)
        # The fragment carries the same last-applied state (apart from the
        # fragment=results transport parameter itself).
        fragment = self.get_list(fragment="results", **params)
        fragment_applied = applied_params(fragment)
        fragment_applied.pop("fragment", None)
        self.assertEqual(fragment_applied, parsed)
        # A toggle request built from this state (only include_historical
        # added) keeps the applied predicate and results.
        toggled = self.get_list(include_historical="1", **params)
        self.assertEqual(
            toggled.context["discovery_selection"].tag_ids,
            (self.tag_x.pk, self.tag_y.pk),
        )
        self.assertEqual(self.result_ids(toggled), self.result_ids(response))
        # A search request built from this state (only q changed) keeps
        # the applied tags/mode rather than any pending selection.
        searched = self.get_list(
            q="resumida",
            tags=[self.tag_x.pk, self.tag_y.pk],
            tag_mode="all",
            tag_filter="manual",
        )
        self.assertEqual(self.result_ids(searched), [])

    def test_catalogue_actions_and_legacy_tag_urls_keep_separate_scopes(self) -> None:
        response = self.get_list(
            q="avaliacao",
            tags=[self.tag_x.pk, self.tag_y.pk],
            tag_mode="all",
            tag_filter="manual",
            include_historical="1",
        )
        body = response.content.decode()
        for attribute, expected in (
            ("data-discovery-clear", {"tag_filter": ["manual"], "tag_mode": ["any"]}),
            (
                "data-discovery-reapply",
                {"q": ["avaliacao"], "include_historical": ["1"]},
            ),
        ):
            hrefs = re.findall(r'href="([^"]*)"[^>]*' + attribute, body)
            self.assertEqual(len(hrefs), 1)
            self.assertEqual(
                parse_qs(urlsplit(html.unescape(hrefs[0])).query), expected
            )
        self.assertNotContains(response, "data-discovery-remove")
        # Legacy tag-only URLs still preserve q/historical and applied mode.
        legacy_clear = response.context["discovery_clear_querystring"]
        legacy_removals = [
            row["remove_querystring"]
            for row in response.context["discovery_selected_tags"]
        ]
        self.assert_legacy_tag_urls(legacy_clear, legacy_removals)

    def assert_legacy_tag_urls(self, clear: str, removals: list[str]) -> None:
        self.assertEqual(len(removals), 2)
        remaining_ids = []
        for encoded in [clear, *removals]:
            parsed = parse_qs(encoded)
            self.assertEqual(parsed["q"], ["avaliacao"])
            self.assertEqual(parsed["include_historical"], ["1"])
            self.assertEqual(parsed["tag_filter"], ["manual"])
            self.assertEqual(parsed["tag_mode"], ["all"])
            if encoded != clear:
                self.assertEqual(len(parsed["tags"]), 1)
                remaining_ids.extend(parsed["tags"])
            else:
                self.assertNotIn("tags", parsed)
            following = self.client.get(reverse(LIST_URL), parsed)
            self.assertEqual(following.status_code, 200)
            self.assertEqual(following.context["discovery_name_query"], "avaliacao")
            self.assertTrue(following.context["discovery_include_historical"])
        self.assertEqual(
            sorted(remaining_ids), sorted(map(str, (self.tag_x.pk, self.tag_y.pk)))
        )

    def test_last_applied_attribute_keeps_automatic_and_manual_empty(self) -> None:
        # Automatic defaults stay out of the canonical state, so search or
        # toggling from an automatic page cannot become manual; manual-
        # empty keeps its marker/mode so it cannot decay back to defaults.
        self.set_current(self.team_a)
        self.save_preference((self.tag_x,))
        automatic = self.get_list(q="avaliacao")
        self.assertEqual(applied_params(automatic), {"q": ["avaliacao"]})
        manual_empty = self.get_list(q="avaliacao", tag_filter="manual", tag_mode="all")
        parsed = applied_params(manual_empty)
        self.assertEqual(parsed["tag_filter"], ["manual"])
        self.assertEqual(parsed["tag_mode"], ["all"])
        self.assertNotIn("tags", parsed)


class DiscoveryPaginationTests(DiscoveryFixturesMixin, TestCase):
    def setUp(self) -> None:
        super().setUp()
        for index in range(25):
            make_template(self.viewer, f"Paginação {index % 5:02d}", is_public=True)

    def test_bounded_stable_pages_without_duplicates(self) -> None:
        page1 = self.get_list(q="Paginacao", page="1")
        page2 = self.get_list(q="Paginacao", page="2")
        ids1 = [t.pk for t in page1.context["object_list"]]
        ids2 = [t.pk for t in page2.context["object_list"]]
        self.assertEqual(len(ids1), 20)
        self.assertEqual(len(ids2), 5)
        self.assertTrue(set(ids1).isdisjoint(ids2))
        combined = list(page1.context["object_list"]) + list(
            page2.context["object_list"]
        )
        keys = [(t.name, str(t.pk)) for t in combined]
        self.assertEqual(keys, sorted(keys))
        self.assertEqual(page1.context["page_obj"].paginator.count, 25)

    def test_pagination_links_preserve_filters(self) -> None:
        response = self.get_list(q="Paginacao", tags=[self.tag_x.pk], tag_mode="any")
        # Only the 25 paginated templates plus tag-X templates match; use the
        # q-only page for a deterministic link check instead.
        response = self.get_list(q="Paginacao")
        hrefs = re.findall(r'href="\?([^"]*page=2[^"]*)"', response.content.decode())
        self.assertTrue(hrefs)
        parsed = parse_qs(html.unescape(hrefs[0]), keep_blank_values=True)
        self.assertEqual(parsed["q"], ["Paginacao"])
        self.assertEqual(parsed["page"], ["2"])

    def test_pagination_links_preserve_q_and_historical(self) -> None:
        # No-JS canonical semantics for P1-C3: pagination hrefs rendered
        # while include_historical is on carry it (and the current q), so
        # following one after an options-only toggle cannot drop it.
        response = self.get_list(q="Paginacao", include_historical="1", page="1")
        body = response.content.decode()
        hrefs = re.findall(r'href="\?([^"]*page=2[^"]*)"', body)
        self.assertTrue(hrefs)
        parsed = parse_qs(html.unescape(hrefs[0]), keep_blank_values=True)
        self.assertEqual(parsed["q"], ["Paginacao"])
        self.assertEqual(parsed["include_historical"], ["1"])
        self.assertEqual(parsed["page"], ["2"])
        following = self.client.get(reverse(LIST_URL), parsed)
        self.assertEqual(following.status_code, 200)
        self.assertEqual(following.context["page_obj"].number, 2)
        self.assertTrue(following.context["discovery_include_historical"])
        self.assertEqual(applied_params(following).get("include_historical"), ["1"])

    def test_forgiving_page_normalization(self) -> None:
        response = self.get_list(q="Paginacao", page="99")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].number, 2)


class DiscoveryServiceTests(DiscoveryFixturesMixin, TestCase):
    def test_service_exports_and_name_parsing(self) -> None:
        from apps.reports.services import template_discovery

        self.assertEqual(
            template_discovery.parse_name_query(make_query(q="  abc ")), "abc"
        )
        self.assertEqual(template_discovery.parse_name_query(make_query()), "")
        with self.assertRaises(template_discovery.InvalidNameQuery):
            template_discovery.parse_name_query(make_query(q="x" * 256))

    def test_service_base_and_apply(self) -> None:
        from apps.patients.services import tag_filters
        from apps.reports.services import template_discovery

        base = template_discovery.catalogue_base_queryset(self.viewer)
        self.assertIn(self.tpl_inactive.pk, list(base.values_list("pk", flat=True)))
        self.assertNotIn(
            self.tpl_private_foreign.pk, list(base.values_list("pk", flat=True))
        )
        selectable = template_discovery.selectable_base_queryset(self.viewer)
        self.assertNotIn(
            self.tpl_inactive.pk, list(selectable.values_list("pk", flat=True))
        )
        selection = tag_filters.parse_tag_selection(
            self.viewer,
            make_query(tags=[self.tag_x.pk, self.tag_y.pk], tag_mode="all"),
        )
        result = template_discovery.apply_discovery_filters(base, selection, "")
        self.assertEqual(list(result.values_list("pk", flat=True)), [self.tpl_a.pk])

    def test_service_options_and_state(self) -> None:
        from apps.reports.services import template_discovery

        options = template_discovery.discovery_tag_options(
            self.viewer, selected_ids=(self.archived_a.pk,)
        )
        option_ids = [o.tag_id for o in options]
        self.assertIn(self.tag_x.pk, option_ids)
        self.assertIn(self.archived_a.pk, option_ids)
        self.assertNotIn(self.inactive_a.pk, option_ids)
        self.assertNotIn(self.restricted_b.pk, option_ids)
        state = template_discovery.resolve_discovery_state(
            self.viewer, make_query(q="avaliacao")
        )
        self.assertEqual(state.name_query, "avaliacao")
        self.assertEqual(state.error, "")
        bad = template_discovery.resolve_discovery_state(
            self.viewer, make_query(tags=["999999"])
        )
        self.assertTrue(bad.error)


class DiscoveryLanguageAndRecoveryTests(DiscoveryFixturesMixin, TestCase):
    """TFUX S1 R1-R3: canonical wording and filtered-empty recovery."""

    def test_canonical_wording_and_visible_correspondencia(self) -> None:
        response = self.get_list(tags=[self.tag_x.pk], tag_mode="all")
        for text in (
            "Pelo menos uma selecionada (OU)",
            "Todas as selecionadas (E)",
            "Correspondência",
            "Filtro personalizado",
            "Limpar todos os filtros",
            "Usar padrão de tags da especialidade",
            "Mostrar inativas e arquivadas no seletor",
            "Aplicar filtros",
        ):
            self.assertContains(response, text)
        self.assertNotContains(response, "Qualquer tag")
        self.assertNotContains(response, "Incluir tags antigas")
        self.assertNotContains(response, "Limpar tags")
        self.assertNotContains(response, "Reaplicar preferências")

    def test_applied_badges_are_informational(self) -> None:
        response = self.get_list(tags=[self.tag_x.pk])
        self.assertContains(response, "data-active-tag-badge")
        self.assertContains(response, "S2 X")
        self.assertNotContains(response, "data-discovery-remove")

    def test_filtered_zero_explains_no_match_without_first_template_cta(self) -> None:
        response = self.get_list(q="zzz-sem-correspondencia")
        self.assertEqual(list(response.context["object_list"]), [])
        self.assertContains(
            response, "Nenhum modelo corresponde aos filtros atuais"
        )
        self.assertNotContains(response, "Crie o primeiro template")
        self.assertNotContains(response, "Nenhum template encontrado")

    def test_filtered_zero_with_tags_offers_scoped_recovery(self) -> None:
        response = self.get_list(
            q="zzz-sem-correspondencia",
            tags=[self.tag_x.pk],
            tag_mode="any",
        )
        self.assertEqual(list(response.context["object_list"]), [])
        self.assertContains(response, "Nenhum modelo corresponde aos filtros atuais")
        body = response.content.decode()
        empty_start = body.index("Nenhum modelo corresponde aos filtros atuais")
        empty_section = body[empty_start : empty_start + 2000]
        self.assertIn("Use as ações dos filtros acima", empty_section)
        self.assertEqual(body.count("data-discovery-clear"), 1)
        self.assertNotContains(response, "Crie o primeiro template")

    def test_manual_empty_is_unfiltered_and_keeps_all_models(self) -> None:
        response = self.get_list(tag_filter="manual")
        self.assertContains(response, "Sem filtro de tags (personalizado)")
        self.assertEqual(set(self.result_ids(response)), self.all_eligible_ids())
        self.assertNotContains(
            response, "Nenhum modelo corresponde aos filtros atuais"
        )

    def test_saved_empty_wording(self) -> None:
        self.set_current(self.team_a)
        self.save_preference(())
        response = self.get_list()
        self.assertContains(response, "Sem filtro de tags (preferência salva)")
        self.assertEqual(set(self.result_ids(response)), self.all_eligible_ids())


class DiscoveryUnfilteredEmptyTests(TestCase):
    """TFUX S1 R3 guard: genuinely unfiltered empty keeps creation CTA."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.viewer = make_user("s2-empty-viewer")

    def setUp(self) -> None:
        self.client.force_login(self.viewer)

    def test_unfiltered_empty_keeps_creation_cta_for_manager(self) -> None:
        response = self.client.get(reverse(LIST_URL))
        self.assertEqual(list(response.context["object_list"]), [])
        self.assertContains(response, "Nenhum template encontrado")
        self.assertContains(response, "Crie o primeiro template")
        self.assertNotContains(
            response, "Nenhum modelo corresponde aos filtros atuais"
        )
