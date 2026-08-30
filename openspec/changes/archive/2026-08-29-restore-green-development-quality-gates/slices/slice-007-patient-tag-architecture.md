# Slice 007 - Patient Tag Architecture and Integration Contracts

## Handoff for a zero-context implementer

Read all standard artifacts and reports 001-006A, then completely inspect the
current `AllowedTag`, `Tag`, patient relation, migrations, forms, views, docs,
and listed tests. Do not assume legacy `patient.tags` or integer tag IDs remain
valid. Start only after slice 006 and reslice 006A approval.

Initial signatures include missing `Patient.tags`, null `Tag.patient_id`,
non-UUID IDs, and cascade expectations that may describe a superseded tag
architecture.

## Mandatory protocol

Create a contract table from current migrations/models/specs before editing.
Run target tests for RED. Update stale tests only when the table proves the
current architecture. If the implementation violates an authoritative
contract, stop and request a smaller production-fix slice rather than changing
models here. Make target modules green, compare full suite, report, stop.

## Objective

Align tag model/form/integration tests with the authoritative current
patient-tag architecture without changing schema or production behavior.

## Requirements

- **R1:** document ownership, relation names, UUID types, and deletion/cascade
  semantics from authoritative sources.
- **R2:** replace superseded direct `patient.tags` or orphan `Tag` setup with
  supported relations/factories.
- **R3:** preserve duplicate prevention, assignment, deletion, and integration
  assertions applicable to the current architecture.
- **R4:** no model or migration edit.

## Expected files

- `apps/patients/tests/test_tag_architecture_refactor.py`
- `apps/patients/tests/test_integration.py`
- `apps/patients/tests/test_forms.py` only for tag-specific stale setup
- one shared tag test factory/helper only if it reduces proven duplication

Inspect-only: patient models, migrations, forms, URLs, and tag views.

## TDD and inspections

```bash
rg -n "class (AllowedTag|Tag)|patient_tags|\.tags|patient_id|on_delete" \
  apps/patients/models.py apps/patients/migrations \
  apps/patients/tests/test_tag_architecture_refactor.py \
  apps/patients/tests/test_integration.py apps/patients/tests/test_forms.py
rg -n "Tag|AllowedTag|patient_tags" docs/apps/patients.md openspec/specs 2>/dev/null
git diff --check
git diff --stat
```

## Verification commands

```bash
./scripts/test.sh apps.patients.tests.test_tag_architecture_refactor
./scripts/test.sh apps.patients.tests.test_integration
./scripts/test.sh apps.patients.tests.test_forms
docker exec eqmd_dev ruff check \
  apps/patients/tests/test_tag_architecture_refactor.py \
  apps/patients/tests/test_integration.py \
  apps/patients/tests/test_forms.py
docker exec eqmd_dev python manage.py check
docker exec eqmd_dev python manage.py makemigrations patients --check --dry-run
./scripts/test.sh
openspec validate restore-green-development-quality-gates --strict
markdownlint-cli2 \
  openspec/changes/restore-green-development-quality-gates/tasks.md \
  /tmp/restore-green-development-quality-gates-slice-007-report.md
```

## Binary criteria

- [ ] Contract table cites migrations/models/specs.
- [ ] Three target modules are green.
- [ ] No schema/model/production edit exists.
- [ ] Relevant assignment/deletion assertions remain strict.
- [ ] Full suite has no new unexplained failure ID.

## Automatic `INCOMPLETE`

Ambiguous authority, model/migration edit, removed assertion without evidence,
target failure, unexpected file, migration drift, new full-suite failure,
missing report, PII, install, commit, or push.

## Required report

Create `/tmp/restore-green-development-quality-gates-slice-007-report.md` with
the contract table, RED/GREEN evidence, stale-assumption mapping, gates,
full-suite comparison, and verifier handoff.

## Ready-to-run implementer prompt

```text
Implement ONLY slice 007. Build an authoritative tag contract table first,
then update only stale tag architecture/integration/form tests. Do not edit
models, migrations, URLs, or production behavior. Make all targets green, run
migration and full comparisons, create the required report, and STOP. Any
contract ambiguity or failed gate is INCOMPLETE.
```
