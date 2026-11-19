# Tasks: Ward-map XLSX export

## 1. Deliver the export

- [x] 1.1 WMX-S1 — Workbook service: one sheet per surviving ward, five
      fixed columns, fixed widths, sanitized sheet titles, identification
      block and latest published evolution, all batch-queried and unit
      tested.
      Contract: [WMX-S1](slices/slice-001-export-workbook-service.md).
      Evidence: `/tmp/eqmd-ward-map-xlsx-export/WMX-S1-report.2bcf354c.md`
      (25 tests OK; review round applied; accepted by the operator on
      2026-11-19).
- [x] 1.2 WMX-S2 — Export endpoint: inherited context resolution, refusal on
      empty result, XLSX attachment response and the named URL.
      Contract: [WMX-S2](slices/slice-002-export-endpoint.md).
      Evidence: `/tmp/eqmd-ward-map-xlsx-export/WMX-S2-report.060d8cca.md`
      (16 view tests + 25 service tests OK; review round applied; accepted
      by the operator on 2026-11-19).
- [x] 1.3 WMX-S3 — Map button: enabled link carrying the current query
      string, disabled variant when the result is empty, placed above the
      results and outside the filter form, plus the full test suite.
      Contract: [WMX-S3](slices/slice-003-export-button-ui.md).
      Evidence:
      `/tmp/eqmd-ward-map-xlsx-export/WMX-S3-report.ebf4ae31.1bbcd7cf.md`
      (22 view tests OK; apps.patients 1007 OK; full suite 4222 OK,
      skipped=59; review round applied; accepted by the operator on
      2026-11-19).

## Execution Boundary

Planning only. Implementation requires operator approval and runs one
vertical slice at a time. The worker does not update this file, commit,
merge, archive or start another change. Cache generation/scheduling/TTL,
shared-cache writes and shared dev-data changes are excluded; isolated
test-database fixtures with a healthy seeded cache are permitted under the
standard test command.

## Requirement Coverage

- Export mirrors the applied map result — WMX-S2 (parity tests) over
  WMX-S1 rows.
- One sheet per surviving ward — WMX-S1.
- Patient identification block — WMX-S1.
- Latest published evolution only — WMX-S1.
- Sheet titles and readability — WMX-S1.
- Export availability control — WMX-S2 (endpoint refusal) and WMX-S3
  (button states and placement).
- Map permission gates — WMX-S2.
