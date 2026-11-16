"""S3: template selection lookup and bounded report-creation selector.

Covers the D6 contract: authenticated selectable lookup sharing S2
semantics (active public-or-own only), safe projected payloads, pinned
still-authorized selections outside results, generic rejection of
unavailable choices, and a bounded clinical-form widget whose validation
queryset stays complete.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.models import (
    EqmdCustomUser,
    MedicalSpecialty,
    UserSpecialtyTagPreference,
)
from apps.patients.models import AllowedTag, Patient
from apps.reports.models import Report, ReportTemplate
from apps.reports.tests.tag_fixtures import (
    join_team,
    make_specialty,
    make_tag,
    make_template,
    make_user,
)

SELECT_URL = "reports:template_select"
CREATE_URL = "reports:report_create"
LIST_URL = "reports:template_list"


def link(template, tag):
    ReportTemplate.tags.through.objects.create(reporttemplate=template, allowedtag=tag)


class _SelectParser(HTMLParser):
    """Collect options of the clinical template select and form nesting."""

    def __init__(self):
        super().__init__()
        self.options = []  # (value, label, selected)
        self._in_template_select = False
        self._option = None
        self.form_stack = []
        self.nested_form = False
        self.filter_inside_clinical = False
        self.clinical_inside_filter = False
        self._in_filter_form = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "form":
            if self.form_stack:
                self.nested_form = True
            is_filter = "data-discovery-form" in attrs_dict
            if is_filter and self.form_stack:
                self.filter_inside_clinical = True
            if self.form_stack and not is_filter and self._in_filter_form:
                self.clinical_inside_filter = True
            self.form_stack.append(attrs_dict)
            if is_filter:
                self._in_filter_form = True
        if tag == "select" and attrs_dict.get("id") == "id_template":
            self._in_template_select = True
        if tag == "option" and self._in_template_select:
            self._option = {
                "value": attrs_dict.get("value", ""),
                "selected": "selected" in attrs_dict,
                "label": "",
            }

    def handle_data(self, data):
        if self._option is not None:
            self._option["label"] += data

    def handle_endtag(self, tag):
        if tag == "option" and self._option is not None:
            self.options.append(
                (
                    self._option["value"],
                    self._option["label"].strip(),
                    self._option["selected"],
                )
            )
            self._option = None
        if tag == "select":
            self._in_template_select = False
        if tag == "form" and self.form_stack:
            popped = self.form_stack.pop()
            if "data-discovery-form" in popped:
                self._in_filter_form = False


def parse_select(body: str) -> _SelectParser:
    parser = _SelectParser()
    parser.feed(body)
    return parser


class SelectionFixturesMixin:
    client: Client
    viewer: EqmdCustomUser
    outsider: EqmdCustomUser
    team_a: MedicalSpecialty
    team_b: MedicalSpecialty
    patient: Patient
    tpl_a: ReportTemplate
    tpl_b: ReportTemplate
    tpl_c: ReportTemplate
    tpl_inactive: ReportTemplate
    tpl_historical: ReportTemplate
    tpl_principal: ReportTemplate
    tpl_private_own: ReportTemplate
    tpl_private_foreign: ReportTemplate
    tag_x: AllowedTag
    tag_y: AllowedTag
    principal_tag: AllowedTag
    restricted_a: AllowedTag
    restricted_b: AllowedTag
    inactive_a: AllowedTag
    archived_a: AllowedTag

    @classmethod
    def setUpTestData(cls):
        cls.team_a = make_specialty("S3TA")
        cls.team_b = make_specialty("S3TB")
        cls.viewer = make_user("s3-viewer")
        join_team(cls.viewer, cls.team_a)
        cls.outsider = make_user("s3-outsider")
        join_team(cls.outsider, cls.team_b)

        cls.tag_x = make_tag(cls.viewer, "S3 X")
        cls.tag_y = make_tag(cls.viewer, "S3 Y")
        cls.principal_tag = make_tag(
            cls.viewer,
            "S3 Principal",
            specialty=cls.team_a,
            visibility=AllowedTag.Visibility.PUBLIC,
        )
        from apps.accounts.models import MedicalSpecialty

        MedicalSpecialty.objects.filter(pk=cls.team_a.pk).update(
            principal_tag_id=cls.principal_tag.pk
        )
        cls.restricted_a = make_tag(
            cls.viewer,
            "S3 Restrita A",
            specialty=cls.team_a,
            visibility=AllowedTag.Visibility.RESTRICTED,
        )
        cls.restricted_b = make_tag(
            cls.viewer,
            "S3 Restrita B",
            specialty=cls.team_b,
            visibility=AllowedTag.Visibility.RESTRICTED,
        )
        cls.inactive_a = make_tag(
            cls.viewer,
            "S3 Inativa A",
            specialty=cls.team_a,
            visibility=AllowedTag.Visibility.RESTRICTED,
            is_active=False,
        )
        cls.archived_a = make_tag(
            cls.viewer,
            "S3 Arquivada A",
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

        cls.patient = Patient.objects.create(
            name="S3 Test Patient",
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            created_by=cls.viewer,
            updated_by=cls.viewer,
            current_record_number="S3REC123",
        )

    def setUp(self):
        self.client.force_login(self.viewer)

    def set_current(self, specialty):
        profile = self.viewer.profile
        profile.current_specialty = specialty
        profile.save(update_fields=["current_specialty"])

    def save_preference(self, tags=(), mode="any"):
        membership = self.viewer.user_specialties.get(specialty=self.team_a)
        preference = UserSpecialtyTagPreference.objects.create(
            membership=membership, mode=mode
        )
        preference.tags.set(list(tags))
        return preference

    def get_lookup(self, **params):
        return self.client.get(reverse(SELECT_URL), params)

    def lookup_ids(self, **params):
        response = self.get_lookup(**params)
        assert response.status_code == 200, response.content
        return [item["id"] for item in response.json()["results"]]

    def active_ids(self):
        return {
            str(self.tpl_a.pk),
            str(self.tpl_b.pk),
            str(self.tpl_c.pk),
            str(self.tpl_historical.pk),
            str(self.tpl_principal.pk),
            str(self.tpl_private_own.pk),
        }

    def create_url(self, **params):
        return reverse(CREATE_URL, kwargs={"patient_id": self.patient.pk})


class TemplateSelectionLookupTests(SelectionFixturesMixin, TestCase):
    def test_anonymous_is_redirected_to_login(self):
        self.client.logout()
        response = self.client.get(reverse(SELECT_URL))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_response_shape_is_bounded_and_metadata_safe(self):
        response = self.get_lookup()
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(
            set(payload),
            {
                "results",
                "count",
                "page",
                "num_pages",
                "has_next",
                "has_previous",
                "filter",
                "tag_options",
                "retained_tag_options",
                "selected",
                "selection_unavailable",
            },
        )
        self.assertEqual(payload["count"], len(self.active_ids()))
        self.assertEqual(payload["page"], 1)
        self.assertEqual(payload["num_pages"], 1)
        self.assertFalse(payload["has_next"])
        self.assertFalse(payload["has_previous"])
        self.assertIsNone(payload["selected"])
        self.assertFalse(payload["selection_unavailable"])
        self.assertEqual(
            set(payload["filter"]), {"source", "mode", "selected_tags", "warning"}
        )
        self.assertEqual(payload["filter"]["warning"], "")
        for item in payload["results"]:
            self.assertEqual(set(item), {"id", "name", "tags"})
            for tag in item["tags"]:
                self.assertEqual(
                    set(tag),
                    {
                        "tag_id",
                        "name",
                        "display_name",
                        "color",
                        "state",
                        "state_label",
                        "team_abbreviation",
                        "is_restricted",
                    },
                )
        for option in payload["tag_options"]:
            self.assertEqual(
                set(option),
                {
                    "tag_id",
                    "display_name",
                    "state_label",
                    "is_selected",
                    "is_historical",
                },
            )
        # No retained request: no authorized retained projection.
        self.assertEqual(payload["retained_tag_options"], [])
        body = response.content.decode()
        self.assertNotIn("markdown_body", body)
        self.assertNotIn(self.tpl_a.markdown_body, body)
        self.assertNotIn("markdown", body.lower().replace("markdown_body", ""))
        self.assertEqual(response.get("Cache-Control"), "no-store")

    def test_active_public_or_own_only(self):
        ids = set(self.lookup_ids())
        self.assertEqual(ids, self.active_ids())
        self.assertNotIn(str(self.tpl_inactive.pk), ids)
        self.assertNotIn(str(self.tpl_private_foreign.pk), ids)

    def test_parity_with_catalogue_for_active_models(self):
        for params in (
            {},
            {"tags": [self.tag_x.pk, self.tag_y.pk], "tag_mode": "any"},
            {"tags": [self.tag_x.pk, self.tag_y.pk], "tag_mode": "all"},
            {"q": "avaliacao"},
            {"q": "AVALIAÇÃO", "tags": [self.tag_y.pk]},
        ):
            with self.subTest(params=params):
                catalogue = self.client.get(reverse(LIST_URL), params)
                catalogue_ids = {str(t.pk) for t in catalogue.context["object_list"]}
                lookup_ids = set(self.lookup_ids(**params))
                # Catalogue also lists the inactive model; selector drops it.
                self.assertEqual(
                    lookup_ids,
                    catalogue_ids - {str(self.tpl_inactive.pk)},
                )

    def test_bounded_twenty_per_page(self):
        for index in range(25):
            make_template(self.viewer, f"S3 Página {index:02d}", is_public=True)
        page1 = self.get_lookup(q="S3 Pagina")
        payload1 = page1.json()
        self.assertEqual(payload1["count"], 25)
        self.assertEqual(len(payload1["results"]), 20)
        self.assertTrue(payload1["has_next"])
        self.assertEqual(payload1["num_pages"], 2)
        page2 = self.get_lookup(q="S3 Pagina", page="2")
        payload2 = page2.json()
        self.assertEqual(len(payload2["results"]), 5)
        self.assertFalse(payload2["has_next"])
        self.assertTrue(payload2["has_previous"])
        ids = [i["id"] for i in payload1["results"] + payload2["results"]]
        self.assertEqual(len(ids), len(set(ids)))
        forgiving = self.get_lookup(q="S3 Pagina", page="99")
        self.assertEqual(forgiving.json()["page"], 2)

    def test_defaults_saved_principal_empty_and_manual(self):
        # No specialty: no predicate.
        payload = self.get_lookup().json()
        self.assertEqual({i["id"] for i in payload["results"]}, self.active_ids())
        # Principal fallback.
        self.set_current(self.team_a)
        payload = self.get_lookup().json()
        self.assertEqual(
            [i["id"] for i in payload["results"]], [str(self.tpl_principal.pk)]
        )
        self.assertEqual(payload["filter"]["source"], "principal")
        # Saved preference with mode.
        self.save_preference((self.tag_x, self.tag_y), mode="all")
        payload = self.get_lookup().json()
        self.assertEqual([i["id"] for i in payload["results"]], [str(self.tpl_a.pk)])
        self.assertEqual(payload["filter"]["source"], "saved")
        self.assertEqual(payload["filter"]["mode"], "all")
        self.assertEqual(
            {t["tag_id"] for t in payload["filter"]["selected_tags"]},
            {self.tag_x.pk, self.tag_y.pk},
        )
        # Manual overrides saved.
        payload = self.get_lookup(
            tags=[self.tag_y.pk], tag_filter="manual", tag_mode="any"
        ).json()
        self.assertEqual(
            {i["id"] for i in payload["results"]},
            {str(self.tpl_a.pk), str(self.tpl_private_own.pk)},
        )
        self.assertEqual(payload["filter"]["source"], "manual")

    def test_saved_empty_suppresses_principal_and_unavailable_warns(self):
        self.set_current(self.team_a)
        self.save_preference(())
        payload = self.get_lookup().json()
        self.assertEqual(payload["filter"]["selected_tags"], [])
        self.assertEqual({i["id"] for i in payload["results"]}, self.active_ids())
        # Unavailable saved tag: valid remainder applies with generic warning.
        UserSpecialtyTagPreference.objects.filter(
            membership__specialty=self.team_a, membership__user=self.viewer
        ).delete()
        self.save_preference((self.tag_x, self.inactive_a))
        payload = self.get_lookup().json()
        self.assertEqual(
            [t["tag_id"] for t in payload["filter"]["selected_tags"]], [self.tag_x.pk]
        )
        self.assertTrue(payload["filter"]["warning"])
        self.assertNotIn(self.inactive_a.name, payload["filter"]["warning"])
        self.assertEqual(
            {i["id"] for i in payload["results"]},
            {str(self.tpl_a.pk), str(self.tpl_b.pk)},
        )

    def test_invalid_filters_and_uuids_are_generic_400_error_only(self):
        cases = (
            {"tags": ["999999"]},
            {"tags": ["not-a-tag"]},
            {"tags": [self.tag_x.pk], "tag_mode": "some"},
            {"tags": [self.restricted_b.pk]},
            {"tag_filter": "automatic"},
            {"q": "x" * 256},
            {"selected_template": "not-a-uuid"},
            {"selected_template": "999999"},
        )
        for params in cases:
            with self.subTest(params=params):
                response = self.get_lookup(**params)
                self.assertEqual(response.status_code, 400)
                payload = response.json()
                self.assertEqual(set(payload), {"error"})
                self.assertTrue(payload["error"])
                body = response.content.decode()
                self.assertNotIn("Avaliação Completa", body)
                self.assertNotIn(self.restricted_b.name, body)
                self.assertNotIn("not-a-uuid", body)
                self.assertNotIn("not-a-tag", body)
                # The 400 body must not echo a submitted unknown identity
                # for the selected_template case either.
                self.assertNotIn("999999", body)

    def test_historical_tag_options_toggle(self):
        payload = self.get_lookup().json()
        option_ids = [o["tag_id"] for o in payload["tag_options"]]
        self.assertIn(self.tag_x.pk, option_ids)
        self.assertNotIn(self.inactive_a.pk, option_ids)
        self.assertNotIn(self.archived_a.pk, option_ids)
        self.assertNotIn(self.restricted_b.pk, option_ids)
        toggled = self.get_lookup(include_historical="1").json()
        toggled_ids = [o["tag_id"] for o in toggled["tag_options"]]
        self.assertIn(self.inactive_a.pk, toggled_ids)
        self.assertIn(self.archived_a.pk, toggled_ids)
        self.assertNotIn(self.restricted_b.pk, toggled_ids)
        self.assertEqual(toggled["filter"]["source"], payload["filter"]["source"])
        self.assertEqual(toggled["count"], payload["count"])
        # Selected historical stays offered when toggle is off.
        selected = self.get_lookup(tags=[self.archived_a.pk]).json()
        options = {o["tag_id"]: o for o in selected["tag_options"]}
        self.assertIn(self.archived_a.pk, options)
        self.assertTrue(options[self.archived_a.pk]["is_selected"])
        self.assertEqual(
            [i["id"] for i in selected["results"]], [str(self.tpl_historical.pk)]
        )

    def test_projected_tags_hide_restricted_metadata_from_outsider(self):
        # tpl_c carries restricted_b (team B) and restricted_a (team A).
        # Each actor sees only the tag of their own team; neither sees
        # the other team's name or identity anywhere in the payload.
        link(self.tpl_c, self.restricted_b)
        link(self.tpl_c, self.restricted_a)
        self.client.force_login(self.outsider)
        payload = self.get_lookup().json()
        by_id = {i["id"]: i for i in payload["results"]}
        self.assertIn(str(self.tpl_c.pk), by_id)
        tag_ids = [t["tag_id"] for t in by_id[str(self.tpl_c.pk)]["tags"]]
        self.assertIn(self.restricted_b.pk, tag_ids)
        self.assertNotIn(self.restricted_a.pk, tag_ids)
        body = self.get_lookup().content.decode()
        self.assertNotIn(self.restricted_a.name, body)
        self.assertNotIn(str(self.restricted_a.pk), body)
        self.client.force_login(self.viewer)
        payload = self.get_lookup().json()
        by_id = {i["id"]: i for i in payload["results"]}
        tag_ids = [t["tag_id"] for t in by_id[str(self.tpl_c.pk)]["tags"]]
        self.assertIn(self.restricted_a.pk, tag_ids)
        self.assertNotIn(self.restricted_b.pk, tag_ids)
        body = self.get_lookup().content.decode()
        self.assertNotIn(self.restricted_b.name, body)
        self.assertNotIn(str(self.restricted_b.pk), body)

    def test_selected_authorized_outside_results_is_pinned_not_counted(self):
        plain = self.get_lookup(q="Resumida").json()
        with_selected = self.get_lookup(
            q="Resumida", selected_template=str(self.tpl_a.pk)
        ).json()
        self.assertEqual(with_selected["count"], plain["count"])
        self.assertEqual(
            [i["id"] for i in with_selected["results"]],
            [i["id"] for i in plain["results"]],
        )
        self.assertEqual(with_selected["selected"]["id"], str(self.tpl_a.pk))
        self.assertEqual(with_selected["selected"]["name"], "Avaliação Completa")
        self.assertFalse(with_selected["selection_unavailable"])
        self.assertNotIn("markdown_body", with_selected["selected"])

    def test_selected_unavailable_reveals_no_metadata(self):
        for target in (
            self.tpl_inactive,
            self.tpl_private_foreign,
            ReportTemplate(pk=uuid.uuid4(), name="x"),
        ):
            with self.subTest(target=str(target.pk)):
                response = self.get_lookup(selected_template=str(target.pk))
                payload = response.json()
                self.assertIsNone(payload["selected"])
                self.assertTrue(payload["selection_unavailable"])
                body = response.content.decode()
                self.assertNotIn("Avaliação Privada Alheia", body)
                self.assertNotIn("Avaliação Inativa", body)
                self.assertNotIn(str(target.pk), body)

    def test_selected_eligibility_is_rechecked_per_request(self):
        response = self.get_lookup(selected_template=str(self.tpl_c.pk))
        self.assertEqual(response.json()["selected"]["id"], str(self.tpl_c.pk))
        # Revoke: make it inactive between requests.
        self.tpl_c.is_active = False
        self.tpl_c.save(update_fields=["is_active"])
        payload = self.get_lookup(selected_template=str(self.tpl_c.pk)).json()
        self.assertIsNone(payload["selected"])
        self.assertTrue(payload["selection_unavailable"])
        self.assertNotIn(str(self.tpl_c.pk), [i["id"] for i in payload["results"]])


class ReportCreateDiscoveryPageTests(SelectionFixturesMixin, TestCase):
    def test_create_page_shares_discovery_markup_and_lookup_url(self):
        response = self.client.get(self.create_url())
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("data-report-template-discovery", body)
        self.assertIn("data-template-selection", body)
        self.assertIn("data-discovery-form", body)
        self.assertIn("data-discovery-q", body)
        self.assertIn("data-discovery-tags", body)
        self.assertIn("data-template-selection-results", body)
        self.assertIn("js/report-template-discovery.js", body)
        self.assertIn(reverse(SELECT_URL), body)
        self.assertIn("data-template-selection-warning", body)
        self.assertIn("filtrar antes de editar", body.lower())
        # Discovery context mirrors the catalogue keys.
        for key in (
            "discovery_selection",
            "discovery_name_query",
            "discovery_tag_options",
            "discovery_clear_querystring",
            "discovery_reapply_querystring",
            "selection_templates",
        ):
            self.assertIn(key, response.context)
        self.assertEqual(
            {t.pk for t in response.context["selection_templates"]},
            {
                self.tpl_a.pk,
                self.tpl_b.pk,
                self.tpl_c.pk,
                self.tpl_historical.pk,
                self.tpl_principal.pk,
                self.tpl_private_own.pk,
            },
        )

    def test_filter_form_is_outside_clinical_form_without_nesting(self):
        body = self.client.get(self.create_url()).content.decode()
        parser = parse_select(body)
        self.assertFalse(parser.nested_form)
        self.assertFalse(parser.filter_inside_clinical)
        self.assertFalse(parser.clinical_inside_filter)
        self.assertEqual(body.count("<form"), 2)

    def test_bounded_select_but_complete_validation_queryset(self):
        for index in range(25):
            make_template(self.viewer, f"S3 Página {index:02d}", is_public=True)
        response = self.client.get(self.create_url(), {"q": "S3 Pagina"})
        parser = parse_select(response.content.decode())
        # Empty option + 20 bounded page options only.
        self.assertEqual(len(parser.options), 21)
        values = {value for value, _label, _sel in parser.options}
        self.assertIn("", values)
        # A template beyond the first page is not rendered as a choice...
        self.assertNotIn(str(self.tpl_c.pk), values)
        # ...but remains in the validation queryset.
        queryset = response.context["form"].fields["template"].queryset
        self.assertIn(self.tpl_c, list(queryset))
        self.assertGreaterEqual(len(list(queryset)), 25)

    def test_selected_outside_results_is_pinned_and_selected(self):
        response = self.client.get(
            self.create_url(), {"template": str(self.tpl_b.pk), "q": "Completa"}
        )
        self.assertEqual(response.status_code, 200)
        parser = parse_select(response.content.decode())
        selected = [(value, label) for value, label, sel in parser.options if sel]
        self.assertEqual(
            selected,
            [(str(self.tpl_b.pk), "Avaliação Resumida (fora dos resultados atuais)")],
        )
        body = response.content.decode()
        self.assertIn("data-selected-template-outside", body)
        self.assertIn("Avaliação Resumida", body)
        # Count excludes the pinned choice.
        self.assertEqual(response.context["selection_count"], 1)
        self.assertEqual(
            [t.pk for t in response.context["selection_templates"]], [self.tpl_a.pk]
        )

    def test_selected_unavailable_uses_generic_label_and_keeps_identity(self):
        response = self.client.get(
            self.create_url(), {"template": str(self.tpl_private_foreign.pk)}
        )
        parser = parse_select(response.content.decode())
        matching = [
            (v, l, s)
            for v, l, s in parser.options
            if v == str(self.tpl_private_foreign.pk)
        ]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0][1], "Modelo selecionado indisponível")
        self.assertTrue(matching[0][2])
        body = response.content.decode()
        self.assertNotIn("Avaliação Privada Alheia", body)
        self.assertIn("data-selected-template-unavailable", body)
        self.assertIn("limpar", body.lower())

    def test_authorized_outside_results_submits_edited_content(self):
        response = self.client.post(
            self.create_url(),
            {
                "template": str(self.tpl_b.pk),
                "title": "Edited Title",
                "document_date": "01-15-2024",
                "content": "SENTINEL edited content",
            },
        )
        self.assertEqual(response.status_code, 302)
        report = Report.objects.get(title="Edited Title")
        self.assertEqual(report.template, self.tpl_b)
        self.assertEqual(report.content, "SENTINEL edited content")

    def test_ineligible_choice_is_rejected_on_submission(self):
        for target in (self.tpl_inactive, self.tpl_private_foreign):
            with self.subTest(target=target.name):
                before = Report.objects.count()
                response = self.client.post(
                    self.create_url(),
                    {
                        "template": str(target.pk),
                        "title": "Should Not Save",
                        "document_date": "01-15-2024",
                        "content": "Body",
                    },
                )
                self.assertEqual(response.status_code, 200)
                self.assertIn("template", response.context["form"].errors)
                self.assertEqual(Report.objects.count(), before)
                # Bound rerender keeps the submitted identity generically.
                parser = parse_select(response.content.decode())
                values = [v for v, _l, _s in parser.options]
                self.assertIn(str(target.pk), values)
                self.assertNotIn(target.name, response.content.decode())

    def test_validation_error_preserves_bound_fields_and_filter_context(self):
        response = self.client.post(
            self.create_url() + "?q=avaliacao",
            {
                "template": str(self.tpl_b.pk),
                "title": "",
                "document_date": "not-a-date",
                "content": "PRESERVED content",
            },
        )
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertEqual(form.data["content"], "PRESERVED content")
        self.assertEqual(form.data["template"], str(self.tpl_b.pk))
        self.assertEqual(response.context["discovery_name_query"], "avaliacao")
        parser = parse_select(response.content.decode())
        selected = [v for v, _l, sel in parser.options if sel]
        self.assertEqual(selected, [str(self.tpl_b.pk)])
        self.assertIn('value="avaliacao"', response.content.decode())

    def test_explicit_get_prefill_still_renders_content(self):
        response = self.client.get(self.create_url(), {"template": str(self.tpl_a.pk)})
        form = response.context["form"]
        self.assertEqual(form.initial.get("title"), self.tpl_a.name)
        self.assertIn("Test Patient", form.initial.get("content", ""))

    def test_manual_creation_without_template_still_works(self):
        response = self.client.post(
            self.create_url(),
            {
                "template": "",
                "title": "Manual S3",
                "document_date": "01-15-2024",
                "content": "Manual body",
            },
        )
        self.assertEqual(response.status_code, 302)
        report = Report.objects.get(title="Manual S3")
        self.assertIsNone(report.template)
        self.assertEqual(report.content, "Manual body")

    def test_duplicate_and_update_have_no_selector(self):
        report = Report.objects.create(
            patient=self.patient,
            created_by=self.viewer,
            updated_by=self.viewer,
            title="Source S3",
            content="Source body",
            document_date=date(2024, 1, 15),
        )
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType

        from apps.events.models import Event

        permission = Permission.objects.get(
            content_type=ContentType.objects.get_for_model(Event),
            codename="add_event",
        )
        self.viewer.user_permissions.add(permission)
        duplicate = self.client.get(
            reverse("reports:report_duplicate", kwargs={"pk": report.pk})
        )
        self.assertEqual(duplicate.status_code, 200)
        dup_body = duplicate.content.decode()
        self.assertNotIn("id_template", dup_body)
        self.assertNotIn("data-template-selection", dup_body)
        self.assertNotIn("data-discovery-form", dup_body)

        update = self.client.get(
            reverse("reports:report_update", kwargs={"pk": report.pk})
        )
        self.assertEqual(update.status_code, 200)
        update_body = update.content.decode()
        self.assertNotIn("id_template", update_body)
        self.assertNotIn("data-template-selection", update_body)
        self.assertNotIn("data-discovery-form", update_body)


class BoundedWidgetTests(SelectionFixturesMixin, TestCase):
    def test_widget_renders_only_bounded_plus_selected(self):
        from apps.reports.widgets import BoundedTemplateSelect

        widget = BoundedTemplateSelect()
        widget.set_bounded_choices(
            [self.tpl_a, self.tpl_b],
            selected_template=self.tpl_c,
            selected_unavailable=False,
        )
        html = widget.render("template", str(self.tpl_c.pk))
        self.assertIn("Avaliação Completa", html)
        self.assertIn("Relatório Simples (fora dos resultados atuais)", html)
        self.assertNotIn("Principal Modelo", html)
        self.assertIn('value="' + str(self.tpl_c.pk) + '"', html)
        self.assertIn("selected", html)

    def test_widget_unavailable_label_is_generic(self):
        from apps.reports.widgets import BoundedTemplateSelect

        widget = BoundedTemplateSelect()
        widget.set_bounded_choices(
            [self.tpl_a],
            selected_template=None,
            selected_template_id=str(self.tpl_private_foreign.pk),
            selected_unavailable=True,
        )
        html = widget.render("template", str(self.tpl_private_foreign.pk))
        self.assertIn("Modelo selecionado indisponível", html)
        self.assertNotIn("Avaliação Privada Alheia", html)

    def test_form_validation_queryset_is_not_narrowed_by_widget(self):
        from apps.reports.forms import ReportCreateForm

        form = ReportCreateForm(
            user=self.viewer,
            patient=self.patient,
            selection_templates=[self.tpl_a],
            selected_template=None,
            selected_unavailable=False,
        )
        self.assertEqual(
            list(form.fields["template"].queryset),
            list(form.fields["template"].queryset),
        )
        queryset_ids = {str(t.pk) for t in form.fields["template"].queryset}
        self.assertIn(str(self.tpl_c.pk), queryset_ids)
        self.assertIn(str(self.tpl_b.pk), queryset_ids)
        html = form["template"].as_widget()
        self.assertIn("Avaliação Completa", html)
        self.assertNotIn("Relatório Simples", html)


def _js_source() -> str:
    root = Path(__file__).resolve().parents[3]
    return (root / "assets" / "js" / "report-template-discovery.js").read_text()


def _js_function(source: str, name: str) -> str:
    start = source.index(f"function {name}(")
    nxt = source.find("\n    function ", start + 1)
    # applyPayload is followed by applyFragment at same indent; other
    # helpers may be followed by a differently-indented function, so
    # fall back to a generous window when no same-indent successor.
    end = nxt if nxt != -1 else start + 4000
    return source[start:end]


def _selection_function(source: str, name: str) -> str:
    """Return a function from the selection initializer only.

    ``historicalParams`` exists in both initializers; the catalogue
    copy is not the selection seam under review.
    """
    selection = source[source.index("function initializeSelection") :]
    return _js_function(selection, name)


def _options_only_branch(source: str) -> str:
    """Return only the optionsOnly branch of applyPayload (rt2-4 fix).

    The previous check searched the whole suffix after ``optionsOnly``,
    so calls in the later ``else`` branch would also satisfy it. This
    slices from ``optionsOnly`` to the closing ``} else {`` only.
    """
    apply_payload = _js_function(source, "applyPayload")
    start = apply_payload.index("optionsOnly")
    end = apply_payload.index("} else {", start)
    return apply_payload[start:end]


def _opening_tag(body: str, marker: str) -> str:
    match = re.search(rf"<[^>]*{re.escape(marker)}[^>]*>", body)
    assert match is not None, f"marker {marker} missing"
    return match.group(0)


class Fix1RegressionTests(SelectionFixturesMixin, TestCase):
    """Review-1 P1 regressions: transitions rebuilt from each response."""

    def test_p1_1_pagination_and_empty_state_are_rebuilt(self):
        # Empty -> match seam: list, empty and nav containers must all
        # exist on an empty initial page so JS can rebuild them.
        empty_body = self.client.get(
            self.create_url(), {"q": "zzz-sem-resultado"}
        ).content.decode()
        self.assertIn("data-template-selection-list", empty_body)
        self.assertIn("data-template-selection-empty", empty_body)
        self.assertIn("data-template-selection-nav", empty_body)
        self.assertNotIn(
            "hidden", _opening_tag(empty_body, "data-template-selection-empty")
        )
        self.assertIn("hidden", _opening_tag(empty_body, "data-template-selection-nav"))
        # Match (single page) seam: empty hidden, nav present hidden.
        match_body = self.client.get(self.create_url()).content.decode()
        self.assertIn("data-template-selection-list", match_body)
        self.assertIn("data-template-selection-empty", match_body)
        self.assertIn("data-template-selection-nav", match_body)
        self.assertIn(
            "hidden", _opening_tag(match_body, "data-template-selection-empty")
        )
        self.assertIn("hidden", _opening_tag(match_body, "data-template-selection-nav"))
        # Single -> multi-page / page navigation: server nav targets and
        # active label follow the requested page.
        for index in range(25):
            make_template(self.viewer, f"S3 Página {index:02d}", is_public=True)
        page1 = self.client.get(
            self.create_url(), {"q": "S3 Pagina", "page": "1"}
        ).content.decode()
        self.assertNotIn("hidden", _opening_tag(page1, "data-template-selection-nav"))
        self.assertIn("page=2", page1)
        self.assertIn(">1</span>", page1)
        page2 = self.client.get(
            self.create_url(), {"q": "S3 Pagina", "page": "2"}
        ).content.decode()
        self.assertNotIn("hidden", _opening_tag(page2, "data-template-selection-nav"))
        self.assertIn("page=1", page2)
        self.assertIn(">2</span>", page2)
        # JS must rebuild list/empty/nav from each payload, not only
        # update pre-existing elements.
        update_results = _js_function(_js_source(), "updateResults")
        self.assertIn("data-template-selection-empty", update_results)
        self.assertIn("data-template-selection-nav", update_results)
        self.assertIn("num_pages", update_results)

    def test_p1_2_selection_notices_follow_lookup_state(self):
        # No selection: all notice containers present but hidden.
        body = self.client.get(self.create_url()).content.decode()
        for marker in (
            "data-selected-template-outside",
            "data-selected-template-unavailable",
            "data-discovery-warning",
        ):
            self.assertIn(marker, body)
            self.assertIn("hidden", _opening_tag(body, marker))
        # In-results selection: outside notice hidden (out -> in seam).
        body = self.client.get(
            self.create_url(), {"template": str(self.tpl_a.pk)}
        ).content.decode()
        self.assertIn("hidden", _opening_tag(body, "data-selected-template-outside"))
        self.assertIn(
            "hidden", _opening_tag(body, "data-selected-template-unavailable")
        )
        # Out-of-results selection: outside visible (in -> out seam).
        body = self.client.get(
            self.create_url(), {"template": str(self.tpl_b.pk), "q": "Completa"}
        ).content.decode()
        self.assertNotIn("hidden", _opening_tag(body, "data-selected-template-outside"))
        self.assertIn(
            "hidden", _opening_tag(body, "data-selected-template-unavailable")
        )
        # Revoked selection: unavailable visible, outside hidden, no name.
        body = self.client.get(
            self.create_url(), {"template": str(self.tpl_private_foreign.pk)}
        ).content.decode()
        self.assertNotIn(
            "hidden", _opening_tag(body, "data-selected-template-unavailable")
        )
        self.assertIn("hidden", _opening_tag(body, "data-selected-template-outside"))
        self.assertNotIn("Avaliação Privada Alheia", body)
        # JS must create notices when missing and decide outside by
        # whether the selected id occurs in results.
        source = _js_source()
        self.assertIn("inResults", source)
        self.assertIn("data-selected-template-outside", source)

    def test_p1_3_pending_historical_selection_survives_toggle_off(self):
        # Server contract enabling the fix: with historical on, the
        # archived tag is offered; the JS rebuild must retain a pending
        # selected option the rebuilt set omits (toggle off before Apply).
        body = self.client.get(
            self.create_url(), {"include_historical": "1"}
        ).content.decode()
        self.assertIn("S3 Arquivada A", body)
        # S4: the shared selector owns tag options/chips, so the
        # creation controller never rebuilds native options (no
        # replaceTagOptions seam); a pending historical selection
        # survives as a chip. Retention stays server-authorized
        # (rt2-3): the model lookup still carries the pending ids as
        # retained_tags (never as the tags filter) for the payload's
        # retained_tag_options projection.
        self.assertNotIn("replaceTagOptions", _js_source())
        lookup = _selection_function(_js_source(), "lookupUrlFor")
        self.assertIn("retained_tags", lookup)
        self.assertIn("selectedTagIds", lookup)
        self.assertIn("retained", _js_source())
        # Pending preservation must not apply filters: historicalParams
        # builds only from the displayed URL (S4 fix4 seam), never from
        # the pending controls.
        historical = _selection_function(_js_source(), "historicalParams")
        self.assertIn("window.location.search", historical)
        self.assertNotIn("search.value", historical)
        self.assertNotIn("selectedTagIds", historical)

    def test_p1_4_options_only_lookup_reconciles_selection(self):
        # Payload contract: historical lookup revalidates the selection.
        payload = self.get_lookup(
            include_historical="1", selected_template=str(self.tpl_c.pk)
        ).json()
        self.assertEqual(payload["selected"]["id"], str(self.tpl_c.pk))
        self.tpl_c.is_active = False
        self.tpl_c.save(update_fields=["is_active"])
        payload = self.get_lookup(
            include_historical="1", selected_template=str(self.tpl_c.pk)
        ).json()
        self.assertIsNone(payload["selected"])
        self.assertTrue(payload["selection_unavailable"])
        # JS (S4): the historical toggle no longer fetches the model
        # lookup at all (options-only, selector-owned), so there is no
        # optionsOnly model branch; EVERY successful model payload
        # reconciles the clinical selection and its notices (rt2-4)
        # and reprojects the displayed results (rt2-2).
        selection_source = _js_source()[
            _js_source().index("function initializeSelection") :
        ]
        self.assertNotIn("optionsOnly", selection_source)
        apply_payload = _selection_function(_js_source(), "applyPayload")
        self.assertIn("updateClinicalSelect", apply_payload)
        self.assertIn("updateResults", apply_payload)
        # Notices reconcile from within updateResults (S4), exactly as
        # the catalogue fragment rebuild does for its summary.
        update_results = _selection_function(_js_source(), "updateResults")
        self.assertIn("reconcileSelectionNotices", update_results)

    def test_p1_5_malformed_template_post_rerenders_without_500(self):
        before = Report.objects.count()
        response = self.client.post(
            self.create_url(),
            {
                "template": "not-a-uuid",
                "title": "Malformed Template",
                "document_date": "01-15-2024",
                "content": "PRESERVED malformed content",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("template", response.context["form"].errors)
        self.assertEqual(Report.objects.count(), before)
        self.assertEqual(
            response.context["form"].data["content"], "PRESERVED malformed content"
        )


class Fix2RegressionTests(SelectionFixturesMixin, TestCase):
    """Review-2 regressions (rt2-1..rt2-5): page coherence, stale DOM
    metadata, server-authorized retention, executable-seam fixture and
    rebuilt badge remove links. Client transitions themselves are
    exercised by the Node/Playwright suite documented in fix-2.md;
    these tests cover the Django-rendered seam and payload contracts
    that suite consumes."""

    def test_rt2_a_page2_page_is_rendered_and_looked_up(self):
        for index in range(25):
            make_template(self.viewer, f"S3 Página {index:02d}", is_public=True)
        body = self.client.get(
            self.create_url(), {"q": "S3 Pagina", "page": "2"}
        ).content.decode()
        # The displayed page is rendered so the options-only lookup
        # can preserve it instead of silently returning page 1.
        self.assertIn('data-template-selection-page="2"', body)
        self.assertIn(">2</span>", body)
        # Server contract: a page-2 lookup returns page-2 identities.
        payload = self.get_lookup(q="S3 Pagina", page="2").json()
        self.assertEqual(payload["page"], 2)
        self.assertEqual(len(payload["results"]), 5)
        # JS seam (supplementary, S4): historicalParams builds from the
        # DISPLAYED URL (window.location.search), so the displayed page
        # survives the toggle without a displayedPage variable; the
        # predicate baseline (rememberApplied) still strips page while
        # the pushed URL keeps it. The executable suite proves the
        # transition.
        historical = _selection_function(_js_source(), "historicalParams")
        self.assertIn("window.location.search", historical)
        self.assertIn("include_historical", historical)
        remember = _selection_function(_js_source(), "rememberApplied")
        self.assertIn('delete("page")', remember)

    def test_rt2_b_revoked_model_leaves_the_lookup_results(self):
        payload = self.get_lookup(selected_template=str(self.tpl_c.pk)).json()
        self.assertIn(str(self.tpl_c.pk), [i["id"] for i in payload["results"]])
        self.assertEqual(payload["selected"]["id"], str(self.tpl_c.pk))
        # Revoke between requests: the next payload must omit the model
        # from results entirely so the client can reproject the list.
        self.tpl_c.is_active = False
        self.tpl_c.save(update_fields=["is_active"])
        payload = self.get_lookup(selected_template=str(self.tpl_c.pk)).json()
        self.assertNotIn(str(self.tpl_c.pk), [i["id"] for i in payload["results"]])
        self.assertIsNone(payload["selected"])
        self.assertTrue(payload["selection_unavailable"])
        # JS seam (supplementary): hiding the outside notice clears
        # its content, and every successful payload reprojects results
        # (S4: no optionsOnly model branch — see test_p1_4).
        reconcile = _js_function(_js_source(), "reconcileSelectionNotices")
        self.assertGreaterEqual(reconcile.count("replaceChildren"), 2)
        apply_payload = _selection_function(_js_source(), "applyPayload")
        self.assertIn("updateResults", apply_payload)

    def test_rt2_c_retained_tag_options_are_server_authorized(self):
        plain = self.get_lookup().json()
        self.assertEqual(plain["retained_tag_options"], [])
        # Readable ids (active + historical, toggle off) are authorized.
        payload = self.get_lookup(
            retained_tags=[
                self.archived_a.pk,
                self.inactive_a.pk,
                self.tag_x.pk,
            ]
        ).json()
        retained_ids = {o["tag_id"] for o in payload["retained_tag_options"]}
        self.assertEqual(
            retained_ids, {self.archived_a.pk, self.inactive_a.pk, self.tag_x.pk}
        )
        for option in payload["retained_tag_options"]:
            self.assertEqual(
                set(option),
                {
                    "tag_id",
                    "display_name",
                    "state_label",
                    "is_selected",
                    "is_historical",
                },
            )
        # retained_tags never applies as a filter and never widens
        # tag_options: results/count/options match the plain lookup.
        self.assertEqual(payload["count"], plain["count"])
        self.assertEqual(
            [i["id"] for i in payload["results"]],
            [i["id"] for i in plain["results"]],
        )
        self.assertEqual(payload["tag_options"], plain["tag_options"])
        # Membership loss revokes authorization for a restricted tag.
        payload = self.get_lookup(retained_tags=[self.restricted_a.pk]).json()
        self.assertIn(
            self.restricted_a.pk, [o["tag_id"] for o in payload["retained_tag_options"]]
        )
        membership = self.viewer.user_specialties.get(specialty=self.team_a)
        membership.is_active = False
        membership.save(update_fields=["is_active"])
        response = self.get_lookup(retained_tags=[self.restricted_a.pk])
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["retained_tag_options"], [])
        body = response.content.decode()
        self.assertNotIn(self.restricted_a.name, body)
        self.assertNotIn(str(self.restricted_a.pk), body)
        # Malformed / unreadable retained ids are omitted, not echoed,
        # and never become a 400 or a filter.
        response = self.get_lookup(
            retained_tags=["not-a-tag", "999999", self.restricted_b.pk]
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["retained_tag_options"], [])
        body = response.content.decode()
        self.assertNotIn("not-a-tag", body)
        self.assertNotIn("999999", body)

    def test_rt2_e_selected_tags_carry_effective_remove_querystrings(self):
        payload = self.get_lookup(
            tags=[self.tag_x.pk, self.tag_y.pk], tag_filter="manual", tag_mode="all"
        ).json()
        by_id = {t["tag_id"]: t for t in payload["filter"]["selected_tags"]}
        self.assertEqual(set(by_id), {self.tag_x.pk, self.tag_y.pk})
        for entry in by_id.values():
            self.assertIn("remove_querystring", entry)
        # Removing one tag leaves the other as an explicit manual filter.
        from urllib.parse import parse_qs

        remaining = parse_qs(by_id[self.tag_x.pk]["remove_querystring"])
        self.assertEqual(remaining.get("tags"), [str(self.tag_y.pk)])
        self.assertEqual(remaining.get("tag_filter"), ["manual"])
        self.assertEqual(remaining.get("tag_mode"), ["all"])
        remaining = parse_qs(by_id[self.tag_y.pk]["remove_querystring"])
        self.assertEqual(remaining.get("tags"), [str(self.tag_x.pk)])
        # Initial markup already carries the same remove links.
        body = self.client.get(
            self.create_url(),
            {
                "tags": [self.tag_x.pk, self.tag_y.pk],
                "tag_filter": "manual",
                "tag_mode": "all",
            },
        ).content.decode()
        self.assertIn("data-discovery-remove", body)
        # JS seam (supplementary): rebuilt badges recreate the links.
        update_results = _js_function(_js_source(), "updateResults")
        self.assertIn("data-discovery-remove", update_results)
        self.assertIn("remove_querystring", _js_source())

    def test_rt2_d_executable_seam_fixture_page(self):
        """Render the real page-2 create page the Playwright suite loads.

        When ``S3_FIXTURE_HTML`` names a path, the rendered HTML is
        also written there (inside the snapshot container) so the
        rerunnable Node suite can load the genuine Django page plus
        the built asset. The assertions below hold with or without it.
        """
        page_templates = [
            make_template(self.viewer, f"S3 Página {index:02d}", is_public=True)
            for index in range(25)
        ]
        selected = page_templates[-1]
        body = self.client.get(
            self.create_url(),
            {
                "q": "S3 Pagina",
                "page": "2",
                "template": str(selected.pk),
                "include_historical": "1",
            },
        ).content.decode()
        fixture_path = os.environ.get("S3_FIXTURE_HTML")
        if fixture_path:
            Path(fixture_path).write_text(body, encoding="utf-8")
        self.assertIn('data-template-selection-page="2"', body)
        self.assertIn("data-report-template-discovery", body)
        self.assertIn("data-template-selection", body)
        # S4: the selector owns the historical toggle on creation.
        self.assertIn("data-tag-historical", body)
        self.assertIn("data-discovery-tags", body)
        self.assertIn("id_template", body)
        self.assertIn(selected.name, body)
        # Page-2 clinical choices include the selected page-2 model.
        parser = parse_select(body)
        values = {value for value, _label, _sel in parser.options}
        self.assertIn(str(selected.pk), values)


class Fix3RegressionTests(SelectionFixturesMixin, TestCase):
    """Review-3 P1: omitted retained values must never echo through
    removal links. A valid applied tag filter plus unreadable,
    malformed and unknown ``retained_tags`` (and the transport-only
    ``selected_template``) must be absent from the entire response,
    while the valid tag's effective remove querystring still works."""

    def test_omitted_retained_values_never_echoed_through_removal_links(self):
        from urllib.parse import parse_qs

        # Unreadable (other-team restricted), malformed, unknown.
        omitted = ["not-a-tag", "999999", str(self.restricted_b.pk)]
        response = self.get_lookup(
            tags=[self.tag_x.pk, self.tag_y.pk],
            tag_filter="manual",
            tag_mode="all",
            retained_tags=omitted,
            selected_template=str(self.tpl_a.pk),
        )
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        serialized = json.dumps(response.json())
        for value in omitted:
            self.assertNotIn(value, body)
            self.assertNotIn(value, serialized)
        payload = response.json()
        self.assertEqual(payload["retained_tag_options"], [])
        by_id = {t["tag_id"]: t for t in payload["filter"]["selected_tags"]}
        self.assertEqual(set(by_id), {self.tag_x.pk, self.tag_y.pk})
        for entry in by_id.values():
            remove_querystring = entry["remove_querystring"]
            parsed = parse_qs(remove_querystring)
            self.assertNotIn("retained_tags", parsed)
            self.assertNotIn("selected_template", parsed)
            self.assertNotIn("retained_tags", remove_querystring)
            self.assertNotIn("selected_template", remove_querystring)
            for value in omitted:
                self.assertNotIn(value, remove_querystring)
        # The valid applied tags still drive effective removal links.
        remaining = parse_qs(by_id[self.tag_x.pk]["remove_querystring"])
        self.assertEqual(remaining.get("tags"), [str(self.tag_y.pk)])
        self.assertEqual(remaining.get("tag_filter"), ["manual"])
        self.assertEqual(remaining.get("tag_mode"), ["all"])
        remaining = parse_qs(by_id[self.tag_y.pk]["remove_querystring"])
        self.assertEqual(remaining.get("tags"), [str(self.tag_x.pk)])


class RuntimeFixProductRegressionTests(SelectionFixturesMixin, TestCase):
    """Runtime review-1 P1-1: revoked GET-prefill reveals no metadata.

    A REVOKED (inactive) public/own template passed as ``?template=``
    must not prefill the create page with its name or rendered body;
    it must surface only as the generic unavailable selection while
    keeping its submitted identity for validation. Active prefill and
    bound-error preservation are guards against over-blocking.
    """

    def test_inactive_public_prefill_reveals_no_name_or_body(self):
        response = self.client.get(
            self.create_url(), {"template": str(self.tpl_inactive.pk)}
        )
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertNotEqual(form.initial.get("title"), self.tpl_inactive.name)
        self.assertNotIn("S3 Test Patient", form.initial.get("content") or "")
        self.assertTrue(response.context["selected_template_unavailable"])
        self.assertIsNone(response.context["selected_template"])
        body = response.content.decode()
        self.assertNotIn(self.tpl_inactive.name, body)
        self.assertNotIn("Paciente: S3 Test Patient", body)
        self.assertIn("data-selected-template-unavailable", body)
        parser = parse_select(body)
        matching = [
            (v, l, s) for v, l, s in parser.options if v == str(self.tpl_inactive.pk)
        ]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0][1], "Modelo selecionado indisponível")
        self.assertTrue(matching[0][2])

    def test_inactive_own_prefill_reveals_no_name_or_body(self):
        inactive_own = make_template(
            self.viewer,
            "Avaliação Inativa Propria",
            is_public=False,
            is_active=False,
        )
        response = self.client.get(
            self.create_url(), {"template": str(inactive_own.pk)}
        )
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertNotEqual(form.initial.get("title"), inactive_own.name)
        self.assertNotIn("S3 Test Patient", form.initial.get("content") or "")
        self.assertTrue(response.context["selected_template_unavailable"])
        self.assertIsNone(response.context["selected_template"])
        body = response.content.decode()
        self.assertNotIn(inactive_own.name, body)
        self.assertNotIn("Paciente: S3 Test Patient", body)
        self.assertIn("data-selected-template-unavailable", body)

    def test_active_own_prefill_still_renders_name_and_body(self):
        response = self.client.get(
            self.create_url(), {"template": str(self.tpl_private_own.pk)}
        )
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertEqual(form.initial.get("title"), self.tpl_private_own.name)
        self.assertIn("S3 Test Patient", form.initial.get("content") or "")
        self.assertFalse(response.context["selected_template_unavailable"])

    def test_bound_error_rerender_preserves_fields_with_revoked_selection(self):
        before = Report.objects.count()
        response = self.client.post(
            self.create_url(),
            {
                "template": str(self.tpl_inactive.pk),
                "title": "Revoked Preserved Title",
                "document_date": "not-a-date",
                "content": "PRESERVED revoked content",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("template", response.context["form"].errors)
        self.assertEqual(Report.objects.count(), before)
        form = response.context["form"]
        self.assertEqual(form.data["title"], "Revoked Preserved Title")
        self.assertEqual(form.data["content"], "PRESERVED revoked content")
        self.assertEqual(form.data["template"], str(self.tpl_inactive.pk))
        body = response.content.decode()
        self.assertNotIn(self.tpl_inactive.name, body)
        parser = parse_select(body)
        selected = [v for v, _l, sel in parser.options if sel]
        self.assertEqual(selected, [str(self.tpl_inactive.pk)])
        self.assertIn("Modelo selecionado indisponível", body)


class ReportCreateLanguageTests(SelectionFixturesMixin, TestCase):
    """TFUX S1 R1-R2: creation shares canonical discovery wording."""

    def test_create_page_uses_canonical_discovery_language(self) -> None:
        response = self.client.get(self.create_url())
        for text in (
            "Pelo menos uma selecionada (OU)",
            "Todas as selecionadas (E)",
            "Correspondência",
            "Mostrar inativas e arquivadas no seletor",
            "Remover filtro de tags",
            "Restaurar padrão da especialidade",
            "Aplicar filtros",
        ):
            self.assertContains(response, text)
        self.assertNotContains(response, "Qualquer tag")
        self.assertNotContains(response, "Limpar tags")

    def test_create_applied_badge_removal_names_the_applied_scope(self) -> None:
        response = self.client.get(
            self.create_url(), {"tags": [self.tag_x.pk]}
        )
        self.assertContains(
            response,
            'aria-label="Remover S3 X dos filtros aplicados"',
        )

    def test_dynamic_applied_badge_removal_uses_applied_scope_label(self) -> None:
        # TFUX S1 review correction: badges recreated by the
        # enhanced selection controller must match the server
        # scope name, not the legacy bare label.
        update_results = _js_function(_js_source(), "updateResults")
        normalized = re.sub(r"\s+", " ", update_results)
        self.assertIn(
            '"Remover " + tag.display_name + " dos filtros aplicados"',
            normalized,
        )
        self.assertNotIn('"Remover " + tag.display_name\n', update_results)

    def test_dynamic_state_summary_uses_canonical_labels(self) -> None:
        # TFUX S1 review correction: the dynamic summary must not
        # regress to raw source/mode values, and must map every
        # payload source/mode to the canonical pt-BR labels.
        source = _js_source()
        self.assertNotIn(
            'payload.filter.source + " · " + payload.filter.mode', source
        )
        for label in (
            "Filtro personalizado",
            "Sem filtro de tags (personalizado)",
            "Sem filtro de tags (preferência salva)",
            "Padrão salvo da especialidade",
            "Padrão inicial da especialidade",
            "Sem filtro de tag",
            "Pelo menos uma selecionada (OU)",
            "Todas as selecionadas (E)",
        ):
            self.assertIn(label, source)
        update_results = _js_function(source, "updateResults")
        self.assertIn("data-discovery-state", update_results)
