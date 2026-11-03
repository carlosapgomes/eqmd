# Proposal: compact-tag-selector-results

## Motivation

The tag selector search results used by the patient list and the ward map
render one tall two-line `list-group` row per tag. The team abbreviation is
shown twice — inside `display_name` (`Nome [ABBR]`) and again in the metadata
line — and each row wastes vertical space. With page size 20 plus "Carregar
mais", the dropdown grows beyond 1,200 px. The visible row also looks fully
clickable while only the inner text button handles clicks.

The operator asked for a denser, non-redundant presentation. An independent
visual analysis (vision LLM, screenshots at desktop and mobile widths; report
at `/tmp/tag-ui-analysis/oracle-analysis.md`, summarized in `design.md`)
compared the current list, a chip-based proposal and a compact one-line list.
Chips save the most height but shrink touch targets to ~24 px, blur the
available-versus-selected state and hurt scanability; the recommended design
is the compact one-line action list.

## What Changes

- `assets/js/tag-selector.js` `resultButton()` becomes a single-line,
  full-row activation button: plain tag name, discreet team-abbreviation pill
  (right aligned, omitted for global tags), textual state when present
  (`Arquivada`/`Inativa`), no repeated `display_name`.
- Results already in the selection render as `Selecionada` with
  `aria-disabled="true"` (no re-add, no focus loss); removing a chip re-enables
  the matching result.
- Keyboard support: ArrowDown/ArrowUp/Home/End move across results,
  Enter/Space activate natively, Esc closes and refocuses the search field;
  the search field gets `aria-controls`.
- `data-tag-status` becomes `aria-live="polite" aria-atomic="true"` and
  announces searching, result counts, loaded counts and add/remove
  confirmations; stale async responses no longer overwrite newer results.
- Server-rendered contract only gains attributes: `_tag_selector.html` keeps
  the native `<select multiple>` no-JavaScript fallback, selected chips and
  the manual marker untouched; `tag_lookup` payload and `display_name` are
  unchanged (`name` already exists).

## Non-Goals

- No backend, model, migration, permission or visibility change.
- No change to selected chips' appearance or to the no-JS fallback.
- No fix for the pre-existing teal contrast debt of selected chips.
- No result grouping by team and no scroll-height cap (separate decisions).

## Impact

- Code: `assets/js/tag-selector.js` (renderer, keyboard, status, stale
  guard), `apps/patients/templates/components/_tag_selector.html`
  (attributes only), rebuilt `static/js/tag-selector.js`, focused tests.
- Specs: adds one requirement to `patient-tag-filtering`.
- Risk: shared surface (list + map); mitigated by the unchanged server
  contract and regression suites on both surfaces.
