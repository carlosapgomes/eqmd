# Tasks: Simplify patient-list filter actions

## 1. Deliver the patient-list action contract

- [x] 1.1 PLFA-S1 — Deliver the single action bar, true clear-all, tag-scoped default
      restore, read-only summary and truthful preference labels. Verify the focused
      Django command, shared-surface regressions and saved-default browser matrix
      in [the slice contract](slices/slice-001-simplify-patient-list-actions.md).
      Evidence: `/tmp/sirhosp-slice-PLFA-S1-report.md`.

## Closure and Acceptance — 2026-11-17

The operator confirmed the live dev behavior: "ficou bom, está funcionando",
then authorized spec synchronization and archive. PLFA-S1 is accepted.

- Independent review: `meta/muse-wonder-1.0:high`, APPROVE_WITH_NITS.
  The optional admission-label correction was regression-tested and resolved.
- Browser: 19 scenario groups passed with genuine saved X/ALL test fixtures.
  This evidence is an isolated workspace preview, not a deployed-login claim.
- Dev: subsequently rebound to the worktree with operator authorization;
  readiness passed and operator functional acceptance followed.
- Full Django inventory: 4,124 unique IDs across 32 sequential passing batches.
  4,068 passed, 56 skipped; zero failures, errors or per-batch timeouts.
- Skips: 31 Node unavailable, 13 deprecated hospital tests, 8 Firebase disabled,
  3 ICD-10 search-vector setup and 1 fake-PDF factory case.
- Scoped Ruff/mypy, strict change/synced-spec OpenSpec and Markdown checks passed.
  The unchanged legacy test modules retain their baseline typing findings.
- Global strict OpenSpec validation retains 10 pre-existing placeholder Purpose
  warnings in other specs, verified identical against HEAD; no unrelated spec
  was edited.
- No new migration, permission, dependency or shared JS change was introduced.
- No Git commit or merge was performed by the assistant.

External evidence is temporary; the outcome summary above is retained here:

```text
/tmp/sirhosp-slice-PLFA-S1-report.md
/tmp/eqmd-validation-batches/20261117-plfa-s1/report.md
/tmp/eqmd-patient-list-filter-actions/20261116/
/tmp/eqmd-patient-list-filter-actions/20261117-env/
```

## Execution Boundary

One vertical slice; operator approval is required before implementation.
The implementation worker does not update this file, commit, merge, archive or
start another change. All feature tests and runtime evidence land with S1.

Read `verification.md` first. A blank-profile browser session alone does not
satisfy acceptance. Runtime fixtures, their cleanup and served-checkout identity
must be explicitly established; missing prerequisites are blockers.

## Requirement Coverage

- Canonical actions and read-only summary: S1 render tests and browser counts.
- True clear-all: S1 URL/follow/refresh/page and preference non-mutation tests.
- Tag-scoped restore: S1 applied-versus-pending browser and GET tests.
- Existing draft removal/no-JS: S1 interaction and native submission tests.
- Truthful preference context: S1 source-state matrix and saved-default browser.
- Modified wording/accessibility: S1 list assertions plus unchanged map/report
  regression evidence.
