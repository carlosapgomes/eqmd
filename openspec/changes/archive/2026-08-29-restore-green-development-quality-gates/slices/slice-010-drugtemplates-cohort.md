# Slice 010 - Drug Templates Cohort

## Handoff for a zero-context implementer

Read standard project/change artifacts and reports 001-009, every active
OpenSpec change/spec for `drugtemplates`, current migrations/models/forms, and
all drug-template tests. Start only after the patients app is approved green.

Initial failures include missing `Hospital`, obsolete user fields, lifecycle
`302`, attempts to set computed/read-only `DrugTemplate.presentation`, and
form/source/import drift. Active drug-template changes must not be implemented
or contradicted by this stabilization slice.

## Mandatory protocol

Baseline `apps.drugtemplates` and group exact failures by setup, stale contract,
or production defect. Build an active-spec contract map before edits. Existing
failures are RED. Prefer fixtures/test repair; production edits require
behavior RED plus explicit current-spec proof. Stop for planner split above six
semantic files. The whole app must become green, full comparison, report, stop.

## Objective

Restore the complete drug-template test suite without advancing pending search,
refactor, or UX changes.

## Requirements

- **R1:** repair supported Hospital, profession, and lifecycle fixtures.
- **R2:** respect current computed/read-only properties and source contracts.
- **R3:** preserve validation, access control, admin, view, and import assertions.
- **R4:** `./scripts/test.sh apps.drugtemplates` exits 0.
- **R5:** active drug-template change files and future behavior remain untouched.

## Expected files

- `apps/drugtemplates/tests/test_models_forms.py`
- `apps/drugtemplates/tests/test_form_validation.py`
- `apps/drugtemplates/tests/test_source_tracking.py`
- `apps/drugtemplates/tests/test_views.py`
- `apps/drugtemplates/tests/test_admin_interface.py`
- `apps/drugtemplates/tests/test_access_control.py`
- `apps/drugtemplates/tests/test_medication_import.py`
- one shared factory only if it replaces duplicated setup

Stop for reslicing if files beyond the expected list above need semantic edits (the
list itself contains seven files). Production files
are inspect-only without RED/current-spec proof and planner approval.

## TDD and inspections

```bash
rg -n "profession=|Hospital|presentation=|create_user|status_code" \
  apps/drugtemplates/tests
rg -n "presentation|source|permission|import|Requirement:" \
  apps/drugtemplates openspec/changes/*drug* openspec/specs 2>/dev/null \
  | head -240
git diff --check
git diff --stat
```

## Verification commands

```bash
./scripts/test.sh apps.drugtemplates
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
  /tmp/restore-green-development-quality-gates-slice-010-report.md
```

Replace placeholders with changed paths; typecheck is not applicable only when
no production Python changed.

## Binary criteria

- [ ] Entire drugtemplates app exits 0.
- [ ] Active drug-template changes remain untouched.
- [ ] Access, validation, source, and import assertions remain strict.
- [ ] No more than six semantic files change without reslicing.
- [ ] No migration or new unexplained full-suite failure exists.

## Automatic `INCOMPLETE`

App red, active feature implemented early, ambiguous contract, excessive files,
weakened assertion, migration, unexpected dependency, new failure, missing
report, PII, install, commit, or push.

## Required report

Create `/tmp/restore-green-development-quality-gates-slice-010-report.md` with
RED/GREEN manifest, active-spec audit, test-vs-production decisions, all gates,
full-suite comparison, rollback, and verifier handoff.

## Ready-to-run implementer prompt

```text
Implement ONLY slice 010 after patients is green. Restore apps.drugtemplates
contract-first without implementing active drug-template features. Stop and ask
for reslicing above six semantic files. Require the whole app green, run
static/migration/full gates, write the exact /tmp report, and STOP. No install,
commit, or push.
```
