# Design: compact-tag-selector-results

Source analysis: independent visual/UX review (vision model) over rendered
screenshots of the current selector and a chip mock, plus code inspection.
Key conclusions are condensed here as binding decisions.

## D1 — Compact one-line action list, not chips

Results stay a `<ul>` action list; each `<li>` contains ONE button that fills
the whole row (Bootstrap flex utilities). The button shows: plain tag name
(`tag.name`, flex-grow, wraps for long names), team abbreviation as a discreet
`badge rounded-pill bg-light text-dark` (right aligned, omitted when empty),
and state label as `text-secondary` text (omitted when empty). `display_name`
is never repeated visibly; it remains the accessible name base.

Rationale vs chips: chips cut height most (~58-71%) but reduce touch targets
to ~24 px, confuse available ("+") and selected ("x") states in the same teal,
overflow on long names and read in zig-zag. The compact list keeps ~44 px
targets, aligned scanning and native semantics at ~29% height reduction
(7 items: 436 px -> ~310 px; 20 items: ~880 px vs 1,240 px).

## D2 — Semantics: action list, not listbox

Keep `role="list"` (native `<ul>`), buttons with descriptive accessible names
(`aria-label="Adicionar {display_name}[ — {state}]"`). No
`role="listbox"`/`option`, no `aria-pressed` (buttons only add; toggling is
done by removing the chip). "Carregar mais" stays outside the list.

## D3 — Selected-state synchronization

- Result already in selection: text `Selecionada`, `aria-disabled="true"`,
  click/Enter does not re-add (JS guard; `aria-disabled` alone does not block
  events), focus is preserved. Accessible name becomes "... — Já
  selecionada".
- Removing a chip re-enables the matching result (id lookup), announces the
  removal, and moves focus to the next remove button or the search field.
- Adding a tag: chip appears immediately, the result flips to `Selecionada`,
  focus stays on the result button, and `data-tag-status` announces
  "{display_name}[, {state},] adicionada à seleção." — not "filter applied"
  (form submission stays a separate step).

## D4 — Keyboard model

- Search field: `aria-controls="tag-search-results"`; ArrowDown opens and
  focuses the first result, ArrowUp the last; typing keeps current behavior.
- Results: ArrowDown/ArrowUp cycle buttons, Home/End jump to first/last,
  Enter/Space use native activation (no double fire), Esc hides results and
  returns focus to the search field without clearing the term; Tab leaves
  naturally (no focus trap).

## D5 — Status announcements and stale-response guard

`data-tag-status` gains `aria-atomic="true"` (keeps `aria-live="polite"`).
Messages: "Buscando tags...", "N resultados encontrados.", "N de M resultados
carregados.", "Nenhuma tag visível encontrada." plus add/remove
confirmations. `load()` rejects responses that arrive after a newer request
(request generation counter). The current click handler must stop erasing
the status line.

## D6 — What must not change

- Native `<select multiple>` fallback (including historical selected
  options), server-rendered contract, `tag_lookup` payload (`name` already
  present), `AllowedTag.display_name` namespace rule, selected-chip markup
  and appearance, manual `tag_filter` marker, ANY/ALL mode control,
  visibility/authorization rules, "Carregar mais" pagination contract.
- Pre-existing selected-chip contrast debt is not expanded (the new pill uses
  `bg-light text-dark`); fixing chip contrast is out of scope.

## D7 — Verification

- Unit/Django: focused suites for the selector surfaces (patient list, map,
  preferences) stay green; the template test surface asserts the new
  attributes (`aria-controls`, `aria-atomic`) as the server contract.
- Visual: headless Chrome screenshots of the real component at desktop and
  390 px widths, before/after, with fixture tags including an archived one
  and a long name; the ~44 px target height is confirmed from the rendered
  button (not assumed).
- Edge cases: global tag (no pill), same name in two teams, long single
  words, 320 px width, focus visibility on row corners.

## D8 — Rollout

Single slice; JS + template attributes + build output + tests. No migration,
no feature flag, no deploy step.
