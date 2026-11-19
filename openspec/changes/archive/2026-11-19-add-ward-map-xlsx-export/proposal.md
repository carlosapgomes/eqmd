# Proposal: Ward-map XLSX export

## Why

The ward map resolves a live, permission-filtered snapshot of inpatients per
ward, but ward rounds still transcribe it by hand into a spreadsheet (bed,
identification, last evolution and a blank conduct column to fill during the
round). The transcription is error-prone and slower than the data the system
already holds. An XLSX download of the exact search result removes the manual
step without changing any map behavior.

## What Changes

- New service that turns the already-resolved map rows into one XLSX
  workbook: one sheet per surviving ward, fixed columns `Leito`,
  `Identificação`, `Médico/Interno`, `Evolução` and `Conduta`, with the
  owner-approved fixed column widths.
- New export endpoint that reuses the map view's full context resolution, so
  the download is exactly the current search/filter result, and answers with
  an attachment download (the page stays on `/patients/map`).
- `Exportar xlsx` button above the map results and outside the filter form,
  disabled only when the filtered result has no patients.
- Only the latest published evolution is exported (drafts and deleted notes
  excluded; blank author/content when the patient has no published note).

## Capabilities

### New Capabilities

- `patient-map-export`: XLSX workbook export of the ward-map filtered result.

### Modified Capabilities

None. Map filtering, rendering, permissions and cache behavior are reused
unchanged.

## Impact

- New code: `apps/patients/services/ward_map_export.py`,
  `apps/patients/views_ward_map_export.py`,
  `apps/patients/tests/test_ward_map_export.py`,
  `apps/patients/tests/test_ward_map_export_view.py`.
- Existing edits: `apps/patients/urls.py` (one named route) and the full map
  template (one action row above the results card).
- No new dependency (openpyxl 3.1.5 is already a direct dependency), no
  schema/migration, no JavaScript, no build change, no cache change.

## Non-Goals

- No CSV/PDF export, no admin-facing export, no print styling.
- No change to map filters, permissions, eligibility or cache
  generation/scheduling/TTL.
- No audit-log feature and no per-role restriction of the button (owner
  accepted the privacy trade-off for ward-round use).
- No evolution editing, no approval workflow, no extra summary sheet.
- No growth of the legacy 1948-line `apps/patients/views.py`.

## Owner Decisions (2026-11-19)

- D1: drafts excluded; only the latest published evolution is exported.
- D2: the button is disabled when the filtered result is empty — no other
  disable criterion; direct endpoint calls with an empty result are refused.
- D3: permissions inherited from the map (login + `patients.view_patient`).
- D4: `Identificação` is one labeled multi-line cell.
- D5: sheet title is the sanitized ward abbreviation with dedupe.
- D6: without a published evolution the author and content cells are blank.
- D7: dates use `DD/MM/AAAA`.
- D8: fixed column widths 12 / 48 / 32 / 72 / 45.
- D9: the live server state wins over the cached snapshot — a cached row
  whose patient is absent from the live database (soft-deleted during the
  cache TTL) is omitted entirely, identity and evolution included; an
  ordinary status change inside the window (for example a discharge) keeps
  the row.
- The file is for exclusive use in nursing ward rounds; the team is aware of
  the LGPD/privacy rules. Full analysis:
  `prompts/ward_map_xlsx_export_feasibility.md`.

## Delivery

Planning only: three vertical slices — WMX-S1 (workbook service), WMX-S2
(export endpoint), WMX-S3 (map button). Implementation requires operator
approval and runs one slice at a time. This proposal does not authorize cache
generation, shared dev-data changes, Git commits, merge or archive.

An independent read-only plan review (fresh-context reviewer,
`openai-codex/gpt-6.1-terra:high`, report at
`/tmp/eqmd-ward-map-xlsx-export/plan-review-report.md`) returned `APPROVE
WITH CHANGES`; all findings were incorporated into the design, the delta
spec and the slice contracts: literal-text cell safety, the `Ala` sheet-title
fallback with case-insensitive dedupe, the deterministic `-pk` note
tie-break and sharper endpoint/button coverage. The review's soft-deleted
row question was resolved by the owner as decision D9.
