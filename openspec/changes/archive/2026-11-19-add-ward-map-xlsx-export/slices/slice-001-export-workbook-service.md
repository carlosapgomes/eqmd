# WMX-S1 — Workbook service

## Identity

- Change: `add-ward-map-xlsx-export`.
- Task: [tasks.md §1 / 1.1](../tasks.md#1-deliver-the-export).
- One vertical slice: workbook-building service and unit tests only. No
  endpoint, no URL, no template.

## Objective

A pure, typed service turns already-resolved map rows into one XLSX
workbook: one sheet per surviving ward, five fixed columns with fixed
widths, a labeled identification cell and the latest published evolution
per patient.

## Read First

- `AGENTS.md` and `docs/workflows/coding-standards.md`.
- This change's proposal, [design](../design.md) and
  [delta spec](../specs/patient-map-export/spec.md).
- `apps/patients/services/ward_tag_overlay.py` (the row contract consumed).
- `apps/core/management/commands/update_ward_mapping_cache.py` (the cached
  payload keys).
- `apps/dailynotes/models.py` and the default manager's draft/deletion
  exclusions in `apps/events/models.py`.
- `apps/research/views.py::export_search_results` (the styling precedent).
- `apps/patients/tests/test_ward_map_tag_filters.py` (fixture helpers).

## Scope

### Included

- `build_ward_map_workbook(ward_data, *, today)` in the new service module.
- Sheet-title sanitization/dedupe, header styling, fixed widths, the
  identification block, batched identity and evolution queries, the
  cell-limit truncation and the filename helper.
- Unit tests for all of the above.

### Excluded

- The view, URL, template and button (WMX-S2/WMX-S3).
- Any edit to the map view, cache, tag services or research export.

### Files allowed

- `apps/patients/services/ward_map_export.py` (new)
- `apps/patients/tests/test_ward_map_export.py` (new)

No other file may be created or modified in this slice.

## Requirements and Planned Evidence

- One sheet per surviving ward in map order; a retained empty ward yields a
  header-only sheet. Evidence: unit tests over seeded row payloads.
- Five columns in order `Leito`, `Identificação`, `Médico/Interno`,
  `Evolução`, `Conduta`; `Conduta` blank everywhere. Evidence: assertions on
  every sheet.
- Identification block: six labeled lines, `DD/MM/AAAA` dates, day count from
  the injected `today`, blank values when missing, Internação line omitted
  without an admission date. Evidence: per-field assertions.
- Latest published evolution: newest by `event_datetime` (tie-break
  `-created_at`, then `-pk`); drafts (human and bot) and deleted notes
  excluded; no note leaves author and content blank. Evidence: fixture
  matrix including an equal-timestamp tie.
- Author cell uses `get_full_name()` with `username` fallback. Evidence:
  user fixture with and without profile names.
- Sheet titles: forbidden characters stripped, 31-character cap,
  abbreviation fallback to sanitized name, then the deterministic base
  `Ala` when both are empty, case-insensitive numeric dedupe (including
  suffixed titles). Evidence: adversarial ward names, a both-empty case
  and a case-only collision.
- Fixed widths 12 / 48 / 32 / 72 / 45 as named constants. Evidence: width
  assertions.
- Content truncated to the 32,767-character cell limit. Evidence: oversized
  note fixture.
- Literal-text safety: formula-like values (leading `=`) are stored as
  text with an explicit string data type; XML-illegal control characters
  are stripped from every exported value. Evidence: round-trip tests with
  a `=`-prefixed note, a formula-like bed and a control-character note.
- A cached row whose patient was soft-deleted during the cache TTL (absent
  from the identity query) is dropped entirely — identity and evolution
  included; the build never fails on the missing lookup. A discharge inside
  the window is not a drop (the patient still exists). Evidence:
  soft-deleted-patient fixture.
- At most two batched enrichment queries regardless of patient count;
  exactly two in the representative nonempty test (an empty patient set
  needs none). Evidence: `assertNumQueries`.

## Failing-Before Plan

1. Write the module's test suite first; it fails on import (no module yet).
2. Pin the sheet/column/width contract with a two-ward seeded payload
   before any query logic exists.
3. Add the evolution matrix (newest wins, drafts excluded, blank when none)
   before implementing the DISTINCT ON query.

## Implementation Constraints

- Follow design D2/D3/D6: constants, no magic numbers, functions ≤ 25
  lines, no business logic outside the service.
- `DailyNote` default manager only (draft/deleted exclusions come free);
  one PostgreSQL `DISTINCT ON` query with `select_related("created_by")`.
- openpyxl header styling replicates the research precedent (bold white on
  #366092, centered).
- Do not touch `views.py`, `ward_tag_overlay.py` or any template.

## Validation

```bash
./scripts/test.sh apps.patients.tests.test_ward_map_export
```

Plus AGENTS.md scoped gates for the changed files (ruff; typecheck if in
scope).

## Acceptance Criteria

- [ ] Sheets, columns, widths, titles (including `Ala` fallback and
      case-insensitive dedupe) and identification block match the delta
      spec.
- [ ] Evolution contract (newest published, deterministic tie-break, drafts
      excluded, blank when none) holds.
- [ ] Every exported value is literal text; control characters never fail
      the save.
- [ ] A soft-deleted-during-TTL cached row is omitted entirely; ordinary
      status changes keep the row.
- [ ] Enrichment queries stay within the batched bound, deterministic via
      the injected `today`.
- [ ] All new tests pass; no file outside the allowed list changed.

## Escalation

Stop and report `BLOCKED_NEEDS_DECISION` for: row-payload contract mismatch
with the real cache, a need to touch files outside the allowed list, or any
spec contradiction.

## Evidence Report and Worker Handoff

Write `/tmp/eqmd-ward-map-xlsx-export/WMX-S1-report.md` with
`READY_FOR_REVIEW` or `BLOCKED_NEEDS_DECISION`, requirement-to-evidence
mapping, changed paths, RED/GREEN proof and commands with exit statuses.

```text
Implement only approved WMX-S1 using this contract and referenced artifacts.
Reconstruct fresh context; follow repository engineering policy.
Produce failing-before evidence, implement minimally and validate.
Write /tmp/eqmd-ward-map-xlsx-export/WMX-S1-report.md and stop for review.
Do not update tasks.md, commit, push, merge, archive or start another slice.
```
