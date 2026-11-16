"""TFUX S3: searchable catalogue selector contract.

Covers the S3 slice contract before implementation exists:
- reports-owned read-only tag lookup (no patients.view_patient gate),
  requester-safe projection incl. historical identity preservation;
- catalogue page opts into the shared selector (no duplicate native
  multi-select as the enhanced path; lookup URL is reports-owned);
- catalogue draft/Apply contract: dirty indicator, clean-Apply
  short-circuit, options-only historical, popstate/no-push-on-failure
  transport seams in report-template-discovery.js.
"""

from __future__ import annotations

import shutil
import unittest
from pathlib import Path

from django.test import TestCase
from django.urls import reverse

from apps.reports.tests.test_template_discovery import DiscoveryFixturesMixin


def link(template, tag):
    template.tags.through.objects.create(reporttemplate=template, allowedtag=tag)


LOOKUP_URL = "reports:template_tag_lookup"
LIST_URL = "reports:template_list"


class CatalogueLookupTests(DiscoveryFixturesMixin, TestCase):
    """Reports-owned lookup: reader-safe, no patient permission required."""

    def test_lookup_requires_login(self) -> None:
        self.client.logout()
        response = self.client.get(reverse(LOOKUP_URL))
        self.assertEqual(response.status_code, 302)

    def test_reader_without_patient_permission_can_search(self) -> None:
        # The viewer holds no patients.view_patient; catalogue discovery
        # must still answer through the report read boundary.
        self.assertFalse(
            self.viewer.has_perm("patients.view_patient"),
            "fixture viewer must lack the patient record permission",
        )
        response = self.client.get(reverse(LOOKUP_URL), {"q": "S2 X"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        names = [row["display_name"] for row in payload["results"]]
        self.assertIn("S2 X", names)
        self.assertNotIn("results", payload.get("templates", {}))

    def test_outsider_lookup_carries_no_foreign_restricted_metadata(self) -> None:
        self.client.force_login(self.outsider)
        response = self.client.get(
            reverse(LOOKUP_URL), {"q": "S2 Restrita", "include_historical": "1"}
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        body = response.content.decode()
        self.assertNotIn("S2 Restrita A", body)
        self.assertIn("S2 Restrita B", body)
        names = [row["display_name"] for row in payload["results"]]
        self.assertTrue(any(name.startswith("S2 Restrita B") for name in names), names)
        self.assertTrue(all("S2 Restrita A" not in name for name in names))
        # Privacy boundary: the outsider's own restricted identity is the
        # only restricted row present; no id of the foreign one leaks.
        # (Parsed identity fields — never a raw body substring, which a
        # small pk can match inside an unrelated id, count or UUID hex.)
        result_ids = [row["id"] for row in payload["results"]]
        selected_ids = [row["id"] for row in payload.get("selected", [])]
        self.assertNotIn(self.restricted_a.pk, result_ids)
        self.assertNotIn(self.restricted_a.pk, selected_ids)
        self.assertIn(self.restricted_b.pk, result_ids)

    def test_outsider_forged_selected_identity_is_absent(self) -> None:
        # A forged ``selected`` id for a foreign restricted tag resolves
        # through the requester projection: it is absent, never echoed.
        self.client.force_login(self.outsider)
        response = self.client.get(
            reverse(LOOKUP_URL),
            {"selected": [str(self.restricted_a.pk)]},
        )
        self.assertEqual(response.status_code, 400)
        # Forged foreign id: absent from the parsed selected identities
        # (never a raw body substring: small pks collide with unrelated
        # ids/counts, the same trap as the substring assertion above).
        selected_ids = [
            row["id"] for row in response.json().get("selected", [])
        ]
        self.assertNotIn(self.restricted_a.pk, selected_ids)

    def test_active_template_only_and_long_tags_are_searchable(self) -> None:
        response = self.client.get(reverse(LOOKUP_URL), {"q": "Só Template"})
        self.assertEqual(response.status_code, 200)
        names = [row["display_name"] for row in response.json()["results"]]
        self.assertIn("S2 Só Template", names)

    def test_historical_options_require_explicit_toggle(self) -> None:
        plain = self.client.get(reverse(LOOKUP_URL), {"q": "S2 Inativa"}).json()
        self.assertEqual(plain["results"], [])
        toggled = self.client.get(
            reverse(LOOKUP_URL),
            {"q": "S2 Inativa", "include_historical": "1"},
        ).json()
        names = [row["display_name"] for row in toggled["results"]]
        self.assertTrue(any(name.startswith("S2 Inativa A") for name in names), names)

    def test_selected_historical_identity_is_preserved(self) -> None:
        response = self.client.get(
            reverse(LOOKUP_URL),
            {"selected": [str(self.inactive_a.pk)]},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(
            [row["id"] for row in payload["selected"]],
            [self.inactive_a.pk],
        )

    def test_invalid_lookup_is_generic_400(self) -> None:
        response = self.client.get(reverse(LOOKUP_URL), {"page": "zero"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("Filtro de tag", response.json()["error"])

    def test_patient_lookup_keeps_its_own_gate(self) -> None:
        # The patient endpoint still requires patients.view_patient: the
        # viewer (no such permission) must be denied there while the
        # reports-owned lookup answers through the report boundary.
        denied = self.client.get(reverse("apps.patients:tag_lookup"))
        self.assertEqual(denied.status_code, 403)
        allowed = self.client.get(reverse(LOOKUP_URL))
        self.assertEqual(allowed.status_code, 200)


class CatalogueSelectorMarkupTests(DiscoveryFixturesMixin, TestCase):
    """Catalogue page opts into the shared selector via reports hooks."""

    def selector_body(self) -> str:
        response = self.client.get(reverse(LIST_URL))
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def test_catalogue_uses_reports_owned_lookup(self) -> None:
        body = self.selector_body()
        self.assertIn("data-tag-selector", body)
        lookup_url = reverse(LOOKUP_URL)
        self.assertIn(f'data-lookup-url="{lookup_url}"', body)

    def test_catalogue_does_not_point_at_patient_lookup(self) -> None:
        body = self.selector_body()
        self.assertNotIn("patients/tag-lookup", body)
        self.assertNotIn("patient-tag-lookup", body)

    def test_catalogue_exposes_dirty_indicator_and_marker(self) -> None:
        body = self.selector_body()
        self.assertIn("data-catalogue-filter-dirty", body)
        self.assertIn("Alterações não aplicadas", body)
        self.assertIn('role="status"', body)
        self.assertIn("data-tag-marker", body)

    def test_catalogue_keeps_native_repeated_tag_fallback(self) -> None:
        body = self.selector_body()
        self.assertIn('name="tags"', body)
        self.assertIn("data-tag-native", body)
        self.assertIn("Aplicar filtros", body)

    def test_catalogue_tag_search_has_visible_label(self) -> None:
        body = self.selector_body()
        search_at = body.find("data-tag-search")
        self.assertNotEqual(search_at, -1)
        label_at = body.find('<label for="report-template-tag-search"')
        self.assertNotEqual(label_at, -1, "catalogue search needs a visible label")
        self.assertLess(label_at, search_at)
        self.assertIn("report-template-tag-search-results", body)

    def test_catalogue_search_label_ids_are_unique(self) -> None:
        body = self.selector_body()
        for dom_id in (
            "report-template-tag-search",
            "report-template-tag-search-results",
            "report-template-include-historical",
            "report-template-tag-native",
            "report-template-mode",
        ):
            self.assertEqual(body.count(f'id="{dom_id}"'), 1, dom_id)

    def test_enhanced_selector_chips_and_panel_hooks_present(self) -> None:
        body = self.selector_body()
        for hook in (
            "data-tag-enhanced",
            "data-tag-search",
            "data-tag-results",
            "data-tag-panel",
            "data-tag-chips",
            "data-tag-hidden-inputs",
            "data-tag-status",
        ):
            self.assertIn(hook, body, hook)


class CatalogueNoJsApplyTests(DiscoveryFixturesMixin, TestCase):
    """No-JS catalogue Apply with a real repeated-tag GET (R2/R3/R5)."""

    def test_native_apply_with_repeated_tags_filters_conjunctively(self) -> None:
        # A real client GET with repeated ``tags`` (what the native
        # multi-select submits with two options selected) narrows the
        # catalogue; the request round-trips as the canonical applied state.
        response = self.client.get(
            reverse(LIST_URL),
            {
                "tag_filter": "manual",
                "tag_mode": "all",
                "tags": [str(self.tag_x.pk), str(self.tag_y.pk)],
            },
        )
        self.assertEqual(response.status_code, 200)
        selection = response.context["discovery_selection"]
        self.assertTrue(selection.is_manual)
        self.assertEqual(selection.mode, "all")
        self.assertEqual(
            {tag.pk for tag in selection.tags}, {self.tag_x.pk, self.tag_y.pk}
        )
        self.assertEqual(
            {template.pk for template in response.context["object_list"]},
            {self.tpl_a.pk},
        )
        self.assertContains(response, "Filtro personalizado")

    def test_native_clear_returns_manual_empty_without_defaults(self) -> None:
        self.set_current(self.team_a)
        self.save_preference((self.tag_x,))
        response = self.client.get(
            reverse(LIST_URL),
            {"tag_filter": "manual", "tag_mode": "any"},
        )
        self.assertEqual(response.status_code, 200)
        selection = response.context["discovery_selection"]
        self.assertTrue(selection.is_manual)
        self.assertFalse(selection.has_predicate)
        self.assertContains(response, "Sem filtro de tags (personalizado)")


class CatalogueCreationIsolationTests(DiscoveryFixturesMixin, TestCase):
    """Report creation never initializes the catalogue controller (R2/R5)."""

    def creation_body(self) -> str:
        from datetime import date

        from apps.patients.models import Patient

        patient = Patient.objects.create(
            name="S3 Isol",
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            created_by=self.viewer,
            updated_by=self.viewer,
        )
        response = self.client.get(
            reverse(
                "reports:report_create",
                kwargs={"patient_id": patient.pk},
            )
        )
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def test_creation_keeps_native_select_without_selector_root(self) -> None:
        # ``selector_plain`` renders the accepted native discovery select
        # (``data-discovery-tags``) with NO ``data-tag-selector`` element and
        # NO catalogue draft wiring; the word ``data-tag-selector`` survives
        # only inside developer comments. tag-selector.js therefore never
        # enhances the creation form and the catalogue transport never
        # initializes there (creation keeps its JSON controller).
        body = self.creation_body()
        self.assertNotIn("data-tag-selector=", body)
        self.assertNotIn("data-tag-selector'", body)
        self.assertNotIn('data-tag-selector"', body)
        self.assertNotIn("data-catalogue-filter-form", body)
        self.assertIn("data-discovery-tags", body)
        self.assertNotIn("report-catalogue-filter-form.js", body)

    def test_creation_does_not_point_at_catalogue_lookup(self) -> None:
        body = self.creation_body()
        self.assertNotIn("templates/tag-lookup", body)
        self.assertNotIn('data-template-selection-url="/reports/templates/tag-lookup', body)


class CatalogueTransportContractTests(TestCase):
    """Behavioral contract of the catalogue host/transport pair (S3 fix3).

    The combined-listener harness (``tfux_s3_harness.cjs``, next to this
    module) stubs just enough DOM to run the real
    ``report-catalogue-filter-form.js`` host and the catalogue
    ``initializeDiscovery`` transport from ``report-template-discovery.js``
    together, without a browser. ``node`` on the HOST runs the harness
    directly (``node apps/reports/tests/tfux_s3_harness.cjs``); the Django
    suite skips these tests when no container node runtime exists, so the
    suite stays green with or without it.

    Fix3 invariant: controls are user-owned — the transport never writes
    the visible controls except on popstate (full synchronous restore
    from the fragment). Reconciliation moves only the applied baseline
    (``catalogue:applied``), the results fragment and URL/history, so
    pending drafts survive Apply and every scoped action visibly dirty.
    """

    HARNESS_PATH = "tfux_s3_harness.cjs"

    @staticmethod
    def repo_root() -> Path:
        return Path(__file__).resolve().parents[3]

    @staticmethod
    def catalogue_source() -> str:
        root = Path(__file__).resolve().parents[3]
        return (root / "assets" / "js" / "report-template-discovery.js").read_text()

    def harness_path(self) -> Path:
        return self.repo_root() / "apps" / "reports" / "tests" / self.HARNESS_PATH

    def run_harness(self, scenario: str) -> dict:
        import json
        import subprocess

        node = shutil.which("node")
        if node is None:
            self.skipTest("node runtime unavailable")
        completed = subprocess.run(
            [node, str(self.harness_path()), scenario],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        self.assertEqual(
            completed.returncode, 0, f"harness failed: {completed.stderr[-2000:]}"
        )
        return json.loads(completed.stdout.strip().splitlines()[-1])

    def test_typing_q_does_not_issue_model_result_requests(self) -> None:
        catalogue = self.catalogue_source().split("function initializeSelection")[0]
        self.assertNotIn('addEventListener("input"', catalogue)

    @unittest.skipUnless(shutil.which("node"), "node runtime unavailable")
    def test_clean_apply_issues_no_request_and_no_history(self) -> None:
        out = self.run_harness("clean-apply")
        self.assertEqual(out["fetchCount"], 0)
        self.assertEqual(out["pushCount"], 0)

    @unittest.skipUnless(shutil.which("node"), "node runtime unavailable")
    def test_dirty_apply_still_submits_one_fragment_request(self) -> None:
        out = self.run_harness("dirty-apply")
        self.assertEqual(out["fetchCount"], 1)
        self.assertIn("fragment=results", out["fetchUrl"])
        self.assertIn("q=novo", out["fetchUrl"])

    @unittest.skipUnless(shutil.which("node"), "node runtime unavailable")
    def test_success_rebaselines_host_and_keeps_unrelated_pending(self) -> None:
        out = self.run_harness("reconcile")
        self.assertEqual(out["fetchCount"], 1)
        # dirty.hidden True right after success = host rebaselined to B;
        # dirty.hidden False after an unrelated pending edit = still visibly
        # pending against the NEW baseline (not the stale initial one).
        self.assertTrue(out["dirtyHiddenAfterRebaseline"])
        self.assertFalse(out["dirtyHiddenAfterUnrelatedEdit"])

    @unittest.skipUnless(shutil.which("node"), "node runtime unavailable")
    def test_popstate_restores_controls_without_pushing(self) -> None:
        out = self.run_harness("popstate")
        self.assertEqual(out["fetchCount"], 1)
        self.assertEqual(out["pushCount"], 0)
        self.assertEqual(out["qAfter"], "A")
        self.assertEqual(out["modeAfter"], "all")

    @unittest.skipUnless(shutil.which("node"), "node runtime unavailable")
    def test_selector_clear_is_manual_empty_and_keeps_pending_drafts(self) -> None:
        # Clear derives manual-empty from the applied state while ALL
        # pending drafts (q, a tag addition, a tag removal, mode) stay
        # untouched and visibly pending against the new baseline.
        out = self.run_harness("selector-clear")
        self.assertEqual(out["fetchCount"], 1)
        self.assertIn("tag_filter=manual", out["fetchUrl"])
        self.assertNotIn("tags=7", out["fetchUrl"])
        self.assertEqual(out["qStaysPending"], "pendente")
        self.assertTrue(out["additionSurvives"])
        self.assertTrue(out["removalSurvives"])
        self.assertEqual(out["modeStaysPending"], "all")
        # The host rebaselined to manual-empty (applied q empty) while the
        # visible controls keep the drafts: dirty stays visible against
        # the NEW baseline.
        self.assertFalse(out["dirtyHiddenAfterClear"])

    @unittest.skipUnless(shutil.which("node"), "node runtime unavailable")
    def test_historical_toggle_replaces_history_without_fetch(self) -> None:
        out = self.run_harness("historical")
        self.assertEqual(out["fetchCount"], 0)
        self.assertEqual(out["replaceCount"], 1)
        self.assertEqual(out["pushCount"], 0)
        self.assertTrue(out["checkedAfter"])
        self.assertIn("include_historical=1", out["replaceUrl"])
        # A genuinely new applied state without the flag re-reconciles
        # the checkbox OFF; the visible toggle is not frozen ON.
        self.assertFalse(out["checkedAfterNewApplied"])

    @unittest.skipUnless(shutil.which("node"), "node runtime unavailable")
    def test_same_canonical_comparison_is_page_and_order_insensitive(self) -> None:
        # The P2 seam now carries direct unit coverage in the harness:
        # the real ``sameCanonical`` is extracted from the transport
        # source and pinned (page/fragment-insensitive, key order free,
        # genuine q/tag changes still detected).
        out = self.run_harness("same-canonical")
        self.assertTrue(out["pageInsensitive"])
        self.assertTrue(out["fragmentInsensitive"])
        self.assertTrue(out["orderInsensitive"])
        self.assertTrue(out["detectsChange"])
        self.assertTrue(out["detectsTagChange"])

    @unittest.skipUnless(shutil.which("node"), "node runtime unavailable")
    def test_apply_preserves_post_submission_q_edit(self) -> None:
        # Apply B while A is applied, then edit q to C BEFORE the
        # response lands: the Apply success must NOT overwrite C
        # (controls keep CURRENT values) while the host baseline moves
        # to the applied B state (dirty stays visible against B).
        out = self.run_harness("delayed-apply")
        self.assertEqual(out["fetchCount"], 1)
        self.assertEqual(out["qAfter"], "C")
        self.assertFalse(out["dirtyHiddenAfter"])
        self.assertEqual(out["pushCount"], 1)

    @unittest.skipUnless(shutil.which("node"), "node runtime unavailable")
    def test_pending_tags_and_mode_survive_pagination(self) -> None:
        # A pending tag addition, a pending tag removal and a pending
        # mode all survive a scoped pagination success untouched.
        out = self.run_harness("pending-survives-pagination")
        self.assertEqual(out["fetchCount"], 1)
        self.assertTrue(out["draftTagSurvives"])
        self.assertTrue(out["additionSurvives"])
        self.assertTrue(out["removalSurvives"])
        self.assertEqual(out["hiddenIds"], ["11"])
        self.assertEqual(out["chipIds"], ["11"])
        self.assertEqual(out["modeStaysPending"], "all")
        self.assertTrue(out["dirtyVisible"])

    @unittest.skipUnless(shutil.which("node"), "node runtime unavailable")
    def test_pending_tags_and_mode_survive_badge_removal(self) -> None:
        # Badge removal moves only the applied baseline; the pending
        # tag addition, the pending tag removal and the pending mode
        # all stay visible and dirty against the new baseline.
        out = self.run_harness("pending-survives-badge")
        self.assertEqual(out["fetchCount"], 1)
        self.assertEqual(out["modeStaysPending"], "all")
        self.assertTrue(out["additionSurvives"])
        self.assertTrue(out["removalSurvives"])
        self.assertEqual(sorted(out["hiddenIds"]), ["11", "7"])
        self.assertEqual(sorted(out["chipIds"]), ["11", "7"])
        self.assertTrue(out["dirtyVisible"])

    @unittest.skipUnless(shutil.which("node"), "node runtime unavailable")
    def test_popstate_restores_selected_ids_with_working_remove(self) -> None:
        # The popstate scenario now carries selected ids through the
        # REAL shared selector: reconciled chips rebuild through the
        # selector's own creation path, so remove buttons work (the
        # fix2 R2/R4 regression) and no tag-selector:change fires from
        # reconciliation itself (the single change below is the user's
        # own remove click).
        out = self.run_harness("popstate")
        # Popstate restores synchronously from the fragment: no lookup.
        self.assertEqual(out["lookupCalls"], 0)
        self.assertEqual(sorted(out["hiddenIds"]), ["3", "5"])
        self.assertEqual(sorted(out["chipIds"]), ["3", "5"])
        self.assertTrue(out["removeWorks"])
        self.assertEqual(sorted(out["hiddenIdsAfterRemove"]), ["5"])
        self.assertEqual(sorted(out["chipIdsAfterRemove"]), ["5"])
        self.assertEqual(out["tagSelectorChangeCount"], 1)

    @unittest.skipUnless(shutil.which("node"), "node runtime unavailable")
    def test_reapply_defaults_moves_baseline_without_touching_controls(self) -> None:
        # Automatic defaults carry no tag params but ARE the fragment's
        # effective selection: reapply moves the applied baseline to
        # [21,22] while the (empty) controls stay untouched and read
        # dirty against it; the marker stays automatic (no
        # automatic→manual conversion). There is no chip to remove.
        out = self.run_harness("reapply-defaults")
        self.assertEqual(out["fetchCount"], 1)
        self.assertEqual(out["chipIds"], [])
        self.assertEqual(out["hiddenIds"], [])
        self.assertEqual(out["markerAfter"], "")
        self.assertEqual(out["modeAfter"], "any")
        self.assertTrue(out["dirtyVisible"])
        self.assertFalse(out["removeWorks"])

    @unittest.skipUnless(shutil.which("node"), "node runtime unavailable")
    def test_apply_preserves_post_submission_tags_and_mode(self) -> None:
        # Tags and mode edited AFTER an Apply submission but BEFORE
        # the response lands survive the success (controls are
        # user-owned) while the baseline moves to the applied state.
        out = self.run_harness("delayed-apply-tags-mode")
        self.assertEqual(out["fetchCount"], 1)
        self.assertEqual(out["qAfter"], "B")
        self.assertEqual(out["hiddenIds"], ["11"])
        self.assertEqual(out["chipIds"], ["11"])
        self.assertEqual(out["modeAfter"], "all")
        self.assertTrue(out["dirtyVisible"])
        self.assertEqual(out["pushCount"], 1)
        self.assertEqual(out["lookupCalls"], 0)

    @unittest.skipUnless(shutil.which("node"), "node runtime unavailable")
    def test_popstate_restores_names_synchronously_without_lookup(self) -> None:
        # Popstate to an automatic-default state rebuilds chips with
        # the fragment's display names/state labels, issues NO
        # selected-ids lookup fetch, and the chips stay removable.
        out = self.run_harness("popstate-restore-names")
        self.assertEqual(out["fetchCount"], 1)
        self.assertEqual(out["lookupCalls"], 0)
        self.assertEqual(out["qAfter"], "")
        self.assertEqual(out["modeAfter"], "any")
        self.assertEqual(out["markerAfter"], "")
        self.assertEqual(sorted(out["hiddenIds"]), ["21", "22"])
        self.assertEqual(sorted(out["chipIds"]), ["21", "22"])
        self.assertEqual(
            out["chipLabels"],
            ["Tag Auto Um (Ativa)", "Tag Auto Dois (Arquivada)"],
        )
        self.assertEqual(out["pushCount"], 0)
        self.assertTrue(out["removeWorks"])
        self.assertEqual(sorted(out["hiddenIdsAfterRemove"]), ["22"])
        self.assertEqual(out["tagSelectorChangeCount"], 1)

    @unittest.skipUnless(shutil.which("node"), "node runtime unavailable")
    def test_pagination_pushes_page_and_back_forward_restore_it(self) -> None:
        # Pagination pushes a URL that keeps page=2; Back/Forward
        # fetch and restore the popped page without new entries.
        out = self.run_harness("pagination-history")
        self.assertEqual(out["fetchCountAfterPage"], 1)
        self.assertTrue(out["pageInPushedUrl"])
        self.assertIn("page=2", out["pushedUrl"])
        self.assertEqual(out["fetchCountAfterBack"], 2)
        self.assertEqual(out["pushCountAfterBack"], 1)
        self.assertEqual(out["qAfterBack"], "A")
        self.assertEqual(out["fetchCountAfterForward"], 3)
        self.assertEqual(out["pushCountAfterForward"], 1)
        self.assertEqual(out["qAfterForward"], "A")
        self.assertTrue(out["forwardFetchHasPage"])
        self.assertIn("page=2", out["fetchUrlAfterForward"])

    def test_catalogue_transport_has_no_badge_hydration_lookup(self) -> None:
        # Fix3 deleted the async selected-ids hydration entirely: the
        # catalogue transport must not reference the lookup badge
        # fetch or any of its stamp/merge machinery. (The creation
        # controller in the same file is out of scope for this guard.)
        catalogue = self.catalogue_source().split("function initializeSelection")[0]
        self.assertNotIn('append("selected"', catalogue)
        self.assertNotIn("hydrationStamp", catalogue)
        self.assertNotIn("readDraftExtra", catalogue)
        self.assertNotIn("lastVisibleTags", catalogue)
        self.assertNotIn("__reconcile_q", catalogue)

    @unittest.skipUnless(shutil.which("node"), "node runtime unavailable")
    def test_inflight_historical_toggle_wins_over_stale_response(self) -> None:
        # Toggle ON while pagination is in flight: the older response
        # lands with the checkbox ON, keeps the newer flag in the
        # pushed URL (which also keeps page=2), and no stale flag is
        # pushed; no model query is replayed.
        out = self.run_harness("historical-inflight")
        self.assertEqual(out["fetchCount"], 1)
        self.assertTrue(out["checkedAfter"])
        self.assertEqual(out["pushCount"], 1)
        self.assertFalse(out["staleFlagPushed"])
        self.assertTrue(out["pushedUrlHasPageAndFlag"])
        self.assertIn("include_historical=1", out["currentSearch"])
        self.assertIn("page=2", out["currentSearch"])

    @unittest.skipUnless(shutil.which("node"), "node runtime unavailable")
    def test_historical_toggle_after_pagination_keeps_displayed_page(self) -> None:
        # Toggling historical AFTER page 2 landed keeps page=2 in the
        # replaced URL (plus the flag), so reload/Forward restoration
        # fetches page 2 instead of page 1.
        out = self.run_harness("historical-after-pagination")
        self.assertEqual(out["pushCountAfterPage"], 1)
        self.assertTrue(out["replaceUrlHasPage2"])
        self.assertTrue(out["replaceUrlHasFlag"])
        self.assertIn("page=2", out["replaceUrl"])
        self.assertIn("include_historical=1", out["replaceUrl"])
        self.assertTrue(out["restoreFetchHasPage2"])
        self.assertTrue(out["restoreFetchHasFlag"])
        self.assertEqual(out["pushCountAfterRestore"], 1)

    @unittest.skipUnless(shutil.which("node"), "node runtime unavailable")
    def test_historical_toggle_during_popstate_keeps_popped_url(self) -> None:
        # Back B->A with A's response in flight, then toggle BEFORE it
        # lands: the final URL is A+flag (not B) while the restored
        # controls/results are A.
        out = self.run_harness("historical-during-popstate")
        self.assertEqual(out["fetchCount"], 1)
        self.assertTrue(out["urlIsAWithFlag"])
        self.assertIn("q=A", out["currentSearch"])
        self.assertNotIn("q=B", out["currentSearch"])
        self.assertEqual(out["qAfter"], "A")
        self.assertEqual(out["modeAfter"], "all")
        self.assertEqual(sorted(out["hiddenIds"]), ["3", "5"])
        self.assertEqual(sorted(out["chipIds"]), ["3", "5"])
        self.assertTrue(out["checkedAfter"])
        self.assertEqual(out["pushCount"], 0)
