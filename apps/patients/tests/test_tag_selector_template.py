"""Compact tag selector: the server-rendered accessibility contract.

The search enhancement in `assets/js/tag-selector.js` can only announce and
navigate when the template exposes the matching hooks, so these assertions pin
the attributes the script depends on: the search field references the results
list, the list keeps its accessible name, the status region announces
atomically and "Carregar mais" stays outside the list. The native multi-select
fallback is asserted unchanged.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import MedicalSpecialty, UserSpecialty
from apps.accounts.tests.helpers import create_navigation_user
from apps.patients.models import AllowedTag, Patient, Tag

RESULTS_LIST = re.compile(r"<ul[^>]*data-tag-results[^>]*></ul>")
SEARCH_FIELD = re.compile(r"<input[^>]*id=\"tag-search\"[^>]*>")
STATUS_REGION = re.compile(r"<p[^>]*data-tag-status[^>]*>")
NATIVE_SELECT = re.compile(r"<select[^>]*data-tag-native[^>]*>")


def make_user(username: str) -> Any:
    """Create an active account allowed to read the patient list."""
    user = create_navigation_user(
        username=username,
        email=f"{username}@example.com",
        password="tag-selector-template-pass",
    )
    user.user_permissions.add(Permission.objects.get(codename="view_patient"))
    return user


class TagSelectorTemplateTests(TestCase):
    """The patient list renders the selector hooks the script relies on."""

    owner: Any
    specialty: MedicalSpecialty
    team_tag: AllowedTag

    @classmethod
    def setUpTestData(cls) -> None:
        cls.owner = make_user("tag-selector-owner")
        cls.specialty = MedicalSpecialty.objects.create(
            name="Equipe CIRGER", abbreviation="CIRGER"
        )
        UserSpecialty.objects.create(
            user=cls.owner, specialty=cls.specialty, is_active=True
        )
        cls.team_tag = AllowedTag.objects.create(
            name="Cir Vascular",
            specialty=cls.specialty,
            visibility=AllowedTag.Visibility.RESTRICTED,
            created_by=cls.owner,
            updated_by=cls.owner,
        )
        # Only catalogue entries already used by a patient stay in the legacy
        # option list (tag_projection.filter_tag_options).
        patient = Patient.objects.create(
            name="Paciente Fixture",
            birthday="1980-01-01",
            created_by=cls.owner,
            updated_by=cls.owner,
        )
        Tag.objects.create(
            allowed_tag=cls.team_tag,
            patient=patient,
            created_by=cls.owner,
            updated_by=cls.owner,
        )

    def setUp(self) -> None:
        self.client.force_login(self.owner)

    def component_markup(self) -> str:
        response = self.client.get(reverse("patients:patient_list"))
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def matches(self, pattern: re.Pattern[str]) -> list[str]:
        found = pattern.findall(self.component_markup())
        self.assertEqual(len(found), 1, "the selector must render exactly once")
        return found

    def test_search_field_references_the_results_list(self) -> None:
        search = self.matches(SEARCH_FIELD)[0]

        self.assertIn('aria-controls="tag-search-results"', search)

    def test_results_list_keeps_its_accessible_name(self) -> None:
        results = self.matches(RESULTS_LIST)[0]

        self.assertIn('id="tag-search-results"', results)
        self.assertIn('role="list"', results)
        self.assertIn('aria-label="Resultados de tags"', results)

    def test_status_region_announces_atomically_and_politely(self) -> None:
        status = self.matches(STATUS_REGION)[0]

        self.assertIn('aria-live="polite"', status)
        self.assertIn('aria-atomic="true"', status)

    def test_pagination_stays_outside_the_results_list(self) -> None:
        markup = self.component_markup()

        list_end = markup.index("</ul>", markup.index("data-tag-results"))
        self.assertGreater(markup.index("data-tag-more"), list_end)
        self.assertLess(markup.index("Carregar mais"), markup.index("data-tag-status"))

    def test_canonical_filter_language(self) -> None:
        markup = self.component_markup()
        self.assertIn("Correspondência", markup)
        self.assertIn("Pelo menos uma selecionada (OU)", markup)
        self.assertIn("Todas as selecionadas (E)", markup)
        self.assertIn("Mostrar inativas e arquivadas no seletor", markup)
        self.assertIn("Limpar todos os filtros", markup)
        self.assertNotIn("Qualquer tag", markup)
        self.assertNotIn("Incluir tags antigas", markup)
        self.assertNotIn("Limpar tags", markup)

    def test_draft_chip_removal_names_the_selection_scope(self) -> None:
        response = self.client.get(
            reverse("patients:patient_list"), {"tags": [self.team_tag.pk]}
        )
        self.assertIn(
            'aria-label="Remover Cir Vascular [CIRGER] da seleção"',
            response.content.decode(),
        )

    def test_dynamic_chip_removal_uses_selection_scope_label(self) -> None:
        # TFUX S1 review correction: chips recreated by the
        # enhancement must match the server-rendered scope name.
        root = Path(__file__).resolve().parents[3]
        source = (root / "assets" / "js" / "tag-selector.js").read_text()
        normalized = re.sub(r"\s+", " ", source)
        self.assertIn(
            '"Remover " + tag.display_name + " da seleção"', normalized
        )
        self.assertNotIn('"Remover " + tag.display_name);', source)

    def test_mode_and_state_block_is_vertical_and_width_constrained(self) -> None:
        # TFUX S1 layout correction: the longer canonical text must
        # not overflow the narrow tag column into the Apply/tree
        # columns. Static class assertions can only constrain the
        # structure (vertical block, full-width select, wrapping
        # state); real geometry still requires browser proof.
        markup = self.component_markup()
        mode_select = re.search(r'<select[^>]*id="tag-mode"[^>]*>', markup)
        self.assertIsNotNone(mode_select)
        classes = mode_select.group(0)
        self.assertIn("w-100", classes)
        self.assertIn("mw-100", classes)
        self.assertNotIn("w-auto", classes)
        self.assertIn('name="tag_mode"', classes)
        # Vertical enclosing block: label, select and state in
        # document order, without the old row justify-between.
        block_start = markup.index('class="d-flex flex-column')
        label_at = markup.index('for="tag-mode"', block_start)
        select_at = markup.index('id="tag-mode"', block_start)
        state_at = markup.index("data-tag-state", block_start)
        self.assertLess(block_start, label_at)
        self.assertLess(label_at, select_at)
        self.assertLess(select_at, state_at)
        block = markup[block_start:state_at]
        self.assertNotIn("justify-content-between", block)
        state_tag = re.search(r'<small[^>]*data-tag-state[^>]*>', markup)
        self.assertIsNotNone(state_tag)
        self.assertIn("text-break", state_tag.group(0))

    def test_map_renders_same_constrained_mode_block(self) -> None:
        response = self.client.get(reverse("patients:patient_map"))
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        mode_select = re.search(r'<select[^>]*id="tag-mode"[^>]*>', body)
        self.assertIsNotNone(mode_select)
        self.assertIn("w-100", mode_select.group(0))
        self.assertIn("mw-100", mode_select.group(0))
        self.assertNotIn("w-auto", mode_select.group(0))
        self.assertIn('class="d-flex flex-column', body)
        self.assertIn("Correspondência", body)
        self.assertIn("Pelo menos uma selecionada (OU)", body)
        self.assertIn('name="tag_mode"', body)

    def test_option_panel_wraps_results_and_load_more(self) -> None:
        # TFUX S2 R3: option results live in a selector-anchored overlay
        # panel so opening/loading rows cannot grow the host card.
        markup = self.component_markup()
        panel = re.search(r'<div[^>]*data-tag-panel[^>]*>', markup)
        self.assertIsNotNone(panel)
        self.assertIn("hidden", panel.group(0))
        panel_start = panel.start()
        results_at = markup.index("data-tag-results", panel_start)
        more_at = markup.index("data-tag-more", panel_start)
        status_at = markup.index("data-tag-status", panel_start)
        self.assertLess(results_at, more_at)
        self.assertLess(more_at, status_at)
        self.assertIn('aria-controls="tag-search-results"', markup)

    def test_draft_chip_uses_neutral_surface_and_sized_remove_target(self) -> None:
        # TFUX S2 R4: draft chips use a neutral light surface with dark
        # text (not the white-on-teal combination) and a sized remove
        # target with the S1 selection-scope accessible name.
        response = self.client.get(
            reverse("patients:patient_list"), {"tags": [self.team_tag.pk]}
        )
        markup = response.content.decode()
        chip = re.search(r'<span[^>]*data-tag-chip[^>]*>', markup)
        self.assertIsNotNone(chip)
        self.assertIn("tag-filter-chip", chip.group(0))
        self.assertNotIn("bg-medical-teal", chip.group(0))
        remove = re.search(
            r'<button[^>]*data-tag-remove[^>]*>.*?</button>', markup
        )
        self.assertIsNotNone(remove)
        self.assertIn("tag-filter-chip-remove", remove.group(0))
        self.assertNotIn("btn-close-white", remove.group(0))
        self.assertIn(
            'aria-label="Remover Cir Vascular [CIRGER] da seleção"',
            remove.group(0),
        )
        self.assertIn(">×</span></button>", remove.group(0))
        self.assertIn("tag-filter-chip-label", markup)
        self.assertNotIn('class="tag-filter-chip-label text-break"', markup)

    def test_map_draft_chip_uses_the_same_neutral_surface(self) -> None:
        response = self.client.get(
            reverse("patients:patient_map"), {"tags": [self.team_tag.pk]}
        )
        self.assertEqual(response.status_code, 200)
        markup = response.content.decode()
        chip = re.search(r'<span[^>]*data-tag-chip[^>]*>', markup)
        self.assertIsNotNone(chip)
        self.assertIn("tag-filter-chip", chip.group(0))
        self.assertNotIn("bg-medical-teal", chip.group(0))
        self.assertIn("data-tag-panel", markup)

    def test_selector_panel_and_chip_styles_are_bounded_and_sized(self) -> None:
        # TFUX S2 R3/R4: the bounded overlay, neutral chip colors and
        # 24/44px remove targets live in the scoped stylesheet.
        root = Path(__file__).resolve().parents[3]
        source = (root / "assets" / "scss" / "main.scss").read_text()
        normalized = re.sub(r"\s+", " ", source)
        self.assertIn(".tag-selector-panel", normalized)
        self.assertIn("width: 100%", normalized)
        self.assertIn("max-height: min(18rem, 50vh)", normalized)
        self.assertIn("overflow-y: auto", normalized)
        self.assertIn(".tag-filter-chip", normalized)
        self.assertIn("background-color: #eef2f7", normalized)
        self.assertIn("color: #1e293b", normalized)
        self.assertIn(".tag-filter-chip-remove", normalized)
        self.assertIn("min-width: 24px", normalized)
        self.assertIn("min-height: 24px", normalized)
        self.assertIn("@media (pointer: coarse)", normalized)
        self.assertIn("min-width: 44px", normalized)
        self.assertIn("min-height: 44px", normalized)

    def test_filter_labels_avoid_conflicting_nowrap_styles(self) -> None:
        root = Path(__file__).resolve().parents[3]
        source = (root / "assets" / "js" / "tag-selector.js").read_text()
        self.assertNotIn(
            'label.className = "tag-filter-chip-label text-break"',
            source,
        )
        selector = self.matches(NATIVE_SELECT)[0]
        self.assertIsNotNone(selector)
        markup = self.component_markup()
        self.assertNotIn('class="tag-filter-chip-label text-break"', markup)
        styles = (root / "assets" / "scss" / "main.scss").read_text()
        self.assertIn("white-space: normal", styles)
        self.assertIn("[data-tag-mode-badge]", styles)
        self.assertIn("[data-tag-default-badge]", styles)

    def test_selector_js_reopens_loaded_results_and_closes_outside(self) -> None:
        # TFUX S2 R3: focus/click reopens loaded results, click-outside
        # and Escape close without losing the term or selection, and
        # selection changes notify the host filter form.
        root = Path(__file__).resolve().parents[3]
        source = (root / "assets" / "js" / "tag-selector.js").read_text()
        normalized = re.sub(r"\s+", " ", source)
        self.assertIn("tag-selector:change", normalized)
        self.assertIn("document.addEventListener(\"click\"", normalized)
        self.assertIn("contains(", normalized)
        self.assertIn("childElementCount", normalized)
        self.assertIn("data-tag-panel", normalized)

    def test_search_escape_prevents_native_term_clear(self) -> None:
        # TFUX S2 browser fix (supplement to the executable
        # harness): native Chrome clears input[type=search] text
        # on Escape unless the keydown is prevented, so the
        # search-field Escape branch must preventDefault while
        # closing the panel (result-row Escape already does).
        root = Path(__file__).resolve().parents[3]
        source = (root / "assets" / "js" / "tag-selector.js").read_text()
        start = source.index('search.addEventListener("keydown"')
        end = source.index('results.addEventListener("keydown"')
        branch = source[start:end]
        normalized = re.sub(r"\s+", " ", branch)
        escape_at = normalized.index('"Escape"')
        arrow_at = normalized.index("ArrowDown")
        escape_block = normalized[escape_at:arrow_at]
        self.assertIn("event.preventDefault()", escape_block)
        self.assertIn("setPanelVisible(false)", escape_block)

    def test_dynamic_chip_recreation_uses_neutral_surface(self) -> None:
        root = Path(__file__).resolve().parents[3]
        source = (root / "assets" / "js" / "tag-selector.js").read_text()
        normalized = re.sub(r"\s+", " ", source)
        self.assertIn("tag-filter-chip", normalized)
        self.assertIn("tag-filter-chip-remove", normalized)
        self.assertIn('"×"', source)

    def test_patient_list_filter_form_exposes_dirty_state(self) -> None:
        # TFUX S2 R1: the host form carries the draft/applied hooks and
        # the persistent unapplied-changes text near Apply.
        markup = self.component_markup()
        form = re.search(r'<form[^>]*data-patient-filter-form[^>]*>', markup)
        self.assertIsNotNone(form)
        self.assertIn('method="get"', form.group(0))
        dirty = re.search(r'<p[^>]*data-patient-filter-dirty[^>]*>', markup)
        self.assertIsNotNone(dirty)
        self.assertIn("hidden", dirty.group(0))
        self.assertIn("Alterações não aplicadas", markup)
        self.assertIn("patient-filter-form.js", markup)
        self.assertIn('name="q"', markup)
        self.assertIn('name="status"', markup)

    def test_filter_form_js_normalizes_state_and_short_circuits_clean_apply(self) -> None:
        # TFUX S2 R1/R2: normalized comparison (trimmed q, deduplicated
        # tag ids) and a clean Apply that issues no result request.
        root = Path(__file__).resolve().parents[3]
        source = (root / "assets" / "js" / "patient-filter-form.js").read_text()
        normalized = re.sub(r"\s+", " ", source)
        self.assertIn("data-patient-filter-form", normalized)
        self.assertIn("data-patient-filter-dirty", normalized)
        self.assertIn("tag-selector:change", normalized)
        self.assertIn(".trim()", normalized)
        self.assertIn("preventDefault", normalized)
        self.assertIn("show_empty_wards", normalized)
        self.assertNotIn("form.submit()", normalized)

    def test_filter_form_enhanced_selection_includes_empty(self) -> None:
        # TFUX S2 review fix: in the enhanced form the hidden
        # repeated inputs are authoritative, including the empty
        # selection after the last chip is removed. Only the
        # unenhanced native select is a fallback, because
        # enhancement disables it without deselecting the
        # server-rendered applied options.
        root = Path(__file__).resolve().parents[3]
        source = (root / "assets" / "js" / "patient-filter-form.js").read_text()
        start = source.index("function selectedTagIds")
        end = source.index("function readState")
        reader = source[start:end]
        normalized = re.sub(r"\s+", " ", reader)
        self.assertIn("if (isEnhanced(form))", normalized)
        self.assertIn("[data-tag-input]", normalized)
        self.assertLess(
            normalized.index("isEnhanced(form)"),
            normalized.index("option:checked"),
        )
        self.assertNotIn("if (inputs.length)", normalized)

    def test_native_multiselect_fallback_is_unchanged(self) -> None:
        select = self.matches(NATIVE_SELECT)[0]
        markup = self.component_markup()

        self.assertIn('name="tags"', select)
        self.assertIn("multiple", select)
        self.assertEqual(markup.count('name="tags"'), 1)
        self.assertIn(f'<option value="{self.team_tag.pk}"', markup)
        self.assertIn("Cir Vascular [CIRGER]", markup)
        self.assertIn('name="tag_filter"', markup)
        self.assertIn('name="tag_mode"', markup)

    def test_set_selection_api_is_catalogue_opt_in_and_patient_neutral(self) -> None:
        # TFUX S3 fix2: the shared selector exposes an opt-in
        # ``tag-selector:set-selection`` reconciliation event for the
        # catalogue transport. Without the event the selector behaves
        # exactly as before: no set-selection listener side effects run
        # on patient surfaces, which never dispatch the event, and the
        # API neither marks manual nor dispatches tag-selector:change.
        root = Path(__file__).resolve().parents[3]
        source = (root / "assets" / "js" / "tag-selector.js").read_text()
        normalized = re.sub(r"\s+", " ", source)
        self.assertIn("tag-selector:set-selection", normalized)
        # Opt-in: a no-op (empty selection) listener arm, wired once per
        # selector root, reusing the existing addChip/attachRemove
        # machinery — not a second chip renderer.
        self.assertIn("addEventListener(\"tag-selector:set-selection\"", normalized)
        self.assertIn("addChip({", normalized)
        self.assertIn("notifySelectionChanged", normalized)
        notify_count = source.count("notifySelectionChanged()")
        # The definition plus the two pre-existing user-change call
        # sites (remove handler, addTag) are untouched; the
        # set-selection arm below adds no new dispatch (reconciliation
        # is not a user change).
        self.assertEqual(notify_count, 3)
        arm_start = source.index(
            'root.addEventListener("tag-selector:set-selection"'
        )
        arm_end = source.index("Array.prototype.forEach.call(", arm_start)
        arm = source[arm_start:arm_end]
        self.assertNotIn("notifySelectionChanged()", arm)
        self.assertNotIn("markManual", arm)
        self.assertNotIn("tag-selector:change", arm)
        # Patient surfaces never dispatch the event: no catalogue
        # transport script loads there and no template references it.
        response = self.client.get(reverse("patients:patient_list"))
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertNotIn("tag-selector:set-selection", body)
        self.assertNotIn("report-template-discovery", body)
