# Tasks: Report-template filter corrections

## 1. Truthful navigation feedback

- [x] 1.1 RTFA-S1 — End false AJAX loading and duplicate overlay IDs while
      preserving real navigation and cache-safe bundle delivery.
      Contract: [RTFA-S1](slices/slice-001-fix-navigation-feedback.md).
      Report: /tmp/sirhosp-slice-RTFA-S1-report.md.

## 2. Canonical catalogue actions

- [x] 2.1 RTFA-S2 — Deliver true clear-all, scoped restore, clean post-action
      controls, conditional visibility and a consistent accessible action bar.
      Contract: [RTFA-S2](slices/slice-002-canonical-catalogue-actions.md).
      Dependency: accepted RTFA-S1.
      Report: /tmp/sirhosp-slice-RTFA-S2-report.md.

## Execution Boundary

Planning is complete only when proposal, both delta specs, design, verification
and both slice prompts are consistent. Implementation requires separate
operator approval. Execute one slice with RED/GREEN/refactor/gates, then stop.
Workers do not check these boxes, sync canonical specs, archive or perform Git
writes. Evidence and any expansion decision belong in the slice report.

These two slices are vertical: S1 makes the currently shipped interactions
usable without changing their scopes; S2 then ships the approved catalogue
contract. Report creation is a protected regression surface, not another
product slice. No migration, shared fixture/cache operation or service lifecycle
change is authorized.

## Closure — 2026-11-18

The operator authorized synchronization and archival after integrating the
implementation into main at commit `0a2a560`. The execution-boundary text above
records the original planning restrictions, not outstanding implementation.
All listed slices are complete; execution results and review limitations are
recorded in [verification](verification.md#execution-record--2026-11-18).
No application changes or Git writes are part of this closure.
