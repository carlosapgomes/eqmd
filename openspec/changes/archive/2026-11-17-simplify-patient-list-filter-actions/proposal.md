# Proposal: Simplify patient-list filter actions

## Why

The patient list repeats tag-removal actions and labels a return to automatic
specialty filtering as "Limpar filtros". Users cannot reliably distinguish
editing a draft, removing filters and returning to saved defaults.

## What Changes

- Provide one action bar: Apply, true clear-all and tag-scoped specialty restore.
- Remove duplicate applied-clear/restore links and make the applied summary
  informational, including in filtered-empty states.
- Keep existing draft-chip removal and native deselection; do not add another
  bulk-clear button in this first delivery.
- Show preference status from the filters actually applied, not record existence.
- Preserve first-entry profile defaults and existing preference persistence.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `patient-tag-filtering`: list-specific canonical actions and truthful state,
  with scoped updates to existing wording/accessibility requirements.

## Impact

Patient-list templates, a list-only context/query helper and focused tests.
Shared components gain an opt-in list presentation while their default map
behavior stays unchanged. Existing JS, asset wiring and lookup protocols remain
untouched. No data migration, new permission, endpoint, dependency or preference
storage change.

## Non-Goals

Map/report UX changes, a new bulk-selection-clear control, a redesign of
matching or privacy policy, automatic preference saving, asynchronous patient
result filtering and JS refactors.

## Delivery

Planning only. One vertical slice after operator approval; no implementation,
commit, merge, archive or shared-stack deployment is authorized by this proposal.
