# Slice 005 - Patients API, Development, and Performance Fixtures

## Handoff for a zero-context implementer

Read the standard project/change artifacts, reports 001-004B, the shared user
factories/lifecycle guard, all listed tests, and the patient URLs/views/models
they exercise. Start only after slices 004, 004A, and 004B are approved.

Initial signatures include lifecycle `302`, removed `profession`, invalid
string profession choices, and setup errors that prevent API,
development-command, and performance assertions from running. Signal fixtures
and recovery behavior are owned and closed by reslice 004B; preserve them.

## Mandatory protocol

Record a per-module RED manifest before edits. Repair fixtures first and rerun
each module to expose real assertions. Follow the contract authority order from
`design.md`; do not change production behavior in this slice. Preserve
permission status codes and performance thresholds. Every listed module must
be green, the full suite must gain no unexplained failure ID, and the report is
mandatory. Stop after this slice.

## Objective

Make patient API, development utility, and performance tests reach and validate
their intended behavior using supported user/lifecycle setup.

## Requirements

- **R1:** eliminate obsolete user constructor fields and invalid profession
  values.
- **R2:** use navigation-ready users only where lifecycle is not under test.
- **R3:** preserve API `200/403/404`, command, and performance contracts.
- **R4:** no view, model, signal, command, or production permission changes.

## Expected files

- `apps/patients/tests/test_api_views.py`
- `apps/patients/tests/test_development_utils.py`
- `apps/patients/tests/test_performance.py`
- `apps/accounts/tests/factories.py` only with proven reusable need

Any production file or extra test module requires planner approval.

## TDD and inspection

Existing setup/redirect failures are RED. Fix setup minimally, then treat any
new business failure as a separate contract question.

```bash
rg -n "profession=|profession_type=.*doctor|create_user|NavigationReady|302" \
  apps/patients/tests/test_api_views.py \
  apps/patients/tests/test_development_utils.py \
  apps/patients/tests/test_performance.py
git diff --check
git diff --stat
```

## Verification commands

```bash
./scripts/test.sh apps.patients.tests.test_api_views
./scripts/test.sh apps.patients.tests.test_development_utils
./scripts/test.sh apps.patients.tests.test_performance
./scripts/test.sh apps.core.tests.test_lifecycle_guard_rail
docker exec eqmd_dev ruff check \
  apps/patients/tests/test_api_views.py \
  apps/patients/tests/test_development_utils.py \
  apps/patients/tests/test_performance.py
docker exec eqmd_dev python manage.py check
./scripts/test.sh
openspec validate restore-green-development-quality-gates --strict
markdownlint-cli2 \
  openspec/changes/restore-green-development-quality-gates/tasks.md \
  /tmp/restore-green-development-quality-gates-slice-005-report.md
```

## Binary criteria

- [ ] Three listed modules are fully green.
- [ ] Tests reach intended views/commands instead of lifecycle redirects.
- [ ] Permission and performance assertions remain strict.
- [ ] No production behavior changed.
- [ ] No new unexplained full-suite failure exists.

## Automatic `INCOMPLETE`

Any target failure, weakened assertion/threshold, production edit, lifecycle
allowlist abuse, unexpected file, new failure ID, missing report, real PII,
install, commit, or push.

## Required report

Create `/tmp/restore-green-development-quality-gates-slice-005-report.md` with
RED/GREEN per module, fixture evidence, contract checks, gate outputs, full
comparison, and verifier handoff.

## Ready-to-run implementer prompt

```text
Implement ONLY slice 005 after reading all required artifacts. Repair only
obsolete/lifecycle patient test fixtures in API, development-utils, and
performance modules; preserve permission, command, and threshold assertions.
Make every target green, compare the full suite, write the required
/tmp report, and STOP. Production edits or any unresolved gate are INCOMPLETE.
Do not install, commit, or push.
```
