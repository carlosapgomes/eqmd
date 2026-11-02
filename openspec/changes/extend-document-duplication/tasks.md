# Tasks: extend document duplication

Order: S1 and S2 are independent and may run in any order; S3 is
independent; S4 runs LAST (touches `patient_timeline.html`, which the
in-flight `harden-discharge-report-collaborative-draft` change also
modifies — verify the shared file against the current base before
starting S4).

Note: `.gitignore` ignores `openspec/changes/*/`; versioning this change
requires `git add -f openspec/changes/extend-document-duplication/`
(Git is handled by the operator, per `AGENTS.md`).

## 1. Slice 001 — report duplication

- [x] 1.1 Implement `ReportDuplicateView`, route, form, and duplicate
      template per `slices/slice-001-report-duplication.md`
      (TDD: RED → GREEN → REFACTOR).
- [x] 1.2 Add the duplicate action to the timeline report card.
- [x] 1.3 Focused suites green; full suite green; no new findings.

Contract: `slices/slice-001-report-duplication.md`

## 2. Slice 002 — prescription duplicate action on the timeline card

- [x] 2.1 Add the POST duplicate form to the prescription event card
      per `slices/slice-002-prescription-card-duplicate.md`
      (TDD: RED → GREEN → REFACTOR).
- [x] 2.2 Focused suites green; full suite green; no new findings.

Contract: `slices/slice-002-prescription-card-duplicate.md`

## 3. Slice 003 — duplication POST regression coverage (text apps)

- [ ] 3.1 Add POST-creates-an-independent-copy tests for daily note,
      simple note, and history and physical duplication per
      `slices/slice-003-duplication-post-tests.md`.
- [ ] 3.2 New tests green immediately (coverage slice — any failure is
      a bug finding, escalate instead of patching silently).

Contract: `slices/slice-003-duplication-post-tests.md`

## 4. Slice 004 — URL namespace consistency (runs last)

- [ ] 4.1 Standardize the three text apps on the short namespace per
      `slices/slice-004-url-namespace-consistency.md`.
- [ ] 4.2 Repository grep returns zero long-form references; full suite
      green.

Contract: `slices/slice-004-url-namespace-consistency.md`
