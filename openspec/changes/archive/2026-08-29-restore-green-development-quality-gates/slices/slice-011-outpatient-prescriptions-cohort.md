# Slice 011 - Outpatient Prescriptions Cohort

## Handoff for a zero-context implementer

Read standard project/change artifacts and reports 001-010, active prescription
and drug-selection specs/changes, current outpatient models/forms/views, and
all outpatient-prescription tests. Start only after drugtemplates is approved
green.

Initial failures include missing Hospital/user fixtures, obsolete profession
arguments, lifecycle redirects, form/model contract drift, and permission/view
setup that does not reach intended behavior.

## Mandatory protocol

Baseline the entire app and map each failure to current specs/models. Existing
failures are RED. Reuse the now-green drug-template and navigation-ready
fixtures; do not duplicate them. Production changes require behavior RED and
current-spec proof. Stop above six semantic files. Whole app green, full
comparison, report, stop.

## Objective

Restore outpatient-prescription model, form, search, permission, view, and
integration tests without implementing pending prescription UX work.

## Requirements

- **R1:** use supported Hospital, user, profession, and lifecycle fixtures.
- **R2:** preserve model/form validation and drug-search semantics.
- **R3:** permission tests reach intended `200/403/404` paths.
- **R4:** integration tests use current drug-template contracts.
- **R5:** complete app suite exits 0 and active UX changes remain untouched.

## Expected files

- `apps/outpatientprescriptions/tests/test_models.py`
- `apps/outpatientprescriptions/tests/test_forms.py`
- `apps/outpatientprescriptions/tests/test_drug_template_search.py`
- `apps/outpatientprescriptions/tests/test_permissions.py`
- `apps/outpatientprescriptions/tests/test_views.py`
- `apps/outpatientprescriptions/tests/test_integration.py`
- one existing shared factory only with proven reusable need

Production files are inspect-only without RED/spec proof and planner approval.
Stop for reslicing above six semantic files. No migrations or dependencies.

## TDD and inspections

```bash
rg -n "profession=|Hospital|create_user|status_code|autocomplete|permission" \
  apps/outpatientprescriptions/tests
rg -n "Requirement:|autocomplete|drug|permission|prescription" \
  openspec/changes/*prescription* openspec/specs \
  apps/outpatientprescriptions 2>/dev/null | head -240
git diff --check
git diff --stat
```

## Verification commands

```bash
./scripts/test.sh apps.outpatientprescriptions
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
  /tmp/restore-green-development-quality-gates-slice-011-report.md
```

## Binary criteria

- [ ] Entire outpatientprescriptions app exits 0.
- [ ] Search, validation, permission, and integration assertions remain strict.
- [ ] Active prescription UX work remains untouched.
- [ ] No more than six semantic files change without reslicing.
- [ ] No migration or new unexplained full-suite failure exists.

## Automatic `INCOMPLETE`

App red, lifecycle interception, weakened permission/validation, active feature
early implemented, excessive files, migration, new failure, missing report,
PII, install, commit, or push.

## Required report

Create `/tmp/restore-green-development-quality-gates-slice-011-report.md` with
failure/authority map, RED/GREEN, fixture reuse proof, all gates, full-suite
comparison, rollback, and verifier handoff.

## Ready-to-run implementer prompt

```text
Implement ONLY slice 011 after drugtemplates is green. Restore the complete
outpatientprescriptions suite using supported shared fixtures and current
contracts; do not implement pending UX work. Stop above six semantic files,
make the app fully green, run all gates/full comparison, write the report, and
STOP. No install, commit, or push.
```
