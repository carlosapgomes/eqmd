# Slice 016 - Events and History-and-Physicals Cohorts

## Handoff for a zero-context implementer

Read standard artifacts and reports 001-015, canonical event soft-delete and
history-and-physical specs, current event/history models/forms/permissions, and
listed tests. Start only after PDF forms is approved green.

Initial residuals include events soft-delete manager/bulk behavior,
history-event patient requirements, and permission/lifecycle fixture drift.
These are clinical/audit contracts and must not be guessed.

## Mandatory protocol

Baseline both app suites and build a scenario authority matrix. Existing
failures are RED. Test-only changes require proof of stale setup/expectation.
Production changes require behavior RED, current-spec proof, and rollback. Never
relax soft-delete retention, event audit, required patient linkage, 24-hour
rules, or permissions. Stop above six semantic files. Both apps green, full
comparison, report, stop.

## Objective

Restore events soft-delete and history-and-physicals contracts while preserving
clinical retention, linkage, and access control.

## Requirements

- **R1:** event soft delete preserves retained rows, managers, history, and
  documented bulk semantics.
- **R2:** history events satisfy current patient and audit-field requirements.
- **R3:** permission tests reach intended checks without lifecycle interception.
- **R4:** both complete app suites exit 0.

## Expected files

- `apps/events/tests/test_soft_delete.py`
- `apps/historyandphysicals/tests/test_models_forms.py`
- `apps/historyandphysicals/tests/test_permissions.py`
- `apps/historyandphysicals/tests/test_integration.py`

Corresponding production files require RED/spec proof and planner approval. No
migration, schema, or more than six semantic files without reslicing.

## TDD and inspections

```bash
rg -n "soft.delete|hard_delete|all_objects|bulk|patient|Permission|24" \
  apps/events/tests/test_soft_delete.py \
  apps/historyandphysicals/tests
rg -n "all_objects|hard_delete|SoftDelete|patient_id|permission" \
  apps/events apps/historyandphysicals apps/core/models \
  openspec/specs 2>/dev/null | head -240
git diff --check
git diff --stat
```

## Verification commands

```bash
./scripts/test.sh apps.events
./scripts/test.sh apps.historyandphysicals
./scripts/test.sh apps.core.tests.test_lifecycle_guard_rail
docker exec eqmd_dev ruff check <CHANGED_PYTHON_FILES>
docker exec eqmd_dev ruff format --check <CHANGED_PYTHON_FILES>
./scripts/typecheck.sh <CHANGED_PRODUCTION_PYTHON_FILES>
docker exec eqmd_dev python manage.py check
docker exec eqmd_dev python manage.py makemigrations --check --dry-run
./scripts/test.sh
openspec validate restore-green-development-quality-gates --strict
markdownlint-cli2 \
  openspec/changes/restore-green-development-quality-gates/tasks.md \
  /tmp/restore-green-development-quality-gates-slice-016-report.md
```

## Binary criteria

- [ ] Both complete app suites exit 0.
- [ ] Retention, audit, linkage, 24-hour, and permission rules remain strict.
- [ ] Any production fix has RED/spec proof and rollback.
- [ ] No more than six semantic files change without reslicing.
- [ ] No migration or new unexplained full-suite failure exists.

## Automatic `INCOMPLETE`

Either app red, weakened clinical/audit contract, ambiguous authority,
production edit without proof, excessive files, migration, new failure,
missing report, PII, install, commit, or push.

## Required report

Create `/tmp/restore-green-development-quality-gates-slice-016-report.md` with
scenario authority matrix, per-app RED/GREEN, production rollback if any, all
gates, full-suite comparison, and verifier handoff.

## Ready-to-run implementer prompt

```text
Implement ONLY slice 016. Restore events and historyandphysicals against
canonical clinical/audit contracts. Never weaken soft-delete retention,
required patient linkage, 24-hour rules, or permissions. Stop above six
semantic files, make both apps green, run all gates/full comparison, write the
report, and STOP. No install, commit, or push.
```
