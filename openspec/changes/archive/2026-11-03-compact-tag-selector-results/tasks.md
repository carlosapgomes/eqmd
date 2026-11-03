# Tasks: compact-tag-selector-results

## 1. Slice-001 — compact selector results

- [x] 1.1 Rewrite `resultButton()` as a one-line full-row button (name, team
      pill, state text; omitted when absent) with accessible names, keeping the
      action-list semantics and "Carregar mais" outside the list
- [x] 1.2 Synchronize selection state: `Selecionada` + `aria-disabled` on
      matching results, no re-add, chip removal re-enables the result, focus
      preserved on both paths
- [x] 1.3 Keyboard and announcements: `aria-controls` on the search field,
      Arrow/Home/End/Esc handling, `aria-atomic` status messages for searching/
      counts/add/remove, stale-response rejection in `load()`
- [x] 1.4 Evidence and regressions: template attribute contract asserted in
      tests, focused suites green on list/map/preferences surfaces,
      `npm run build` deterministic output, before/after screenshots at desktop
      and 390 px (fixture incl. archived and long names), full suite,
      `git diff --check`, `openspec validate --strict`
