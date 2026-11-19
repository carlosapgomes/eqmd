# WMX-S3 — Map button UI

## Identity

- Change: `add-ward-map-xlsx-export`.
- Task: [tasks.md §1 / 1.3](../tasks.md#1-deliver-the-export).
- Depends on WMX-S1 and WMX-S2 being accepted. One vertical slice: the map
  template button and its tests, plus the full test suite.

## Objective

The map page shows `Exportar xlsx` above the results and outside the filter
controls: enabled with the current query string when the filtered result has
patients, disabled when it does not; never present in the AJAX tree
fragment; no navigation away from `/patients/map`.

## Read First

- `AGENTS.md` and `docs/workflows/coding-standards.md`.
- This change's proposal, [design](../design.md) (D4) and
  [delta spec](../specs/patient-map-export/spec.md).
- The WMX-S2 contract and `apps/patients/views_ward_map_export.py`.
- `apps/patients/templates/patients/ward_patient_map.html` (filter section,
  updating alert, Tree View section) and
  `apps/patients/templates/patients/ward_patient_map_tree_only.html`.
- `apps/patients/tests/test_ward_map_export_view.py` (fixture helpers from
  WMX-S2).

## Scope

### Included

- One action row in the full map template, between the updating alert and
  the results card, with the enabled and disabled anchor variants.
- Template tests asserting placement, state, query string and absence from
  the AJAX fragment.
- The full test suite run as the closing gate.

### Excluded

- Any behavior change in the endpoint, service, filters or tree rendering.
- Any JavaScript, asset or build change.

### Files allowed

- `apps/patients/templates/patients/ward_patient_map.html`
- `apps/patients/tests/test_ward_map_export_view.py` (extend with the UI
  cases, reusing its fixtures)

No other file may be created or modified in this slice.

## Requirements and Planned Evidence

- The button row renders above the results card and outside the
  `<form method="get">` / `data-patient-filter-panel` subtree. Evidence:
  rendered-HTML assertions (ancestor checks between the export row and the
  form/panel nodes).
- With patients in the result: anchor with
  `href="{% url 'patients:patient_map_export' %}"` plus the current query
  string, no trailing `?` when the query string is empty. Evidence: with
  and without `?q=`/`?ward=` requests.
- The enabled link preserves repeated query parameters exactly as the
  request carried them. Evidence: request with repeated `tags=` parameters
  asserting the href (and following it once).
- With an empty result (including the cold-cache updating state, and zero
  total patients while `show_empty_wards=true` retains empty wards):
  anchor without `href`, class `disabled`, `aria-disabled="true"`,
  `tabindex="-1"`, title `Nenhum paciente no resultado da busca`.
  Evidence: filtered-empty, retained-empty-wards and cold-cache render
  tests.
- The export row keys its state only on `total_patients`: the row markup
  never references `updating`. Evidence: source/DOM assertion over the
  rendered variants.
- The button never renders in `ward_patient_map_tree_only.html` (both
  variants keep their contract). Evidence: AJAX-fragment render test.
- Map regressions hold. Evidence: the full suite
  (`./scripts/test.sh`) passes.

## Failing-Before Plan

1. Template tests fail first (no button in the rendered page).
2. Pin placement (outside the form) before adding the markup.
3. Pin the disabled variant before writing the `{% if %}` branch.

## Implementation Constraints

- Follow design D4 exactly: server-rendered anchor, no JavaScript, no
  changes to existing map markup except the added row.
- Keep the existing filter form, display options and preference panel
  untouched; do not move or renumber existing blocks.
- Reuse Bootstrap button and icon classes already present in the project
  (for example `btn-medical-outline-primary` and `bi-file-earmark-excel`).

## Validation

```bash
./scripts/test.sh apps.patients.tests.test_ward_map_export_view
./scripts/test.sh
```

Plus AGENTS.md scoped gates for the changed files.

## Acceptance Criteria

- [ ] Button sits above the results and outside the filter form.
- [ ] Enabled state carries the current query string; empty query string
      omits the `?`.
- [ ] Empty result renders the correctly disabled anchor; cold cache is
      covered by the same rule.
- [ ] The AJAX tree fragment is unchanged and button-free.
- [ ] Full suite passes with no regression.

## Escalation

Stop and report `BLOCKED_NEEDS_DECISION` for: any required change to the
form structure, the AJAX contract, or files outside the allowed list.

## Evidence Report and Worker Handoff

Write `/tmp/eqmd-ward-map-xlsx-export/WMX-S3-report.md` with
`READY_FOR_REVIEW` or `BLOCKED_NEEDS_DECISION`, requirement-to-evidence
mapping, changed paths, RED/GREEN proof and commands with exit statuses,
including the full-suite summary.

```text
Implement only approved WMX-S3 using this contract and referenced artifacts.
Reconstruct fresh context; follow repository engineering policy.
Produce failing-before evidence, implement minimally and validate.
Write /tmp/eqmd-ward-map-xlsx-export/WMX-S3-report.md and stop for review.
Do not update tasks.md, commit, push, merge, archive or start another slice.
```
