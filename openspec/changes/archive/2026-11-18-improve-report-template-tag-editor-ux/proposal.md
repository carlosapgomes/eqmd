# Proposal: Improve report-template tag editor UX

## Why

Creating a model with several tags and removing its last tag currently require
Ctrl/Cmd-click in a native multiple select. The operator confirmed both problems.
The backend already supports zero or more tags; the editor needs usable controls,
not weaker validation or a new persistence workflow.

## What Changes

- Give template creation and update a searchable selection of existing,
  editor-authorized tags.
- Add several tags by ordinary click/tap, with selected chips and a named
  removal button on each chip, including the last.
- Keep all tag edits pending until Criar/Salvar Modelo. Preserve name, markdown,
  active/public switches and other unsaved form values during selection.
- Search locally within the existing server-offered choices; do not use the
  broader read-only discovery lookup or add an endpoint.
- Keep the current POST contract, protected-link retention, historical labels,
  ownership rules and native no-JS fallback with modifier-key guidance.
- Deliver the editor asset through the existing build/versioning mechanism.

No breaking endpoint or submitted-field change is intended.

## Capabilities

### New Capabilities

None; template classification remains owned by reports.

### Modified Capabilities

- `reports`: optional classification gains usable enhanced multiple selection,
  explicit last-chip removal, deferred form persistence and accessible controls.

## Impact

The shared template create/update form, one editor-owned partial and small
JavaScript module, a Webpack copy entry, and focused tests.
No form/model/service/policy change, migration, new dependency or lookup API.
Read and mutation authority remain deliberately different.

## Scope and Risk

PROFESSIONAL / FEATURE: both editor surfaces and their submission boundary need
integration/browser proof. Existing association writes and audit are unchanged.

Patient report creation/update, discovery filters, the prior RTFA-S1/S2 change,
patient selectors, preferences, clinical data and the tag catalogue are out of
scope. No inline creation of catalogue tags, bulk-clear action or default restore
is added.

## Delivery

Planning only. One vertical slice, RTTE-S1, covers both editors because they
already share the form/template and persistence path. Separate implementation
approval is required. Do not commit, sync canonical specs or archive.
