# Proposal: Simplify report-template filter actions

## Why

The catalogue's AJAX links also trigger the global page-navigation overlay,
blocking interaction until its 15-second timeout despite fast successful
responses. Clear/restore can update results while leaving old chips/mode in
the editor, making the actions appear ineffective or reversible by Apply.

The operator approved matching the clearer patient list/map action contract.
The diagnosis is recorded in /tmp/reports-template-tag-filter-analysis.md.

## What Changes

- Separate real document navigation from cancelled/AJAX interactions and
  render exactly one global loading overlay.
- Keep genuine navigation feedback and deliver updated global assets safely.
- Give /reports/templates/ one left-aligned action bar: Aplicar filtros,
  Limpar todos os filtros and conditional Usar padrão de tags da especialidade.
- Make clear-all remove name/tags/options and suppress defaults on reload.
- Restore applied name and specialty tags/mode while discarding pending edits.
- Rebuild controls through full GET navigation for those two explicit actions.
  Apply and catalogue pagination retain their existing AJAX transport.
- Make the catalogue applied summary read-only; keep draft-chip removal local.
- Remove repeated empty-state actions and retain accessible draft targets.
- Preserve report creation's filtering/editor behavior and legacy query URLs.

The catalogue UI contract intentionally changes. No endpoint is added or
renamed, and existing tag-only URLs remain compatible.

## Capabilities

### New Capabilities

- `page-navigation-feedback`: truthful loading feedback for document navigation,
  excluding intercepted interactions and duplicate overlays.

### Modified Capabilities

- `reports`: canonical catalogue actions, clean post-action controls and
  single-bar recovery, explicitly distinct from report-creation discovery.

## Impact

Shared page-loading JavaScript and base templates; catalogue presentation,
a bounded context adapter/service, a narrow catalogue-only transport bridge
and tests. Existing Webpack build/versioned-static mechanisms are reused.
No new dependency, schema, permission, preference store or clinical write.

## Risk and Boundaries

PROFESSIONAL / FEATURE: a multi-file UI contract with cross-page loading
impact, not a trivial isolated bugfix. Design and cross-surface regression
are required. Authorization, persistent data and clinical rules do not change.

Do not change report creation's JSON controller, selection, title, date or
editor semantics. No patient list/map behavior change, shared cache operation,
service lifecycle change, migration, Git write or release deployment is planned.

## Delivery

Planning only. RTFA-S1 fixes navigation feedback; RTFA-S2 then delivers the
catalogue contract. Implement one approved slice, verify and stop.
Current approval covers this plan, not implementation or archive.
