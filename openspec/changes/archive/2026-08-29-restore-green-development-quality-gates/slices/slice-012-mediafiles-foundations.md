# Slice 012 - Mediafiles Model, Form, and Security Foundations

## Handoff for a zero-context implementer

Read standard artifacts and reports 001-011, mediafiles docs/specs, current
models/migrations/forms/validators, shared Hospital/Patient factories, and the
listed tests. Start only after medication cohorts are approved.

Initial failures are dominated by missing `Hospital` imports/fixtures, obsolete
`Patient.birth_date`, obsolete `Photo.media_file`, and old reverse-relation
names. This slice covers model/form/security foundations, not HTTP views or
performance/UAT.

## Mandatory protocol

Baseline each listed module and build a current field/relation map from models
and migrations. Existing setup failures are RED. Update stale fixtures rather
than adding compatibility aliases to production. Security assertions may not
be weakened. A proven production defect requires planner approval before
editing. All target modules must be green, full comparison, report, stop.

## Objective

Restore mediafiles foundational tests to supported Hospital, Patient, Photo,
series, validation, and security contracts.

## Requirements

- **R1:** centralize valid synthetic Hospital/Patient/media fixture setup.
- **R2:** use current model field and reverse-relation names.
- **R3:** preserve file validation, path, access, and sanitization assertions.
- **R4:** no storage migration, real file data, or compatibility field added.

## Expected files

- `apps/mediafiles/tests/test_models.py`
- `apps/mediafiles/tests/test_forms.py`
- `apps/mediafiles/tests/test_file_upload_fix.py`
- `apps/mediafiles/tests/test_security.py`
- `apps/mediafiles/tests/test_utils.py`
- `apps/mediafiles/tests/test_validators.py`
- one mediafiles test factory/helper if it replaces duplication

If more than six semantic files are necessary, stop for planner split.
Production media models/forms/validators are inspect-only without approval.

## TDD and inspections

```bash
rg -n "Hospital|birth_date|media_file|photoseriesfile_set|create_user" \
  apps/mediafiles/tests
rg -n "class (Photo|MediaFile|PhotoSeries)|related_name|ForeignKey|FileField" \
  apps/mediafiles/models.py apps/mediafiles/migrations
rg -n "Hospital|birthday" apps/core apps/patients/models.py
find apps/mediafiles/tests -maxdepth 2 -type f | sort
git diff --check
git diff --stat
```

## Verification commands

```bash
./scripts/test.sh apps.mediafiles.tests.test_models
./scripts/test.sh apps.mediafiles.tests.test_forms
./scripts/test.sh apps.mediafiles.tests.test_file_upload_fix
./scripts/test.sh apps.mediafiles.tests.test_security
./scripts/test.sh apps.mediafiles.tests.test_utils \
  apps.mediafiles.tests.test_validators
docker exec eqmd_dev ruff check <CHANGED_PYTHON_FILES>
docker exec eqmd_dev ruff format --check <CHANGED_PYTHON_FILES>
docker exec eqmd_dev python manage.py check
docker exec eqmd_dev python manage.py makemigrations --check --dry-run
./scripts/test.sh
openspec validate restore-green-development-quality-gates --strict
markdownlint-cli2 \
  openspec/changes/restore-green-development-quality-gates/tasks.md \
  /tmp/restore-green-development-quality-gates-slice-012-report.md
```

## Binary criteria

- [ ] Six listed foundational modules are green.
- [ ] Fixture field/relation map matches migrations/models.
- [ ] Security/validator assertions are not weakened.
- [ ] No production compatibility alias, migration, or real media data exists.
- [ ] No new unexplained full-suite failure exists.

## Automatic `INCOMPLETE`

Target red, more than six semantic files, production edit without approval,
weakened security assertion, migration, filesystem/destructive operation,
unexpected file, new failure, missing report, real PII/media, install, commit,
or push.

## Required report

Create `/tmp/restore-green-development-quality-gates-slice-012-report.md` with
field/relation map, RED/GREEN per module, fixture changes, security audit,
gates, full comparison, and verifier handoff.

## Ready-to-run implementer prompt

```text
Implement ONLY slice 012. Map current media model fields/relations, then repair
only stale foundational fixtures/tests; never add compatibility fields or
weaken security checks. Stop for planner split above six semantic files. Make
all listed modules green, run migration/full gates, write the required report,
and STOP. No real media/PII, install, commit, or push.
```
