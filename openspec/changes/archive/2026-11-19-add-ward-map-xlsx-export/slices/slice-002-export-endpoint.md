# WMX-S2 — Export endpoint

## Identity

- Change: `add-ward-map-xlsx-export`.
- Task: [tasks.md §1 / 1.2](../tasks.md#1-deliver-the-export).
- Depends on WMX-S1 (the workbook service) being accepted. One vertical
  slice: view, URL and response behavior only. No template change.

## Objective

A named endpoint exports the map's current search/filter result as an XLSX
attachment with the map's exact context resolution and permission gates,
refusing empty results.

## Read First

- `AGENTS.md` and `docs/workflows/coding-standards.md`.
- This change's proposal, [design](../design.md) and
  [delta spec](../specs/patient-map-export/spec.md).
- The WMX-S1 contract and `apps/patients/services/ward_map_export.py`.
- `apps/patients/views.py::WardPatientMapView` (context resolution and the
  inherited `get()` AJAX branch).
- `apps/patients/views_ward_map_filters.py` and `apps/patients/urls.py`.
- `apps/patients/tests/test_ward_map_tag_filters.py` (helpers:
  `make_user`, `make_patient`, `seed_warm_cache`).

## Scope

### Included

- `WardMapExportXlsxView(WardMapFilterActionsView)` overriding `get()`:
  inherited `get_context_data()`, empty-result refusal (409 + plain-text
  message, no attachment), workbook build, `BytesIO` response with the
  XLSX content type and timestamped attachment filename.
- URL `path("map/export/", ..., name="patient_map_export")`.
- Integration tests: auth gates, response shape, filter parity, refusal.

### Excluded

- The button and template (WMX-S3).
- Any edit to the map view's rendering, the AJAX branch or the service.

### Files allowed

- `apps/patients/views_ward_map_export.py` (new)
- `apps/patients/urls.py` (add the one named route next to `map/`)
- `apps/patients/tests/test_ward_map_export_view.py` (new)

No other file may be created or modified in this slice.

## Requirements and Planned Evidence

- Anonymous request redirects to login; authenticated without
  `patients.view_patient` gets 403. Evidence: request tests.
- Warm cache + patients: 200 with the XLSX content type,
  `Content-Disposition: attachment` and filename matching
  `mapa_pacientes_YYYYMMDD_HHMMSS.xlsx`; body loads as a valid workbook.
  Evidence: header assertions plus `load_workbook(BytesIO(...))`.
- Parity: with `?q=`, `?ward=` and `?tag_filter` variants, including one
  with repeated query parameters, the exported patients equal the
  `ward_data` rows the map view itself renders for the same query string.
  Evidence: per-filter assertions comparing view context rows to workbook
  sheets.
- Empty result (filters matching nothing, an expired/missing cache, or
  filters matching nothing while `show_empty_wards=true` retains empty
  wards at zero total patients) refuses identically: 409, plain-text
  explanation, no attachment header. Evidence: the three cases.
- A request bearing the AJAX header still answers with the file (the
  inherited tree-partial branch is not used by this view). Evidence: header
  variant test.

## Failing-Before Plan

1. Endpoint tests fail on import (no view module / no URL name).
2. Pin the parity requirement first against the existing map view (red),
   then add the view.
3. Pin the refusal before implementing the guard.

## Implementation Constraints

- Follow design D1/D5: inherit `WardMapFilterActionsView`, call
  `get_context_data()` exactly once, refuse on `total_patients == 0`,
  never read the cache or re-resolve preferences.
- The view stays thin; no workbook logic here (consume the WMX-S1 service).
- Do not modify the map view, the AJAX partial or any template.

## Validation

```bash
./scripts/test.sh apps.patients.tests.test_ward_map_export_view \
  apps.patients.tests.test_ward_map_export
```

Plus AGENTS.md scoped gates for the changed files.

## Acceptance Criteria

- [ ] Inherited permission gates hold for the endpoint.
- [ ] Attachment response is a valid workbook with a timestamped filename.
- [ ] Exported patients equal the map's rendered rows for the same filters.
- [ ] Empty result refuses with 409 and no file.
- [ ] All new tests pass; no file outside the allowed list changed.

## Escalation

Stop and report `BLOCKED_NEEDS_DECISION` for: any need to alter the map
view or context contract, permission surprises, or a WMX-S1 service gap.

## Evidence Report and Worker Handoff

Write `/tmp/eqmd-ward-map-xlsx-export/WMX-S2-report.md` with
`READY_FOR_REVIEW` or `BLOCKED_NEEDS_DECISION`, requirement-to-evidence
mapping, changed paths, RED/GREEN proof and commands with exit statuses.

```text
Implement only approved WMX-S2 using this contract and referenced artifacts.
Reconstruct fresh context; follow repository engineering policy.
Produce failing-before evidence, implement minimally and validate.
Write /tmp/eqmd-ward-map-xlsx-export/WMX-S2-report.md and stop for review.
Do not update tasks.md, commit, push, merge, archive or start another slice.
```
