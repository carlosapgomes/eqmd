# S1: Compact selector results (single slice)

## Identity and objective

Change: `compact-tag-selector-results`. Tasks: 1.1-1.4 in
[../tasks.md](../tasks.md). Deliver the compact, accessible, non-redundant
search-results presentation for the shared tag selector on the patient list
and the ward map, with selection synchronization, keyboard operation and
polite announcements, without touching the server contract.

## Read first

- [Shared execution/report contract](README.md), `AGENTS.md`,
  `PROJECT_CONTEXT.md`, `docs/workflows/coding-standards.md`.
- [../design.md](../design.md) D1-D8 (binding).
- [Delta spec scenarios](../specs/patient-tag-filtering/spec.md)
  (they are the acceptance surface).
- Canonical `openspec/specs/patient-tag-filtering/spec.md` for surrounding
  behavior that must not regress.
- `apps/patients/templates/components/_tag_selector.html`,
  `assets/js/tag-selector.js` (whole file),
  `apps/patients/views_tag_filters.py` and
  `apps/patients/services/tag_lookup.py`
  (read-only context: payload already contains `name`, `team_abbreviation`,
  `state_label`, `display_name`).
- Visual analysis summary in `../../design.md` (source:
  `/tmp/tag-ui-analysis/oracle-analysis.md` if still present; otherwise the
  design decisions stand alone).

## Requirements and evidence

- **R1:** `resultButton()` renders one compact row: full-width button
  (`d-flex`, `align-items-center`, `gap-2`, `w-100`, target height ~44 px
  confirmed from rendering), plain `tag.name` (wraps, never truncated-only),
  team abbreviation once as `badge rounded-pill bg-light text-dark`
  (omitted when empty), `state_label` as text (omitted when empty);
  `display_name` never repeated visibly; `aria-label="Adicionar
{display_name}[ — {state}]"`. List keeps `role="list"`; "Carregar mais"
  stays outside. Evidence: code + screenshots + template/Django tests as
  applicable.
- **R2:** selection synchronization: matching result shows `Selecionada` and
  `aria-disabled="true"`, activation does not re-add (idempotent) and keeps
  focus; removing a chip re-enables the result and announces it; accessible
  name of inert rows ends with "— Já selecionada". Evidence: interaction log
  or scripted DOM assertions and screenshots.
- **R3:** keyboard and announcements: search field gains
  `aria-controls="tag-search-results"`; ArrowDown opens/focuses first,
  ArrowUp last; arrows/Home/End navigate; Enter/Space native activation
  without double fire; Esc hides and refocuses search without clearing the
  term; `data-tag-status` gains `aria-atomic="true"` and announces
  "Buscando tags...", "N resultados encontrados.", "N de M resultados
  carregados.", "Nenhuma tag visível encontrada." and add/remove
  confirmations; click no longer erases status; `load()` ignores stale
  responses (generation counter). Evidence: interaction log.
- **R4:** regressions and build: native `<select multiple>` fallback markup
  unchanged, chips/marker/ANY-ALL control untouched, `tag_lookup` payload
  unchanged; `npm run build` output committed as generated; focused suites
  green; full suite green; `git diff --check`; `openspec validate
compact-tag-selector-results --strict`. Evidence: command statuses and
  logs.

## Allowed blast radius

- `assets/js/tag-selector.js`; `static/js/tag-selector.js` (build output).
- `apps/patients/templates/components/_tag_selector.html` — attribute
  additions only (`aria-controls`, `aria-atomic`; `id` if needed).
- Existing test modules for the selector surfaces may gain assertions
  (`apps/patients/tests/test_tag_filters.py`,
  `apps/patients/tests/test_ward_map_tag_filters.py`); a new focused test
  module is allowed if it asserts the server-rendered contract.
- No other file. No backend, model, migration, docs, CSS or dependency
  change.

## Failing-before plan

Where a Django-rendered assertion exists, capture RED first (e.g. template
missing `aria-controls`/`aria-atomic`). For pure client-side rendering,
capture the BEFORE screenshot and a DOM dump of one current result row as
the baseline, then the AFTER equivalents; state clearly in the report which
evidence is RED/GREEN and which is before/after visual evidence.

## Implementation constraints

- Plain ES5-style consistent with the current file (no build-time syntax
  change, no framework); keep the module's existing structure and naming.
- Never mutate the shared payload or server-rendered nodes beyond the
  documented contract; results `<ul>` keeps `aria-label="Resultados de
tags"`.
- Screenshots must use synthetic fixtures only (no real patient content) and
  be produced with the headless Chrome available to the controller; if the
  worker cannot produce screenshots, it must say so and provide DOM dumps
  instead (honesty over completeness).
- Run test commands sequentially (shared test DB).

## Validation

Focused (sequential):

```bash
./scripts/test.sh apps.patients.tests.test_tag_filters
./scripts/test.sh apps.patients.tests.test_ward_map_tag_filters
./scripts/test.sh apps.accounts.tests.test_tag_preferences
npm run build
```

Release gates:

```bash
./scripts/test.sh
git diff --check
openspec validate compact-tag-selector-results --strict
```

Scoped ruff/typecheck on changed Python files if any; markdownlint on any
changed `.md`.

## Acceptance criteria

- [ ] R1-R4 satisfied with evidence in the report.
- [ ] Design D6 exclusions verified untouched by the reviewer and gates.
- [ ] No new dependency, migration or backend change.

## Escalation and report

Stop `BLOCKED_NEEDS_DECISION` if any D6 contract must break, a backend
change seems required, or visual verification is impossible. Report to
`/tmp/eqmd-compact-tags-slice-001-report.md` per the shared schema.

## Worker handoff

Implement only this slice from the canonical artifacts. Do not update
`tasks.md`, do not commit, push, merge or archive. End with the completion
marker from the README.
