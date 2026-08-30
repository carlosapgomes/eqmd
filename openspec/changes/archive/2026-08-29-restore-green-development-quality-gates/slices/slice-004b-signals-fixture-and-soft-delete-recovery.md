# Slice 004B - Repair Signal Fixture and Soft-Delete Recovery

## Handoff for a zero-context implementer

Read completely, in order: `AGENTS.md`, `PROJECT_CONTEXT.md`, the canonical
workflow documents, ADR-0001, every artifact of this change, approved reports
001-003, slices 004 and 004A, both reports, the third-LLM rejection of 004A,
and this reslice. Implement only 004B and stop.

Preserve the accepted partial 004A implementation:

- `PatientRecordNumber.clean()` guards its current-record lookup with
  `self.patient_id`;
- the record-number replacement view regression remains unchanged;
- the three original slice-004 modules are green;
- `/tmp/full_suite_004a.log` is the comparison baseline: 2,030 tests, 157
  failures, 375 errors, 12 skips, and 532 FAIL/ERROR headers.

004A remains formally `INCOMPLETE` because its mandatory signals module has ten
setup errors and its run mutated the development database. This reslice must
use Django test databases only. Deleting synthetic rows afterward is not an
acceptable substitute.

Planner preflight established a two-stage RED:

1. all ten signal tests error in `setUp` because removed `profession=` is passed
   to `EqmdCustomUser`;
2. after substituting the supported lifecycle-ready fixture in memory, nine
   tests pass and `test_signal_error_handling` errors with the unique
   `record_change_id` constraint: the test soft-deletes its timeline event, the
   active-only manager cannot find it, and the post-save signal tries to insert
   another child row rather than restore the existing soft-deleted row.

The authoritative behavior is one timeline event per record-number change.
Updating the source record restores and refreshes its soft-deleted timeline
event; it never creates a second row or raises `IntegrityError`.

## Mandatory DeepSeek4-Flash protocol

1. Record `BASE_REF`, ownership, checksums/diff of accepted 004A files, the ten
   setup-error headers, and the 004A full-suite manifest before editing.
2. Fix only the signal test fixture and rerun the module. Capture the expected
   9/10 intermediate RED and exact unique-constraint traceback before editing
   production.
3. Strengthen the existing error-handling test to require restoration of the
   same event row, then make the minimal signal fix.
4. Run all mandatory gates. Any target failure or any database access outside
   a Django-managed test database is `INCOMPLETE`.
5. Write the exact report, reply with `REPORT_PATH` and `STATUS`, and stop.
   Do not start slice 005, mark tasks, commit, or push.

## Objective

Close slices 004/004A by making the signal cohort use supported user fixtures
and by restoring a soft-deleted record-number timeline event safely when its
source record changes.

## Requirements

- **R1:** `SignalTests.setUp()` uses the shared supported lifecycle-ready user
  helper and `profession_type=User.MEDICAL_DOCTOR`; removed fields are absent.
- **R2:** all ten signal tests reach their signal assertions rather than fail in
  user construction.
- **R3:** `create_record_change_event()` searches active and soft-deleted
  `RecordNumberChangeEvent` rows for the source `record_change`.
- **R4:** an existing soft-deleted event is restored in place: same primary key,
  `is_deleted=False`, deletion metadata cleared, synchronized event fields,
  and exactly one all-states row.
- **R5:** active existing and first-created events preserve current behavior;
  no model, schema, constraint, lifecycle helper, or unrelated signal changes.
- **R6:** all 004/004A target and supporting modules are green, and the full
  suite gains no unexplained failure header.

## Expected files

- `apps/patients/tests/test_signals.py`
- `apps/patients/signals.py`

No other source/test file may change. In particular, do not edit models,
forms, views, templates, URLs, event models/managers, migrations, shared
helpers, dependency metadata, scripts, CI, or OpenSpec tasks.

The two expected files have small pre-existing Ruff findings. Mechanical import
sorting and removal of truly unused local assignments are allowed only in
these files so the full Ruff gate can pass. Do not reformat whole files or
change assertions as lint cleanup.

## TDD: RED -> GREEN -> REFACTOR

### RED 1 - obsolete fixture

Run before edits:

```bash
./scripts/test.sh apps.patients.tests.test_signals
```

Required baseline: 10 tests, 10 errors, each caused by:

```text
TypeError: EqmdCustomUser() got unexpected keyword arguments: 'profession'
```

Replace only the user setup with `create_navigation_user()` using synthetic
credentials, an explicit password, and
`profession_type=User.MEDICAL_DOCTOR`. Do not add the module to a lifecycle
allowlist and do not weaken lifecycle defaults.

### RED 2 - exposed production defect

Rerun the module immediately after the fixture-only edit and before production
changes. Required result: nine tests pass; only
`test_signal_error_handling` errors when `create_record_change_event()` tries
to insert a second `RecordNumberChangeEvent` for the same
`record_change_id`.

Strengthen that existing test before GREEN:

1. retain the original event primary key;
2. soft-delete it through the supported queryset behavior;
3. assert no active event and exactly one all-states event;
4. update/save the record;
5. assert one active event with the original primary key;
6. assert exactly one all-states row and synchronized record-number data;
7. preserve the patient denormalization assertion.

Do not catch `IntegrityError`, hard-delete the event, change the unique
constraint, or alter manager/model semantics.

### GREEN - restore the existing event

In `create_record_change_event()` only:

- perform the existing lookup through an all-states queryset obtained from the
  established soft-delete manager API (`objects.all_with_deleted()`);
- preserve first-create defaults;
- when the row already exists, clear `is_deleted`, `deleted_at`, `deleted_by`,
  and `deletion_reason` while applying the existing event field updates;
