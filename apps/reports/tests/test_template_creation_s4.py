"""TFUX S4: report-creation selector parity (R1-R5).

Creation (``/reports/create/<patient>/``) opts into the shared selector
while keeping its JSON transport and clinical isolation: explicit
draft/dirty/Apply, searchable chips on the reports-owned lookup,
options-only historical, deliberate history with popstate restore, and
the catalogue host never binding there. Harness scenarios
(``tfux_s3_harness.cjs`` ``creation-*``) run the REAL selector plus the
REAL creation controller under a DOM stub with clinical sentinels;
they skip without a host ``node`` runtime, like the S3 harness tests.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import unittest
from datetime import date
from pathlib import Path

from django.test import TestCase
from django.urls import reverse

from apps.patients.models import Patient
from apps.reports.tests.test_template_discovery import DiscoveryFixturesMixin


class CreationSelectorParityTests(DiscoveryFixturesMixin, TestCase):
    """Creation renders the shared selector without catalogue host wiring."""

    def creation_body(self, **params) -> str:
        patient = Patient.objects.create(
            name="S4 Isol",
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            created_by=self.viewer,
            updated_by=self.viewer,
        )
        response = self.client.get(
            reverse("reports:report_create", kwargs={"patient_id": patient.pk}),
            params,
        )
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def test_creation_renders_selector_with_reports_lookup(self) -> None:
        body = self.creation_body()
        self.assertIn("data-tag-selector", body)
        self.assertIn("templates/tag-lookup", body)
        self.assertIn("data-creation-filter-dirty", body)
        self.assertIn("Alterações não aplicadas", body)
        self.assertIn("data-creation-filter-error", body)

    def test_catalogue_host_never_binds_on_creation(self) -> None:
        body = self.creation_body()
        self.assertNotIn("data-catalogue-filter-form", body)
        self.assertNotIn("report-catalogue-filter-form.js", body)
        self.assertNotIn("data-catalogue-filter-dirty", body)
        self.assertNotIn("data-catalogue-filter-error", body)
        self.assertIn("tag-selector.js", body)

    def test_filter_form_stays_outside_clinical_form(self) -> None:
        # No nested forms: the discovery GET form and the clinical POST
        # form are siblings, and the pre-edit warning survives for no-JS.
        body = self.creation_body()
        self.assertEqual(body.count("<form"), 2)
        self.assertIn("data-template-selection-warning", body)
        self.assertIn("filtrar antes de editar", body)
        # Discovery params never leak into the clinical POST: the
        # clinical form carries no repeated hidden tags inputs.
        clinical = body.split('<form method="post"', 1)[1]
        self.assertNotIn("data-tag-input", clinical)
        self.assertNotIn('name="tags"', clinical)

    def test_creation_selector_context_contract(self) -> None:
        patient = Patient.objects.create(
            name="S4 Ctx",
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            created_by=self.viewer,
            updated_by=self.viewer,
        )
        response = self.client.get(
            reverse("reports:report_create", kwargs={"patient_id": patient.pk})
        )
        self.assertEqual(response.status_code, 200)
        for key in (
            "tag_selection",
            "selected_tag_ids",
            "available_tags",
            "available_tag_ids",
            "selected_tags",
            "clear_tags_querystring",
        ):
            self.assertIn(key, response.context)
        # Native fallback honors the requested historical flag: without
        # it historical identities are NOT offered (no-JS users can
        # request them via the native control below).
        available_ids = {
            option.tag_id for option in response.context["available_tags"]
        }
        self.assertTrue(available_ids)
        self.assertNotIn(self.inactive_a.pk, available_ids)
        self.assertNotIn(self.archived_a.pk, available_ids)

    def test_nojs_historical_control_outside_enhanced_block(self) -> None:
        # Fix1: creation keeps a usable native historical checkbox with a
        # real submitted name outside the JS-only enhanced block, and the
        # view honors it for the native fallback options.
        patient = Patient.objects.create(
            name="S4 NoJS",
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            created_by=self.viewer,
            updated_by=self.viewer,
        )
        url = reverse("reports:report_create", kwargs={"patient_id": patient.pk})
        plain = self.client.get(url)
        self.assertEqual(plain.status_code, 200)
        body = plain.content.decode()
        # Native control exists with a real name, outside the enhanced
        # (JS-only) block whose toggle carries no submitted name.
        match = re.search(r'id="report-template-historical"[^>]*', body)
        self.assertIsNotNone(match, "native historical control missing")
        self.assertIn('name="include_historical"', match.group(0))
        self.assertNotIn("checked", match.group(0))
        self.assertIn("data-discovery-historical", match.group(0))
        # Fix2 placement: the native control is NOT inside the
        # selector's enhanced (JS-only) block — the enhanced markup
        # span carries no native historical control, and the native
        # input + its wrapper div render after that block, so no-JS
        # users still see the control even though the enhanced toggle
        # (inside the block) is hidden without JS.
        self.assertIn("data-discovery-historical-wrap", body)
        enhanced_start = body.index("data-tag-enhanced")
        hidden_start = body.index("data-tag-hidden-inputs")
        enhanced_block = body[enhanced_start:hidden_start]
        self.assertNotIn('id="report-template-historical"', enhanced_block)
        self.assertNotIn("data-discovery-historical", enhanced_block)
        native_index = body.index('id="report-template-historical"')
        wrap_index = body.index("data-discovery-historical-wrap")
        self.assertGreater(native_index, hidden_start)
        self.assertGreater(wrap_index, hidden_start)
        self.assertLess(wrap_index, native_index)
        native_ids = {
            option.tag_id for option in plain.context["available_tags"]
        }
        self.assertNotIn(self.inactive_a.pk, native_ids)
        self.assertNotIn(self.archived_a.pk, native_ids)
        # Requested via the native control: checked and offered.
        toggled = self.client.get(url, {"include_historical": "1"})
        self.assertEqual(toggled.status_code, 200)
        toggled_match = re.search(
            r'id="report-template-historical"[^>]*', toggled.content.decode()
        )
        self.assertIsNotNone(toggled_match)
        self.assertIn("checked", toggled_match.group(0))
        toggled_ids = {
            option.tag_id for option in toggled.context["available_tags"]
        }
        self.assertIn(self.inactive_a.pk, toggled_ids)
        self.assertIn(self.archived_a.pk, toggled_ids)


class CreationHarnessTests(unittest.TestCase):
    """Creation controller behavior under the real selector (S4 harness)."""

    HARNESS = "tfux_s3_harness.cjs"

    def run_harness(self, scenario: str) -> dict:
        root = Path(__file__).resolve().parents[3]
        harness = root / "apps" / "reports" / "tests" / self.HARNESS
        completed = subprocess.run(
            [shutil.which("node"), str(harness), scenario],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        self.assertEqual(
            completed.returncode, 0, f"harness failed: {completed.stderr[-2000:]}"
        )
        return json.loads(completed.stdout.strip().splitlines()[-1])

    @unittest.skipUnless(shutil.which("node"), "node runtime unavailable")
    def test_typing_q_issues_no_request_and_marks_dirty(self) -> None:
        out = self.run_harness("creation-typing-q")
        self.assertEqual(out["creationFetchCount"], 0)
        self.assertTrue(out["dirtyVisible"])
        self.assertTrue(out["clinicalUnchanged"])

    @unittest.skipUnless(shutil.which("node"), "node runtime unavailable")
    def test_clean_apply_issues_no_request_and_no_history(self) -> None:
        out = self.run_harness("creation-clean-apply")
        self.assertEqual(out["creationFetchCount"], 0)
        self.assertEqual(out["pushCount"], 0)
        self.assertTrue(out["clinicalUnchanged"])

    @unittest.skipUnless(shutil.which("node"), "node runtime unavailable")
    def test_dirty_apply_fetches_once_and_preserves_clinical(self) -> None:
        out = self.run_harness("creation-dirty-apply")
        self.assertEqual(out["creationFetchCount"], 1)
        self.assertIn("q=novo", out["fetchUrl"])
        self.assertEqual(out["pushCount"], 1)
        self.assertTrue(out["dirtyHiddenAfter"])
        self.assertTrue(out["clinicalUnchanged"])
        self.assertTrue(out["selectedPreserved"])
        self.assertEqual(out["selectedId"], "tpl-1")
        self.assertEqual(out["clinical"]["selected"], "tpl-1")
        # Enhanced: the native no-JS historical control is hidden/disabled
        # so JS users only see the selector panel toggle — wrapper (label)
        # hidden too, no orphaned native label.
        self.assertTrue(out["nativeHistoricalHidden"])
        self.assertTrue(out["nativeHistoricalWrapHidden"])

    @unittest.skipUnless(shutil.which("node"), "node runtime unavailable")
    def test_failed_apply_retains_results_draft_and_shows_error(self) -> None:
        out = self.run_harness("creation-apply-failure")
        self.assertEqual(out["creationFetchCount"], 1)
        self.assertEqual(out["pushCount"], 0)
        self.assertTrue(out["errorVisible"])
        self.assertTrue(out["dirtyVisible"])
        self.assertEqual(out["qRetained"], "novo")
        # Seeded identifiable results survive the failed Apply unchanged.
        self.assertEqual(out["resultsAfterFailure"], ["Modelo Um", "Modelo Dois"])
        self.assertTrue(out["resultsRetained"])
        self.assertEqual(out["selectedId"], "tpl-1")
        self.assertTrue(out["clinicalUnchanged"])

    @unittest.skipUnless(shutil.which("node"), "node runtime unavailable")
    def test_popstate_restores_controls_without_push_or_clinical_change(
        self,
    ) -> None:
        out = self.run_harness("creation-popstate")
        self.assertEqual(out["creationFetchCount"], 1)
        self.assertEqual(out["pushCount"], 0)
        self.assertEqual(out["qAfter"], "B")
        self.assertEqual(out["modeAfter"], "all")
        self.assertEqual(sorted(out["hiddenIds"]), ["3", "5"])
        self.assertTrue(out["hiddenEqualsChips"])
        self.assertTrue(out["noDuplicateHidden"])
        self.assertTrue(out["dirtyHiddenAfter"])
        self.assertTrue(out["clinicalUnchanged"])
        self.assertTrue(out["selectedPreserved"])

    @unittest.skipUnless(shutil.which("node"), "node runtime unavailable")
    def test_outside_results_selected_model_stays_pinned(self) -> None:
        out = self.run_harness("creation-outside-results")
        self.assertEqual(out["creationFetchCount"], 1)
        self.assertTrue(out["selectedPreserved"])
        self.assertTrue(out["outsideOptionPresent"])
        self.assertEqual(out["countAttr"], "1")
        self.assertTrue(out["clinicalUnchanged"])

    @unittest.skipUnless(shutil.which("node"), "node runtime unavailable")
    def test_historical_toggle_is_options_only(self) -> None:
        out = self.run_harness("creation-historical-toggle")
        self.assertEqual(out["creationFetchCount"], 0)
        self.assertEqual(out["replaceCount"], 1)
        self.assertEqual(out["pushCount"], 0)
        self.assertIn("include_historical=1", out["replaceUrl"])
        self.assertTrue(out["checkedAfter"])
        self.assertTrue(out["dirtyHidden"])
        self.assertTrue(out["clinicalUnchanged"])

    @unittest.skipUnless(shutil.which("node"), "node runtime unavailable")
    def test_badge_removal_is_scoped_and_keeps_draft(self) -> None:
        out = self.run_harness("creation-badge-remove")
        self.assertEqual(out["creationFetchCount"], 1)
        self.assertIn("tags=7", out["fetchUrl"])
        self.assertNotIn("tags=8", out["fetchUrl"].split("retained_tags")[0])
        self.assertEqual(out["qRetained"], "pendente")
        self.assertEqual(sorted(out["hiddenIds"]), ["7", "8"])
        self.assertTrue(out["dirtyVisible"])
        self.assertTrue(out["clinicalUnchanged"])

    @unittest.skipUnless(shutil.which("node"), "node runtime unavailable")
    def test_stale_selection_clear_shows_no_phantom_notice(self) -> None:
        out = self.run_harness("creation-stale-selection-clear")
        self.assertEqual(out["creationFetchCount"], 1)
        self.assertEqual(out["selectedAfter"], "")
        self.assertNotIn("tpl-1", out["selectedOptionIds"])
        self.assertTrue(out["outsideHidden"])
        self.assertTrue(out["unavailableHidden"])
        self.assertNotIn("Modelo Um", out["outsideText"])
        self.assertTrue(out["clinicalSentinels"])
        self.assertEqual(out["clinical"]["selected"], "")

    @unittest.skipUnless(shutil.which("node"), "node runtime unavailable")
    def test_stale_response_is_ignored(self) -> None:
        out = self.run_harness("creation-stale-response")
        self.assertEqual(out["pendingCount"], 2)
        self.assertEqual(out["listAfterStale"], [])
        self.assertEqual(out["listAfterApply"], ["Resultado B"])
        self.assertEqual(out["creationFetchCount"], 2)
        self.assertEqual(out["pushCount"], 1)
        self.assertTrue(out["clinicalUnchanged"])

    @unittest.skipUnless(shutil.which("node"), "node runtime unavailable")
    def test_revert_clears_dirty_without_request(self) -> None:
        out = self.run_harness("creation-revert-clears-dirty")
        self.assertTrue(out["dirtyAfterEdit"])
        self.assertEqual(out["creationFetchCount"], 0)
        self.assertTrue(out["dirtyHiddenAfterRevert"])
        self.assertTrue(out["clinicalUnchanged"])

    @unittest.skipUnless(shutil.which("node"), "node runtime unavailable")
    def test_pagination_keeps_page_in_history(self) -> None:
        out = self.run_harness("creation-pagination")
        self.assertTrue(out["pageLinkFound"])
        self.assertEqual(out["creationFetchCount"], 2)
        self.assertIn("page=2", out["pageFetchUrl"])
        self.assertIn("page=2", out["pushAfterPage"])
        self.assertTrue(out["selectedPreserved"])
        self.assertEqual(out["selectedId"], "tpl-1")
        self.assertTrue(out["clinicalUnchanged"])

    @unittest.skipUnless(shutil.which("node"), "node runtime unavailable")
    def test_revoked_selection_is_reconciled(self) -> None:
        out = self.run_harness("creation-revoked-selection")
        self.assertEqual(out["creationFetchCount"], 1)
        self.assertTrue(out["selectedPreserved"])
        self.assertEqual(out["selectedId"], "tpl-1")
        self.assertIn("tpl-1", out["selectedOptionIds"])
        self.assertTrue(out["unavailableVisible"])
        # The revoked selection keeps its identity under the generic
        # unavailable label from the real-payload scenario
        # (selected: null + selection_unavailable: true).
        self.assertEqual(
            out["selectedOptionLabel"], "Modelo selecionado indisponível"
        )
        self.assertTrue(out["unavailableLabel"])
        self.assertTrue(out["clinicalUnchanged"])
