# Tasks: Simplify patient-map filter actions

## 1. Deliver the map filter contract

- [x] 1.1 PMFA-S1 — Deliver canonical map actions, truthful origin/totals and
      filter-aware ward/zero-result messages in full and AJAX rendering.
      Contract: [PMFA-S1](slices/slice-001-simplify-map-filter-actions.md).
      Evidence: `/tmp/sirhosp-slice-PMFA-S1-report.md`.

## Completion Evidence

The operator accepted the implementation and visual amendment, and authorized
spec synchronization, checklist closure and archive on 2026-11-17.

- Final focused validation: 235 tests OK, 31 skips, zero failures/errors.
- Final Chrome validation: 30 groups, including both surfaces at three widths.
- Pre-amendment full suite: 4,140 IDs, 4,084 passed and 56 skipped in 32 batches.
  This historical full run is not a new full-suite claim for the visual polish.
- Scoped lint/type/format, OpenSpec and Markdown gates pass.
- Isolated fixtures preserve snapshots and roll back to zero owned rows.
- Latest report: `/tmp/sirhosp-slice-PMFA-S1-layout-report.md`.
- Shared cache generation/repair and Git operations remain excluded.

## Execution Boundary

One vertical slice. Operator approval is required before implementation.
The worker does not update this file, commit, merge, archive or start another
change. All implementation, regression and runtime evidence belongs to S1.

Cache generation/scheduling/TTL, stale fallback repair and shared-cache writes
are explicitly excluded. Isolated test-database fixtures with healthy map cache
are permitted under the standard test command; do not run the shared generator
to make verification possible.

## Requirement Coverage

- R1: one action bar, conditional restore and informational applied summary.
- R2: true clear-all with manual-empty persistence and unchanged eligibility.
- R3: restore applied search/ward/show-empty, discard pending drafts.
- R4: draft ×, native empty Apply and enhanced clean Apply.
- R5: effective-filter labels distinct from manual origin/display options.
- R6: helper, per-ward messages and global zero notice in both variants.
- R7: truthful preference-source matrix without new persistence.
- R8: preserved list/reports/privacy/cache contract and scoped regression proof.
