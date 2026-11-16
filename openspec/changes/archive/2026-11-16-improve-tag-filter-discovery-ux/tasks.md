# Tasks: Improve tag filter discovery UX

## Execution Contract

Implement one slice at a time, in order, only after the change and its slice are
approved. Each slice is a vertical delivery with its own failing-before
evidence, focused/project gates and runtime report. The operator/reviewer owns
task updates; implementation workers do not check this file, start the next
slice, commit, merge, deploy or archive.

Read `design.md`, the applicable delta specs and `verification.md` before every
slice. The accepted previous slice report is the interface handoff for the next
one. No schema change or shared-database fixture mutation by a worker is
approved by these tasks.

## 1. S1 — Clarify filter language and recovery

- [x] 1.1 Deliver task-oriented labels, text Apply/removal affordances and
      filtered-versus-unfiltered empty states on patient list, map and report
      catalogue. Prove template/view regressions and scoped desktop/mobile
      browser scenarios without changing filtering or application behavior.
      Contract: [S1](slices/slice-001-filter-language-and-recovery.md).
      Report: `/tmp/sirhosp-slice-TFUX-S1-report.md`.

## 2. S2 — Stabilize patient/map explicit selection

- [x] 2.1 Deliver normalized draft-versus-applied state, explicit Apply for all
      patient/map predicates, bounded option-panel open/close behavior and
      accessible chip/removal presentation. Verify both patient surfaces,
      keyboard/mobile/long-name behavior and preference/filter regressions.
      Contract: [S2](slices/slice-002-stable-patient-tag-selector.md).
      Dependency: S1 accepted. Report:
      `/tmp/sirhosp-slice-TFUX-S2-report.md`.

## 3. S3 — Unify report catalogue discovery

- [x] 3.1 Deliver explicit name/tag Apply, searchable lookup/chips, preserved
      scoped shortcuts and restorable history in `/reports/templates/`, with a
      reports-owned visibility-safe lookup and native fallback. Keep report
      creation on its last accepted controller without duplicate activation.
      Contract: [S3](slices/slice-003-searchable-template-catalogue.md).
      Dependency: S2 accepted and actual selector hook handoff. Report:
      `/tmp/sirhosp-slice-TFUX-S3-report.md`.

## 4. S4 — Preserve report creation with selector parity

- [x] 4.1 Deliver the same explicit searchable discovery in report creation,
      content/model preservation and Back/Forward safety. Verify EasyMDE,
      selected/outside-results model behavior, no clinical POST/navigation,
      no-JS fallback and catalogue/patient regressions.
      Contract: [S4](slices/slice-004-report-creation-selector-parity.md).
      Dependency: S3 accepted and actual catalogue integration handoff. Report:
      `/tmp/sirhosp-slice-TFUX-S4-report.md`.

## Requirement Coverage

All names below refer to this change's delta specs, not only the baseline
specifications.

- **Explicit draft and applied filter states:** S2 GET/browser pending matrix.
- **Task-oriented filters and filtered-empty recovery:** S1 template tests and
  zero-state browser checks.
- **Bounded dismissible tag options:** S2 DOM measurements and keyboard/mobile
  browser checks.
- **Accessible patient filter actions:** S1 labels plus S2 target/contrast
  evidence.
- **Explicit report discovery draft state:** S3 catalogue and S4 creation
  network/browser matrix.
- **Searchable report tag selection:** S3 safe lookup and S4 clinical-state
  browser evidence.
- **Restorable report discovery history:** S3/S4 Back/Forward and history-entry
  assertions.
- **Filtered-empty template recovery:** S1 view tests and S3 dynamic empty-state
  regression.
- **Accessible report discovery controls:** S3/S4 mobile and accessibility
  proof.
- **Dynamic report template name discovery:** S3/S4 explicit Apply replacing
  typing-driven model-result refresh.

## Project Gates and Completion

Each slice runs the focused commands in its contract and all applicable gates
in `AGENTS.md` and `docs/workflows/coding-standards.md`, including the project
test suite, scoped Python lint/type checks, `git diff --check`, frontend source
build and generated-output inspection. Markdown changes require
`markdownlint-cli2` on touched `.md` files.

Runtime artifacts are evidence only when they identify the actual served
checkout, use approved fixtures and satisfy `verification.md`. Test failures,
missing fixtures, stale served code or absent browser tooling are reported as
blockers, never waived. Existing content-preservation and privacy behavior that
already passes is regression evidence, not retroactively labelled RED.

The change is complete only after all four independent slice acceptances, an
end-to-end final browser matrix and `openspec validate
improve-tag-filter-discovery-ux --strict` pass on the final tree.