- save once so `RecordNumberChangeEvent.save()` continues synchronizing its
  domain fields from the source record.

Do not use the misleading inherited `all_objects` manager: the current Event
model binds it to `SoftDeleteInheritanceManager`, whose default queryset is
active-only. Do not modify that separate manager architecture in this slice.

### REFACTOR

Only targeted Ruff cleanup described above is allowed. If another signal test
exposes a business defect or the fix requires another file, report
`INCOMPLETE` and return to the planner.

## Mandatory inspections

```bash
rg -n "profession=|profession_type|create_user|create_navigation_user" \
  apps/patients/tests/test_signals.py
SOFT_DELETE_PATTERN="create_record_change_event|all_with_deleted|is_deleted"
SOFT_DELETE_PATTERN="${SOFT_DELETE_PATTERN}|deleted_at|deleted_by|deletion_reason"
rg -n "$SOFT_DELETE_PATTERN" \
  apps/patients/signals.py \
  apps/patients/tests/test_signals.py
git diff --word-diff=porcelain -- apps/patients/signals.py
git diff --check
git diff --stat
git status --short
```

The report must separate prior 004A diffs from 004B ownership and show the
exact production signal diff.

## Static and migration verification

```bash
docker exec eqmd_dev ruff check \
  apps/patients/signals.py \
  apps/patients/tests/test_signals.py
docker exec eqmd_dev python -m compileall -q \
  apps/patients/signals.py \
  apps/patients/tests/test_signals.py
docker exec eqmd_dev python manage.py check
docker exec eqmd_dev python manage.py makemigrations --check --dry-run
```

All commands must exit 0. No ignore, `noqa`, config change, migration, or
whole-file formatting is allowed.

## Functional verification

```bash
./scripts/test.sh apps.patients.tests.test_signals
./scripts/test.sh apps.events.tests.test_record_tracking_events
./scripts/test.sh apps.patients.tests.test_history
./scripts/test.sh apps.patients.tests.test_record_tracking_models
./scripts/test.sh apps.patients.tests.test_record_tracking_views
./scripts/test.sh apps.patients.tests.test_business_logic
./scripts/test.sh apps.core.tests.test_lifecycle_guard_rail
```

Required outcomes:

- signals: 10/10;
- event record tracking: 8/8;
- history: 13/13;
- record-tracking models: 18/18;
- record-tracking views: 11/11;
- business logic: 10/10;
- lifecycle guard rail command exits 0.

Do not add unrelated currently-red event soft-delete modules to this slice and
do not claim they are green.

## Full comparison and artifact gates

```bash
./scripts/test.sh
openspec validate restore-green-development-quality-gates --strict
markdownlint-cli2 \
  openspec/changes/restore-green-development-quality-gates/tasks.md \
  /tmp/restore-green-development-quality-gates-slice-004b-report.md
git diff --check
git status --short
```

Extract sorted `FAIL:`/`ERROR:` headers identically from the new full log and
`/tmp/full_suite_004a.log`. The ten prior `SignalTests` setup-error headers must
be removed, no new header may appear, and the added/removed counts must be
reported. If newly reached signal assertions fail, stop `INCOMPLETE`; do not
hide them as baseline debt.

## Binary acceptance criteria

- [ ] RED 1 is exactly 10/10 obsolete-`profession` setup errors.
- [ ] Fixture-only rerun records RED 2 as exactly 9/10 plus the known timeline
      event unique-constraint error.
- [ ] The existing test proves restoration of the same row and exactly one
      all-states event.
- [ ] The signal uses `objects.all_with_deleted()` and clears all four
      soft-delete fields on restoration.
- [ ] First create, active update, patient denormalization, and other signal
      assertions remain strict.
- [ ] Every listed functional/static/migration/artifact command exits 0.
- [ ] Full suite removes all ten prior signal headers and adds zero headers.
- [ ] Only the two expected files change in 004B.
- [ ] No package install, non-test database query/mutation, PII, container
      rebuild/recreation, commit, push, task edit, ignore, or migration occurs.
- [ ] Tasks 4.x, 4A.x, and 4B.x remain unchecked for third-LLM closure.

## Automatic `INCOMPLETE`

Report `INCOMPLETE` and stop if RED 2 is not captured; any signal assertion
remains red; a production file other than `signals.py` is needed; manager/model
architecture or a constraint is changed; another file changes; a full-suite
header is added; any non-test database is queried or mutated; or any install,
PII, container rebuild, commit, push, task edit, ignore, or migration occurs.

## Required report

Create `/tmp/restore-green-development-quality-gates-slice-004b-report.md` with
status, RED 1/RED 2 evidence, requirement matrix, exact signal/test diffs,
soft-delete restoration proof, target/static/migration/full-suite results,
database-isolation proof, scope audit, rollback, and third-LLM handoff.

The database-isolation section must list commands used and explicitly state
that no `manage.py shell`, SQL client, development-database probe, or restored
row was used. All synthetic objects must be created only by Django test cases.

## Ready-to-run implementer prompt

```text
Read every prerequisite in slice-004b-signals-fixture-and-soft-delete-recovery.md.
Implement ONLY reslice 004B with strict two-stage TDD. Preserve accepted 004A
work. First replace the obsolete SignalTests user fixture and capture 9/10 plus
the exposed unique-constraint RED. Strengthen the existing error-handling test
to prove same-row restoration, then minimally make create_record_change_event
look through objects.all_with_deleted() and clear all soft-delete metadata on
an existing event. Touch only test_signals.py and signals.py, make every listed
gate green, compare against /tmp/full_suite_004a.log, write
/tmp/restore-green-development-quality-gates-slice-004b-report.md, reply with
REPORT_PATH and STATUS, then STOP. Never query/mutate a non-test database. No
install, container rebuild, task edit, commit, or push.
```
