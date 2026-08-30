<!-- markdownlint-disable MD013 -->

# Slice 018B - Core App Discovery and Cohort Repair

## Handoff for a zero-context implementer

Read standard artifacts, approved reports 001-018, and especially slice 016
report section "Baseline and ownership" (apps/core namespace-package note)
and slice 018 report section 4.1. Start only after slice 018A approval.

`apps/core` has no `__init__.py`, so it is a namespace package: the full
suite NEVER discovers its tests and `./scripts/test.sh apps.core` crashes
(`TypeError` in unittest discovery). Its tests only run via deep explicit
labels. Verifier-measured explicit baseline (2026-08-29):

| Module                                                                 | Result                                                                                       |
| ---------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| test_management_commands                                               | Ran 7, FAILED (failures=2)                                                                   |
| test_medical_procedures                                                | Ran 30, FAILED (failures=11, errors=3)                                                       |
| test_new_permissions                                                   | Ran 15, FAILED (failures=5)                                                                  |
| test_soft_delete_admin                                                 | Ran 17, FAILED (failures=6)                                                                  |
| test_soft_delete_history_integration                                   | Ran 12, FAILED (errors=1)                                                                    |
| test_templates                                                         | Ran 27, FAILED (failures=10)                                                                 |
| test_views                                                             | Ran 31, FAILED (failures=18, errors=1)                                                       |
| test_hospital_membership                                               | import crash: pytest module-level `skip(allow_module_level=True)` aborts the unittest runner |
| remaining 13 modules (incl. soft_delete_edge_cases, urls, markdown ×4) | green (~181 tests)                                                                           |

## Mandatory protocol

Baseline every module explicitly (table above is the expected starting RED;
re-verify). Existing failures are RED. Test-only changes require proof of
stale setup/expectation; production changes require behavior RED, current
spec proof, and rollback. Never weaken soft-delete retention, audit, or
permission contracts (slice 016 restored the canonical
`Event.all_objects` semantics — core tests asserting the broken manager are
stale). The full suite count WILL increase when `apps/core/__init__.py` is
added; the final full suite must exit 0. Do not touch apps outside
`apps/core` except imports already established. Stop above nine semantic
files without reslicing.

## Objective

Make `apps/core` a discovered, fully green app inside the full suite.

## Requirements

- **R1:** add `apps/core/__init__.py` (minimal, matching sibling apps'
  convention) so `./scripts/test.sh apps.core` and full-suite discovery
  work; no other production file changes without RED/spec proof.
- **R2:** repair the seven red modules per stale-contract/stale-fixture
  analysis (lifecycle-ready users where middleware 302s interfere —
  `NavigationReadyUserFactory`; restored `all_objects` semantics; current
  template/URL/permission contracts).
- **R3:** convert `test_hospital_membership` to a unittest-compatible skip
  (e.g. `unittest.skip` decorator preserving the deprecation intent) or
  planner-approved removal of the dead module; no silent unskip.
- **R4:** convert the 46 `apps/core` guard-rail violations
  (`/tmp/guardrail_violations_018.txt` lines under `apps/core/`) to
  lifecycle-ready factories or the two explicit flags — except modules that
  genuinely test lifecycle middleware (guard-rail allowlist already covers
  the middleware modules; any additional exemption requires planner
  approval in the report).
- **R5:** full suite exits 0 with the new larger count and unchanged skip
  semantics (document the new total; skip increases require approval).

## Expected files

- `apps/core/__init__.py` (new)
- `apps/core/tests/test_management_commands.py`
- `apps/core/tests/test_medical_procedures.py`
- `apps/core/tests/test_new_permissions.py`
- `apps/core/tests/test_soft_delete_admin.py`
- `apps/core/tests/test_soft_delete_history_integration.py`
- `apps/core/tests/test_templates.py`
- `apps/core/tests/test_views.py`
- `apps/core/tests/test_hospital_membership.py`

Corresponding `apps/core` production files require RED/spec proof and
rollback. Green core modules may receive only fixture conversions for R4.

## TDD and inspections

```bash
ls apps/core/__init__.py
./scripts/test.sh apps.core   # crashes before R1 — record the TypeError
for m in apps.core.tests.test_*; do ./scripts/test.sh $m; done
rg -n "all_objects|create_user|NavigationReady|password_change_required" \
  apps/core/tests | head -120
rg -n '^(FAIL|ERROR): ' <full-suite log>   # must be empty
```

## Verification commands

```bash
./scripts/test.sh apps.core                # OK, exit 0, discovered
./scripts/test.sh apps.core.tests.test_lifecycle_guard_rail  # 8 OK, scan count drops by ~46
docker exec eqmd_dev ruff check apps/core
docker exec eqmd_dev ruff format --check apps/core
docker exec eqmd_dev python manage.py check
docker exec eqmd_dev python manage.py makemigrations --check --dry-run
./scripts/test.sh                           # exit 0; new count documented; 0 headers
openspec validate restore-green-development-quality-gates --strict
markdownlint-cli2 \
  openspec/changes/restore-green-development-quality-gates/slices/slice-018b-core-discovery-and-cohort.md \
  /tmp/restore-green-development-quality-gates-slice-018b-report.md
```

## Binary criteria

- [ ] `./scripts/test.sh apps.core` exits 0 and the app appears in the full
      suite discovery.
- [ ] All core modules green; hospital-membership intent preserved.
- [ ] Full suite exits 0 with zero headers; count increase documented.
- [ ] Guard-rail scan decreases by the core cohort (~46) with no new
      violations anywhere.
- [ ] No migration, no behavior-weakening change, no app outside `apps/core`
      touched.

## Automatic `INCOMPLETE`

Any red core module after repair, full-suite failure, new violation, count
or skip change without documentation, migration, excessive files, missing
report, PII, install, commit, or push.

## Required report

Create `/tmp/restore-green-development-quality-gates-slice-018b-report.md`
with the per-module RED/GREEN table, discovery proof, new full-suite count,
guard-rail delta, production fixes (if any) with rollback, scope audit, and
verifier handoff.

## Ready-to-run implementer prompt

```text
Implement ONLY slice 018B after 018A approval. Make apps/core discovered
(add __init__.py) and repair its seven red modules plus the broken
hospital-membership skip per current contracts; convert core's 46 guard-rail
violations. Full suite must exit 0 with the documented larger count. Write
the report and STOP. No install, commit, or push.
```
