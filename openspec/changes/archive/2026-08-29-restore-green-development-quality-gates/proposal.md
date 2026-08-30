# Proposal: Restore Green Development Quality Gates

## Why

The repository cannot currently provide a trustworthy regression signal for
critical clinical work. The verified baseline runs 2,029 tests and ends with
157 failures, 416 errors, and 12 skipped tests. The failures span ten apps and
include stale test fixtures, lifecycle redirects, outdated model/API
contracts, static-analysis debt, non-deterministic dependency installation,
and Django 6.1 running where project documentation specifies Django 5.2.1.

The patient-identity change is functionally green in focused tests but remains
formally incomplete because repository gates are red. Continuing its later
slices would allow new regressions to hide inside known failures.

This change restores deterministic, green development gates before critical
patient-identity work resumes. It follows up on
`stabilize-test-suite-lifecycle-gates`, preserving that change's completed
lifecycle helper and failure classification rather than reopening it as an
unbounded cleanup effort.

## Risk Assessment

**Level:** CRITICAL (HIGH/ARCH)

The deterministic classifier returned CRITICAL because the change affects the
Django runtime, dependency lock, container build, CI/tooling behavior, and more
than five applications. It may expose real production defects while repairing
stale tests. An ADR, rollback plan, strict slice isolation, and third-LLM
verification are therefore mandatory.

## What Changes

- Align local containers, CI, and lock resolution on the documented Django 5.2
  LTS minor line.
- Make Ruff and Mypy reproducible development dependencies rather than tools
  installed ad hoc into a running container.
- Make quality scripts fail closed when required tooling is unavailable.
- Restore scoped Ruff, format, Mypy, migration, and test gates.
- Repair failing tests in small app/domain cohorts, using existing failures as
  RED evidence.
- Correct production behavior only when an authoritative spec or established
  contract proves the implementation is wrong; otherwise update stale tests.
- Require each targeted module/app to reach zero failures and errors before the
  next slice.
- Finish with a green full suite and re-verification of the blocked
  patient-identity slice 001.

## Baseline Inventory

Verified baseline on 2026-08-23:

| App                       | Failures and errors |
| ------------------------- | ------------------: |
| `mediafiles`              |                 200 |
| `patients`                |                 145 |
| `pdf_forms`               |                  85 |
| `drugtemplates`           |                  74 |
| `outpatientprescriptions` |                  33 |
| `historyandphysicals`     |                  20 |
| `events`                  |                   9 |
| `matrix_integration`      |                   3 |
| `pdfgenerator`            |                   2 |
| `sample_content`          |                   2 |

Full summary: `Ran 2029 tests`, `failures=157`, `errors=416`, `skipped=12`.
These are aggregate counts only; no production or identifiable patient data
belongs in artifacts or reports.

## Capabilities

### Added Capabilities

- `deterministic-development-runtime`: lock-backed Django and toolchain parity
  across Docker and CI.
- `contract-first-test-restoration`: repeatable rules for deciding whether a
  failing test or production behavior must change.
- `green-quality-gate-baseline`: module, app, and repository gates with zero
  failures and errors.

### Modified Capabilities

- `test-auth-fixture-baseline`: complete adoption of the existing
  navigation-ready user factory and lifecycle guard rail.
- `test-suite-signal-to-noise`: progress from tolerated failures to an enforced
  zero-failure baseline.

## Included Scope

- `pyproject.toml`, `uv.lock`, Docker development/runtime dependency setup,
  quality scripts, and relevant CI gates.
- Static quality debt that directly blocks touched patient files.
- Test fixtures and tests in the ten failing apps listed above.
- Minimal production corrections proven by authoritative contracts and new or
  existing regression tests.
- Aggregate failure manifests and temporary slice reports.

## Excluded Scope

- New product features.
- Patient duplicate consolidation or slices 002-004 of the identity change.
- Broad redesigns of clinical workflows without a separate approved change.
- Database resets, restored-production-data mutation, destructive commands, or
  SQLite support.
- Changes made only to silence a test without resolving its contract.
- Blanket lint/type ignores or weakening/removing assertions to obtain green.

## Success Criteria

- Docker development and CI resolve the same supported Django minor line from
  `uv.lock`.
- Ruff and Mypy are available without runtime package installation.
- `manage.py check`, Ruff, format, scoped Mypy, lock, and global migration-drift
  checks pass.
- Every targeted module and app reaches exit code 0 with zero failures/errors.
- `./scripts/test.sh` ends with exit code 0 and zero failures/errors.
- The lifecycle guard rail enforces zero unapproved bare-user fixtures.
- No report contains real PII or patient-level production data.
- Slice 001 of `harden-patient-identity-and-duplicate-prevention` is rerun and
  may be marked complete only after all its original gates pass.

## Rollback Summary

- Runtime/toolchain slices are reverted as one lock-backed unit: dependency
  declaration, lockfile, Docker target, scripts, and CI.
- Test-only slices can be reverted independently by cohort.
- Any production correction must include its own regression test and explicit
  rollback note in the slice report.
- No migration or production-data mutation is permitted by this change.
