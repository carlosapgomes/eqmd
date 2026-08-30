# Slice 004A - Repair Record-Number Create Validation

## Handoff for a zero-context implementer

Read completely, in order: `AGENTS.md`, `PROJECT_CONTEXT.md`, the canonical
workflow documents, ADR-0001, every artifact of this change, approved reports
001-003, slice 004, its report, this reslice, and the current diffs in the
three slice-004 test modules. Implement only this reslice and stop.

Required prior evidence:

- slice 004 is `INCOMPLETE` with 40 of 41 target errors removed;
- `test_history` is 13/13 green;
- `test_record_tracking_models` is 18/18 green;
- `test_record_tracking_views` is 9/10 with one production error;
- a record-number create POST raises `RelatedObjectDoesNotExist` because
  `PatientRecordNumber.clean()` dereferences `self.patient` while the excluded
  ModelForm relation has no `patient_id` yet;
- `PatientRecordNumberCreateView.form_valid()` intentionally delegates the
  actual replacement to `Patient.update_current_record_number()`;
- assigning `self.instance.patient` in the form constructor is not approved:
  it would make model validation reject a legitimate replacement whenever the
  patient already has a current record.

The approved minimal contract is that model-level current-record uniqueness is
checked only when `patient_id` is present. Required-field validation, database
constraints, signals, and the managed replacement method remain unchanged.

## Mandatory DeepSeek4-Flash protocol

1. Record `BASE_REF`, ownership status, the exact remaining traceback, target
   module counts, and full-suite failure manifest before editing.
2. Preserve every slice-004 fixture/assertion repair and all unrelated work.
3. Add the existing-current replacement view regression before production
   code. Prove both create scenarios fail for the expected missing-patient
   dereference before GREEN.
4. Make the one-condition model fix described below. Do not edit forms, views,
   signals, migrations, templates, URLs, or services.
5. Run every target module and full comparison. Any target failure means
   `INCOMPLETE`.
6. Write the exact report, reply with `REPORT_PATH` and `STATUS`, and stop.
   Do not start slice 005, mark tasks, commit, or push.

## Objective

Close slice 004 by making the supported record-number create view validate
partial ModelForm instances safely while preserving managed lifelong record
history and replacement behavior.

## Requirements

- **R1:** `PatientRecordNumber.clean()` never dereferences `patient` when
  `patient_id` is absent during excluded-field ModelForm validation.
- **R2:** when `patient_id` is present, the existing current-record validation
  remains byte-for-byte equivalent and still rejects an actual duplicate
  current assignment.
- **R3:** the create view creates a patient's first record number without HTTP
  500 and updates the denormalized current number.
- **R4:** the same view can replace an existing current number through
  `update_current_record_number()`: old record inactive, new record current,
  `previous_record_number` retained, and patient denormalization updated.
- **R5:** all three slice-004 modules and the existing business/signal
  regressions finish green with no new full-suite failure ID.

## Expected files

- `apps/patients/models.py`
- `apps/patients/tests/test_record_tracking_views.py`

Do not edit `apps/patients/forms.py`, views, signals, templates, URLs,
migrations, services, other tests, dependency metadata, scripts, CI, or
OpenSpec tasks. Do not fix the create/edit titles or duplicate discharge route
here; those are separate workflow debts assigned to a later focused slice.

## TDD: RED -> GREEN -> REFACTOR

### RED

First rerun the existing unchanged test:

```bash
./scripts/test.sh \
  apps.patients.tests.test_record_tracking_views.RecordNumberViewTests.test_record_number_create_view
```

It must error only with `PatientRecordNumber.patient.RelatedObjectDoesNotExist`
from `PatientRecordNumber.clean()`.

Then add one regression in the same test class for replacing an existing
current record through `record_number_create`. It must:

1. create current record `REC001` using the supported patient method;
2. POST `REC002` and a synthetic reason/effective date to the create view;
3. fail before GREEN with the same missing-patient dereference;
4. after GREEN, assert redirect, exactly one current record, old record
   inactive, new record current, `previous_record_number == "REC001"`, and
   `patient.current_record_number == "REC002"`.

Do not catch the exception, weaken client exception behavior, or change the
existing first-create assertions merely to obtain RED.

### GREEN

Change only the current-record uniqueness condition in
`PatientRecordNumber.clean()` from unconditional patient dereference to the
approved relation-presence guard:

```python
if self.is_current and self.patient_id:
```

Keep the query, exclusion, error key/message, database constraint, signals, and
all other model behavior unchanged. Do not assign the patient in the form
constructor and do not bypass model `full_clean()`.

### REFACTOR

No refactor is expected. If more than the one condition and one regression test
need semantic changes, stop `INCOMPLETE` and return to the planner.

