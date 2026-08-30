# Slice 006 - Patient Tag HTTP Contracts

## Handoff for a zero-context implementer

Read standard project/change artifacts, reports 001-005A, current patient tag
models/URLs/views, the tag architecture documentation/specs, and the three
listed test modules. Start only after slice 005 and reslice 005A approval.

Initial failures include lifecycle `302`, non-UUID tag IDs passed to UUID
routes, and expectations that requests return `400/403/404/500` before the
view is reached. This slice covers HTTP/error contracts, not relation-model
architecture.

## Mandatory protocol

Baseline each module and classify every failure as lifecycle setup, stale URL
fixture, or real HTTP defect. Existing failures are RED. Update tests only when
current URL/spec authority proves them stale. If a production HTTP defect is
proved, stop and request planner approval for the exact production file before
editing. Targets must become fully green; run full comparison, report, stop.

## Objective

Restore meaningful tag endpoint and error-handling tests so requests reach the
current UUID routes and validate permission and response contracts.

## Requirements

- **R1:** use navigation-ready users except tests intentionally covering
  lifecycle.
- **R2:** construct valid UUID route parameters when testing application errors;
  test malformed paths separately at resolver boundaries.
- **R3:** preserve strict expected status/error payload contracts.
- **R4:** do not accept `500` as a generic success criterion where a domain
  `400/404` contract is authoritative.

## Expected files

- `apps/patients/tests/test_tag_error_handling.py`
- `apps/patients/tests/test_tag_management_basic_error_handling.py`
- `apps/patients/tests/test_tag_management_error_handling.py`

`apps/patients/urls.py` and tag views are inspect-only. Any production defect
requires `INCOMPLETE` plus a planner-approved follow-up.

## TDD and inspections

```bash
rg -n "create_user|status_code|reverse\(|tag_id|patient_tag_(add|remove)" \
  apps/patients/tests/test_tag_error_handling.py \
  apps/patients/tests/test_tag_management_basic_error_handling.py \
  apps/patients/tests/test_tag_management_error_handling.py
rg -n "patient_tag_(add|remove)|<uuid:" \
  apps/patients/urls.py apps/patients/views.py
git diff --check
git diff --stat
```

## Verification commands

```bash
./scripts/test.sh apps.patients.tests.test_tag_error_handling
./scripts/test.sh apps.patients.tests.test_tag_management_basic_error_handling
./scripts/test.sh apps.patients.tests.test_tag_management_error_handling
./scripts/test.sh apps.core.tests.test_lifecycle_guard_rail
docker exec eqmd_dev ruff check \
  apps/patients/tests/test_tag_error_handling.py \
  apps/patients/tests/test_tag_management_basic_error_handling.py \
  apps/patients/tests/test_tag_management_error_handling.py
docker exec eqmd_dev python manage.py check
./scripts/test.sh
openspec validate restore-green-development-quality-gates --strict
markdownlint-cli2 \
  openspec/changes/restore-green-development-quality-gates/tasks.md \
  /tmp/restore-green-development-quality-gates-slice-006-report.md
```

## Binary criteria

- [ ] All three modules exit 0.
- [ ] Requests intended for views are not intercepted by lifecycle.
- [ ] UUID fixtures match current route converters.
- [ ] Permission/error assertions remain strict and specific.
- [ ] No production edit or new full-suite failure exists.

## Automatic `INCOMPLETE`

Unresolved target, production edit without approval, permissive multi-status or
`500` assertion without contract evidence, lifecycle allowlist abuse,
unexpected file, new failure, missing report, PII, install, commit, or push.

## Required report

Create `/tmp/restore-green-development-quality-gates-slice-006-report.md` with
failure classification, route authority, before/after fixtures, all gates,
full-suite comparison, and verifier handoff.

## Ready-to-run implementer prompt

```text
Implement ONLY slice 006. Restore the three patient tag HTTP/error test modules
using lifecycle-ready users and current UUID route contracts. Do not weaken
status/payload assertions and do not edit production URLs/views without a new
planner-approved slice. Make targets green, run full comparison, write the
required report, then STOP. Any ambiguity or failed gate is INCOMPLETE.
```
