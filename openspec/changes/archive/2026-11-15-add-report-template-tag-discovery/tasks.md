# Tasks: Report template tag discovery

## Execution Contract

Implement one slice at a time after approval of the change and its
prerequisites.
Each checkbox includes its own tests, runtime verification and evidence report.
The operator/reviewer owns task updates; implementation workers do not check off
this file or start the next slice. Migration approval is a separate prerequisite
for S1, as defined in design Migration Plan. Read `verification.md` before
execution; fixture provisioning and cleanup belong to the operator. Each
accepted
slice report must include design D7's actual interface handoff. Optional helpers
are not dependencies; the next worker consumes only interfaces actually
delivered.

## 1. S1 — Classify a report template end to end

- [x] 1.1 S1 — Deliver authorized optional classification in create/edit,
      visible badges, safe retention and attributable history. Verify the
      contract's focused tests, `./scripts/test.sh apps.reports`, browser
      scenario and `/tmp/sirhosp-slice-S1-report.md`.
      Contract: [S1](slices/slice-001-classify-report-templates.md).
      Dependencies: approved migration generation; operator-applied schema for
      UI proof.

## 2. S2 — Discover models in the catalogue

- [x] 2.1 S2 — Deliver default-aware tag filtering and dynamic name search in
      `/reports/templates/`, with tests, paginated fallback and scoped browser
      evidence. Verify the contract's focused tests,
      `./scripts/test.sh apps.reports`, browser scenario and
      `/tmp/sirhosp-slice-S2-report.md`.
      Contract: [S2](slices/slice-002-discover-report-template-catalogue.md).
      Dependency: S1 accepted by the operator/reviewer.

## 3. S3 — Discover models during report creation

- [x] 3.1 S3 — Deliver the same discovery in the report-creation selector,
      bounded choices, safe current-selection retention and content
      preservation. Verify `./scripts/test.sh apps.reports`, the contract's
      browser scenario and `/tmp/sirhosp-slice-S3-report.md`.
      Contract: [S3](slices/slice-003-discover-models-during-report-
      creation.md).
      Dependency: S2 accepted by the operator/reviewer.

## Requirement Coverage

All requirement names below refer to `specs/reports/spec.md`.

| Spec requirement                           | Primary slice and evidence    |
| ------------------------------------------ | ----------------------------- |
| Optional report template classification    | S1 CRUD tests and browser     |
| Per-tag mutation authority                 | S1 forged/stale request tests |
| Safe retention of associations             | S1 retention tests            |
| Audited association changes                | S1 audit/rollback             |
| Visibility independent of tag metadata     | S1–S3 privacy tests           |
| Consistent tag matching                    | S2–S3 parity                  |
| Shared discovery specialty defaults        | S2–S3 defaults                |
| Explicit discovery override and validation | S2–S3 options/validation      |
| Dynamic name discovery                     | S2–S3 browser                 |
| Discovery preserves creation state         | S3 browser/form tests         |

## Project Gates and Completion

Each slice references `AGENTS.md` and the canonical engineering policy for
project-required gates, in addition to the focused commands above. Source asset
changes require the existing frontend build; docs changes require Markdown lint.
Browser proof must identify the actually served checkout and approved test data;
the draft-supervision harness alone is not evidence of this feature. Follow
`verification.md` for Playwright routing, fixture manifests and evidence
scripts.
S2/S3 browser proof includes loading historical choices without navigation and
preserving selected historical tags when hiding unselected historical choices.

Artifact completeness is not implementation completion. All three tasks remain
open until their contracts and evidence are independently accepted.