## Mandatory inspections

```bash
rg -n 'def clean|self.is_current|patient_id|existing_current' \
  apps/patients/models.py
rg -n 'test_record_number_create_view|REC001|REC002|previous_record_number' \
  apps/patients/tests/test_record_tracking_views.py
git diff --word-diff=porcelain -- apps/patients/models.py
git diff --check
git diff --stat
```

The report must show the exact production token diff and prove that no model
field, constraint, signal, migration state, or unrelated assertion changed.

## Static and migration verification

`apps/patients/models.py` has documented pre-existing full-file Ruff/Mypy debt.
Do not format it, add ignores, or repair unrelated findings. Run the critical
syntax/name subset plus full Ruff on the changed test:

```bash
docker exec eqmd_dev ruff check --isolated \
  --select E9,F63,F7,F82 apps/patients/models.py
docker exec eqmd_dev ruff check \
  apps/patients/tests/test_record_tracking_views.py
docker exec eqmd_dev python -m compileall -q apps/patients/models.py
docker exec eqmd_dev python manage.py check
docker exec eqmd_dev python manage.py makemigrations --check --dry-run
```

Every command must exit 0 and no migration file may appear.

## Functional verification

```bash
./scripts/test.sh apps.patients.tests.test_history
./scripts/test.sh apps.patients.tests.test_record_tracking_models
./scripts/test.sh apps.patients.tests.test_record_tracking_views
./scripts/test.sh apps.patients.tests.test_business_logic
./scripts/test.sh apps.patients.tests.test_signals
./scripts/test.sh apps.core.tests.test_lifecycle_guard_rail
```

Required minimum outcomes:

- history: 13/13;
- record-tracking models: 18/18;
- record-tracking views: all tests green, including the new replacement test;
- business logic, signals, and lifecycle guard rail: zero failures/errors.

## Full comparison and artifact gates

```bash
./scripts/test.sh
openspec validate restore-green-development-quality-gates --strict
markdownlint-cli2 \
  openspec/changes/restore-green-development-quality-gates/tasks.md \
  /tmp/restore-green-development-quality-gates-slice-004a-report.md
git diff --check
git status --short
```

Compare the new full-suite FAIL/ERROR headers against
`/tmp/full_suite_004.log` using identical extraction. Account explicitly for
one newly added passing test and removal of the prior create-view error. No new
or changed unexplained failure header is allowed.

## Binary acceptance criteria

- [ ] Both first-create and existing-current replacement scenarios are RED for
      the exact pre-fix dereference.
- [ ] Production diff is exactly the `patient_id` presence guard.
- [ ] Validation remains active whenever `patient_id` exists.
- [ ] First create redirects and persists the current record/denormalization.
- [ ] Replacement preserves old/new current flags and previous-number history.
- [ ] All three slice-004 target modules exit 0.
- [ ] Business logic, signals, lifecycle, syntax, Django, and migration gates
      exit 0.
- [ ] Full suite has no new unexplained failure header.
- [ ] No forms/views/templates/routes/signals/migrations/constraints or
      unrelated assertions change.
- [ ] No package install, data mutation outside test databases, PII, commit, or
      push occurs.
- [ ] Tasks 4.1-4.5 and 4A.1-4A.5 remain unchecked for planner closure.

## Automatic `INCOMPLETE`

Report `INCOMPLETE` and stop if assigning the patient in the form is required;
an existing-current replacement is blocked; any target module remains red;
the production diff exceeds the one condition; an unexpected file changes;
migration drift appears; full-suite failures are added; or any install,
restored-data mutation, PII, commit, or push occurs.

## Required report

Create `/tmp/restore-green-development-quality-gates-slice-004a-report.md` with
status, RED tracebacks for both scenarios, requirement matrix, exact token diff,
first-create/replacement evidence, target/static/migration/full-suite results,
scope audit, rollback, and third-LLM verifier handoff.

## Ready-to-run implementer prompt

```text
Read every prerequisite in slice-004a-record-number-create-validation.md.
Implement ONLY reslice 004A with strict TDD. Preserve all slice-004 repairs.
Add the existing-current replacement view regression first, reproduce the same
missing-patient RED in both create scenarios, then change only the
PatientRecordNumber.clean condition to require self.patient_id before current
record uniqueness lookup. Never assign patient in the form constructor or edit
forms/views/templates/routes/signals/migrations. Make all three slice-004
modules plus business/signals/lifecycle green, run static/migration/full gates,
write /tmp/restore-green-development-quality-gates-slice-004a-report.md, reply
REPORT_PATH and STATUS, then STOP before slice 005. No install, commit, or push.
```
