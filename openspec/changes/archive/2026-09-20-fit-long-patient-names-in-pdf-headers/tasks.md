# Tasks: Fit long patient names in shared PDF headers

## 0. Change preflight

- [x] 0.1 Record `BASE_REF` and confirm the working tree can preserve unrelated
      changes
- [x] 0.2 Confirm `eqmd_dev` is already running; obtain owner approval before
      any container lifecycle action
- [x] 0.3 Record the unavailable pre-change full baseline and substitute a
      post-review full `./scripts/test.sh` run

> The pre-change full baseline was blocked by container infrastructure. The
> post-review full suite passed all 2,789 tests with 25 skips.

## 1. Slice 001 - Hybrid patient-name fitting and safe geometry

- [x] 1.1 Add focused RED tests for preferred-size rendering, deterministic
      font reduction, wrapping, oversized-token preservation, and line-width
      bounds
- [x] 1.2 Extract the generic header canvas into a focused service module while
      preserving the existing `NumberedCanvas` import path
- [x] 1.3 Implement the pure 18 pt-to-12 pt shrink-then-wrap layout policy
- [x] 1.4 Derive separator position and default content-frame reservation from
      the fitted name block without changing the short-name baseline
- [x] 1.5 Prove prescription and discharge-report PDF validity and preserve
      custom-canvas/explicit-header behavior
- [x] 1.6 Run focused GREEN and nearby regression checks, then stop for
      independent review

## 2. Independent review

- [x] 2.1 Verify behavior against all specification scenarios
- [x] 2.2 Verify tests prove width and coordinate safety rather than text
      presence alone
- [x] 2.3 Verify the diff remains within the declared blast radius and does not
      alter persistence, routes, permissions, templates, or Daily Note layout
- [x] 2.4 Resolve all concrete P0/P1 findings before acceptance

## 3. Final quality gate

- [x] 3.1 Run Django check, focused Ruff/format, and scoped type checking
- [x] 3.2 Run shared PDF, prescription, discharge-report, and Daily Note focused
      regressions
- [x] 3.3 Run `./scripts/test.sh` once after slice acceptance
- [x] 3.4 Run
      `openspec validate fit-long-patient-names-in-pdf-headers --strict`
- [x] 3.5 Run `markdownlint-cli2` on changed Markdown files and record final
      evidence
