"""RTFA-S2: canonical catalogue actions, visibility and creation isolation."""

import json
import shutil
import subprocess
from pathlib import Path
from unittest import skipUnless
from urllib.parse import parse_qs, urlsplit

from django.urls import reverse

from apps.accounts.models import MedicalSpecialty
from apps.reports.tests.catalogue_filter_action_fixtures import (
    CatalogueActionFixture,
    elements,
)


class CatalogueFilterActionTests(CatalogueActionFixture):
    def href(self, body: str, attribute: str) -> str:
        matches = elements(body, attribute)
        self.assertEqual(len(matches), 1)
        return str(matches[0]["href"])

    def test_clear_all_uses_only_manual_any_and_survives_reload(self) -> None:
        response = self.get_list(
            q="Ana",
            tags=[self.tag_y.pk],
            tag_mode="all",
            include_historical="1",
            page="2",
            fragment="",
            stale="discard",
        )
        before = self.snapshot()
        href = self.href(response.content.decode(), "data-discovery-clear")
        self.assertEqual(
            parse_qs(urlsplit(href).query),
            {
                "tag_filter": ["manual"],
                "tag_mode": ["any"],
            },
        )
        for _ in range(2):
            cleared = self.client.get(href)
            self.assertEqual(cleared.status_code, 200)
            self.assertEqual(cleared.context["discovery_name_query"], "")
            self.assertEqual(cleared.context["discovery_selection"].tag_ids, ())
            self.assertEqual(cleared.context["discovery_selection"].mode, "any")
            self.assertEqual(cleared.context["page_obj"].number, 1)
            self.assertEqual(cleared.context["page_obj"].paginator.count, 29)
            self.assertFalse(cleared.context["discovery_include_historical"])
        self.assertEqual(self.snapshot(), before)

    def test_restore_keeps_only_applied_name_and_historical(self) -> None:
        response = self.get_list(
            q=" Ana ",
            tags=[self.tag_y.pk],
            tag_mode="any",
            tag_filter="manual",
            include_historical="1",
            page="9",
            stale="discard",
        )
        before = self.snapshot()
        href = self.href(response.content.decode(), "data-discovery-reapply")
        self.assertEqual(
            parse_qs(urlsplit(href).query),
            {
                "q": ["Ana"],
                "include_historical": ["1"],
            },
        )
        restored = self.client.get(href)
        self.assertEqual(restored.context["discovery_selection"].source, "saved")
        self.assertEqual(restored.context["discovery_selection"].mode, "all")
        self.assertEqual(
            restored.context["discovery_selection"].tag_ids, (self.tag_x.pk,)
        )
        self.assertEqual(restored.context["discovery_name_query"], "Ana")
        self.assertEqual(self.snapshot(), before)

    def test_automatic_state_does_not_offer_restore(self) -> None:
        body = self.get_list().content.decode()
        restore = elements(body, "data-discovery-reapply")
        self.assertTrue(not restore or "hidden" in restore[0])

    def test_manual_saved_empty_is_restorable(self) -> None:
        self.preference.tags.clear()
        response = self.get_list(tag_filter="manual")
        self.assertTrue(response.context.get("catalogue_show_restore"))
        self.assertContains(response, 'data-catalogue-can-restore="true"')
        restored = self.client.get(
            self.href(response.content.decode(), "data-discovery-reapply")
        )
        self.assertEqual(restored.context["discovery_selection"].source, "saved")
        self.assertEqual(restored.context["discovery_selection"].tag_ids, ())

    def test_principal_only_is_restorable_without_saving(self) -> None:
        self.preference.delete()
        response = self.get_list(tag_filter="manual")
        self.assertTrue(response.context.get("catalogue_show_restore"))
        restored = self.client.get(
            self.href(response.content.decode(), "data-discovery-reapply")
        )
        self.assertEqual(restored.context["discovery_selection"].source, "principal")

    def test_no_specialty_no_default_and_inactive_membership_hide_restore(self) -> None:
        self.preference.delete()
        MedicalSpecialty.objects.filter(pk=self.team_a.pk).update(principal_tag=None)
        self.assertFalse(
            self.get_list(tag_filter="manual").context.get("catalogue_show_restore")
        )
        self.viewer.user_specialties.filter(specialty=self.team_a).update(
            is_active=False
        )
        self.assertFalse(
            self.get_list(tag_filter="manual").context.get("catalogue_show_restore")
        )
        profile = self.viewer.profile
        profile.current_specialty = None
        profile.save(update_fields=["current_specialty"])
        self.assertFalse(
            self.get_list(tag_filter="manual").context.get("catalogue_show_restore")
        )

    def test_unavailable_saved_default_keeps_generic_warning(self) -> None:
        self.preference.tags.set([self.inactive_a])
        response = self.get_list(tag_filter="manual")
        self.assertTrue(response.context.get("catalogue_show_restore"))
        restored = self.client.get(
            self.href(response.content.decode(), "data-discovery-reapply")
        )
        self.assertTrue(restored.context["discovery_warning"])
        self.assertNotIn(self.inactive_a.name, restored.context["discovery_warning"])
        self.assertEqual(restored.context["discovery_selection"].tag_ids, ())

    def test_fragment_has_fresh_server_owned_restore_metadata(self) -> None:
        for params, flag in (({}, "false"), ({"tag_filter": "manual"}, "true")):
            with self.subTest(params=params):
                response = self.get_list(fragment="results", **params)
                self.assertContains(response, f'data-catalogue-can-restore="{flag}"')
                self.assertNotContains(response, "data-discovery-remove")
                self.assertNotContains(response, "data-catalogue-filter-actions")

    def test_one_bar_in_order_and_no_duplicate_empty_recovery(self) -> None:
        body = self.get_list(q="Nenhum RTFA", tags=[self.tag_y.pk]).content.decode()
        self.assertEqual(len(elements(body, "data-catalogue-filter-actions")), 1)
        apply = body.index("data-discovery-apply")
        clear = body.index("data-discovery-clear")
        restore = body.index("data-discovery-reapply")
        self.assertLess(apply, clear)
        self.assertLess(clear, restore)
        self.assertEqual(len(elements(body, "data-discovery-clear")), 1)
        self.assertEqual(len(elements(body, "data-discovery-reapply")), 1)
        self.assertNotIn("data-discovery-remove", body)
        self.assertNotIn("ms-lg-auto", body)
        self.assertIn("Use as ações dos filtros acima", body)

    def test_clear_keeps_eligibility_inactive_and_private_boundaries(self) -> None:
        response = self.get_list(
            tag_filter="manual", tag_mode="any", q="Avaliação Privada"
        )
        self.assertIn(self.tpl_private_own.pk, self.result_ids(response))
        self.assertNotIn(self.tpl_private_foreign.pk, self.result_ids(response))
        response = self.get_list(tag_filter="manual", tags=[self.tag_x.pk])
        self.assertIn(self.tpl_inactive.pk, self.result_ids(response))
        self.assertFalse(self.viewer.has_perm("patients.view_patient"))

    def test_legacy_tag_only_url_preserves_name_and_invalid_input_stays_400(
        self,
    ) -> None:
        response = self.get_list(q="Ana", tag_filter="manual", tag_mode="all")
        self.assertEqual(response.context["discovery_name_query"], "Ana")
        self.assertEqual(response.context["discovery_selection"].tag_ids, ())
        for params in (
            {"tags": [self.restricted_b.pk]},
            {"tags": ["bad"]},
            {"tag_mode": "bad"},
        ):
            self.assertEqual(self.get_list(**params).status_code, 400)

    def test_creation_has_legacy_actions_without_catalogue_opt_in(self) -> None:
        response = self.client.get(
            reverse("reports:report_create", kwargs={"patient_id": self.patient.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Remover filtro de tags")
        self.assertContains(response, "Restaurar padrão da especialidade")
        self.assertNotContains(response, "data-catalogue-navigation")
        self.assertNotContains(response, "data-catalogue-filter-actions")

    @skipUnless(shutil.which("node"), "node runtime unavailable; run host harness")
    def test_catalogue_action_harness(self) -> None:
        harness = Path(__file__).with_name("catalogue_filter_actions_harness.cjs")
        result = subprocess.run(
            [str(shutil.which("node")), str(harness)],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["failed"], [])
