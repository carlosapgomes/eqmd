# Slice 005A - Refresh Command Dry-Run and Aggregate Verbosity

## Handoff for a zero-context implementer

Read completely, in order: `AGENTS.md`, `PROJECT_CONTEXT.md`, the canonical
workflow documents, ADR-0001, every artifact of this change, approved reports
001-004B, slice 005, its `INCOMPLETE` report, the third-LLM verification, this
reslice, the current command, and the full current development-utility tests.
Implement only 005A and stop.

Preserve the accepted partial slice-005 work in exactly these files:

- `apps/patients/tests/test_api_views.py` (11/11 green);
- `apps/patients/tests/test_performance.py` (9/9 green);
- `apps/patients/tests/test_development_utils.py` (7/9 green).

The remaining RED tests are:

- `test_command_dry_run_mode`: `--dry-run` is unrecognized;
- `test_command_verbosity_levels`: verbosity 2 produces only the normal summary
  and does not satisfy the stale patient-identifier expectation.

The planner decision is:

1. `refresh_patient_data --dry-run` is a supported safety feature and must
   persist no model, history, event, or denormalized-field change;
2. verbosity 2 provides additional **aggregate** progress only;
3. command output must not disclose patient names, UUIDs, record numbers, or
   other patient-level identifiers;
4. the old `VERBOSE001`/`NEW` output assertions are redefined, not deleted;
5. normal successful summary and well-formed missing-UUID behavior remain
   unchanged.

The currently unused `transaction` import, existing dry-run conventions in
other maintenance commands, and the safety requirements support this contract.
No restored data may be used to verify it.

## Mandatory DeepSeek4-Flash protocol

1. Record `BASE_REF`, ownership, checksums of all accepted slice-005 files, the
   two exact RED tracebacks, and both immediate full-suite baselines before
   editing.
2. Strengthen/redefine the command tests before production code and rerun the
   two methods to preserve RED.
3. Implement the smallest aggregate, non-identifying dry-run/verbosity command
   contract. Use only Django-managed test databases.
4. Run every listed target and full comparison. Any target failure or added
   full-suite header means `INCOMPLETE`.
5. Write the exact report, reply with `REPORT_PATH` and `STATUS`, and stop.
   Do not start slice 006, mark tasks, commit, or push.

## Baseline authority

Use both baselines and do not substitute the stale pre-004B manifest:

- accepted pre-slice-005 baseline: `/tmp/full_suite_004b.log` — 2,030 tests,
  157 failures, 365 errors, 12 skips, 522 headers;
- verifier baseline for the accepted partial slice-005 working tree:
  `/tmp/full_suite_005_verifier.log` — 2,030 tests, 147 failures, 348 errors,
  12 skips, 495 headers.

The eight UTC/local-midnight failures present only in the implementer's earlier
`/tmp/s005_full_suite.log` disappeared on verifier rerun. They are not baseline
waivers and must not reappear in the 005A manifest.

## Objective

Close slice 005 by supporting a transactionally rolled-back dry run and
non-identifying aggregate verbosity for `refresh_patient_data`, while proving
that normal refresh still repairs deliberately corrupted denormalized data.

## Requirements

- **R1:** `--dry-run` is a documented boolean command option.
- **R2:** dry run executes the same refresh path inside `transaction.atomic()`
  and marks that transaction for rollback after all selected patients are
  processed.
- **R3:** dry run leaves patient fields, simple-history rows, timeline events,
  and all other database state unchanged.
- **R4:** verbosity 2 emits only aggregate selection/progress information;
  verbosity output contains no patient name, UUID, record number, CPF, CNS, or
  other patient-level value.
- **R5:** normal mode persists corrections and preserves the existing summary
  `Refreshed denormalized fields for N patients`.
- **R6:** the supported `--patient-id` filter and well-formed missing UUID output
  remain unchanged.
- **R7:** all three slice-005 target modules and lifecycle/static/migration/full
  comparison gates finish green.

## Expected files

- `apps/patients/management/commands/refresh_patient_data.py`
- `apps/patients/tests/test_development_utils.py`

No other file may change in 005A. Do not edit models, signals, event managers,
API/performance tests, shared helpers, migrations, settings, dependencies,
scripts, CI, or OpenSpec tasks.

## TDD: RED -> GREEN -> REFACTOR

### RED 1 - preserve the two failures

Before editing, run individually:

```bash
./scripts/test.sh \
  apps.patients.tests.test_development_utils.DataConsistencyTests.test_command_dry_run_mode
./scripts/test.sh \
  apps.patients.tests.test_development_utils.DataConsistencyTests.test_command_verbosity_levels
```

Required causes are unrecognized `--dry-run` and missing verbosity detail.
Record both outputs.

### RED 2 - strengthen real mutation evidence and privacy

Before production changes, update only the existing command tests:

1. In both normal refresh tests, create source records/admissions first and then
   deliberately corrupt denormalized fields with `QuerySet.update()`. This is
   required because record/admission signals otherwise repair the fields before
   the command runs, producing false-positive command tests.
2. In the dry-run test, create source record and active admission, then corrupt
   `current_record_number`, status/current-admission fields, and any asserted
   denormalized values through `QuerySet.update()`.
3. Capture patient history count and all-states patient timeline-event count
   before dry run. After it, assert every corrupted field remains unchanged and
   both counts are identical.
4. Replace the stale dry-run output expectation for `NEW` with an exact
   aggregate mode/count expectation, and assert that synthetic patient name,
   UUID, `OLD`, and `NEW` are absent from output.
5. Replace the stale verbosity expectation for `VERBOSE001` with an aggregate
   selected/processed count, preserve the normal completion summary, and assert
   name, UUID, and record number are absent.
6. Keep the existing non-dry success and missing-patient assertions strict.

Rerun both tests before command edits. They must remain RED for the same missing
interfaces, not because of fixture/setup errors.

For all-states event counting, use the established
`Event.objects.all_with_deleted()` API; do not alter event managers.

### GREEN - command contract

In `refresh_patient_data.py`:

- sort imports and use the existing `transaction` import;
- add `--dry-run` with `action="store_true"` and non-identifying help text;
- determine an aggregate selected-patient count without rendering patient
  objects or identifiers;
- at verbosity 2 or higher, emit one aggregate selection/progress line;
- execute dry-run refreshes inside `transaction.atomic()` and call
  `transaction.set_rollback(True)` before leaving the block;
- emit a clear aggregate `DRY RUN` completion stating that no changes were
  saved;
- in normal mode, execute the existing refresh behavior and preserve its exact
  aggregate success summary;
- do not print any per-patient value in any mode.

Do not catch exceptions to force green, use mocks instead of PostgreSQL,
manually reverse individual writes, or run the command against the development
or restored database. Normal mode need not gain a new outer transaction in
this slice; preserve its existing failure semantics.

### REFACTOR

Only local extraction needed to avoid duplicating the refresh loop is allowed.
No model/service extraction or unrelated command cleanup is permitted.

## Mandatory inspections

```bash
rg -n "dry-run|dry_run|verbosity|transaction|patient-id|Refreshed" \
  apps/patients/management/commands/refresh_patient_data.py
rg -n "QuerySet|objects.filter|history|all_with_deleted|assertNotIn|DRY RUN" \
  apps/patients/tests/test_development_utils.py
git diff --word-diff=porcelain -- \
  apps/patients/management/commands/refresh_patient_data.py \
  apps/patients/tests/test_development_utils.py
git diff --check
git diff --stat
git status --short
```

The report must separate prior slice-005 test diffs from 005A ownership and
show every output string used by the command without real patient values.

## Static and migration verification

```bash
docker exec eqmd_dev ruff check \
  apps/patients/management/commands/refresh_patient_data.py \
  apps/patients/tests/test_development_utils.py
docker exec eqmd_dev python -m compileall -q \
  apps/patients/management/commands/refresh_patient_data.py \
  apps/patients/tests/test_development_utils.py
docker exec eqmd_dev python manage.py check
docker exec eqmd_dev python manage.py makemigrations --check --dry-run
```

All commands must exit 0. No ignore, `noqa`, configuration change, dependency
change, or migration is allowed.

## Functional verification

Run sequentially; do not run test processes concurrently against the shared
preserved PostgreSQL test database.

```bash
./scripts/test.sh apps.patients.tests.test_development_utils
./scripts/test.sh apps.patients.tests.test_api_views
./scripts/test.sh apps.patients.tests.test_performance
./scripts/test.sh apps.patients.tests.test_signals
./scripts/test.sh apps.core.tests.test_lifecycle_guard_rail
```

Required outcomes:

- development utilities: 9/9;
- API: 11/11;
- performance: 9/9;
- signals: 10/10;
- lifecycle guard rail command exits 0.

The report must include direct database assertions proving dry-run rollback and
normal-mode persistence. Command output alone is insufficient.

## Full comparison and artifact gates

```bash
./scripts/test.sh > /tmp/full_suite_005a.log 2>&1
openspec validate restore-green-development-quality-gates --strict
markdownlint-cli2 \
  openspec/changes/restore-green-development-quality-gates/tasks.md \
  /tmp/restore-green-development-quality-gates-slice-005a-report.md
git diff --check
git status --short
```

Extract sorted FAIL/ERROR headers identically from
`/tmp/full_suite_005_verifier.log`, `/tmp/full_suite_004b.log`, and the new log.
The new result must:

- remove exactly the two remaining development-command headers from the
  verifier baseline and add zero headers;
- contain no slice-005 target header;
- reconcile the full delta from 004B without treating time-of-day failures as
  accepted baseline.

If unrelated time failures reappear, stop `INCOMPLETE`; do not classify them as
an acceptable added set.

## Binary acceptance criteria

- [ ] Both original command tests and strengthened versions are RED for the
      expected missing interfaces before production changes.
- [ ] Normal command tests deliberately corrupt fields after source signals and
      prove persisted repair.
- [ ] Dry run uses `transaction.atomic()` plus explicit rollback and proves no
      patient/history/event persistence.
- [ ] Verbose and dry-run output is aggregate and excludes every synthetic
      patient-level identifier asserted by the tests.
- [ ] Existing summary, patient filter, and missing UUID behavior remain strict.
- [ ] Development utilities are 9/9; API 11/11; performance 9/9; signals 10/10.
- [ ] Static, Django, migration, lifecycle, OpenSpec, Markdownlint, and diff
      gates exit 0.
- [ ] Full suite removes exactly two headers from the verifier baseline and
      adds zero.
- [ ] Only the two expected files change in 005A.
- [ ] No non-test database access/mutation, package install, container rebuild,
      PII, task edit, commit, push, ignore, or migration occurs.
- [ ] Tasks 5.x and 5A.x remain unchecked for third-LLM closure.

## Automatic `INCOMPLETE`

Report `INCOMPLETE` and stop if either target test remains red; dry run persists
any field/history/event change; output contains a patient-level value; a normal
refresh test does not first establish deliberate corruption; any target/static
or migration command fails; a full-suite header is added; another file changes;
or any non-test database access, install, PII, container rebuild, task edit,
commit, push, ignore, or migration occurs.

## Required report

Create `/tmp/restore-green-development-quality-gates-slice-005a-report.md` with
status, original/strengthened RED evidence, requirement matrix, exact command
and test diffs, normal persistence proof, dry-run rollback/history/event proof,
output privacy proof, sequential target/static/migration/full-suite results,
database-isolation proof, scope audit, rollback, and third-LLM handoff.

The database-isolation section must state that no `manage.py shell`, SQL client,
development command invocation, restored row, or concurrent test process was
used. Synthetic data must exist only inside Django-managed test cases.

## Ready-to-run implementer prompt

```text
Read every prerequisite in slice-005a-refresh-command-dry-run-and-verbosity.md.
Implement ONLY reslice 005A with strict TDD. Preserve accepted partial slice-005
work. Strengthen normal tests by corrupting denormalized fields after source
signals; redefine the two command tests to require transactional dry-run
rollback and aggregate non-identifying verbosity. Then minimally implement
--dry-run using transaction.atomic()+set_rollback(True) and aggregate verbosity
without printing any patient value. Touch only refresh_patient_data.py and
test_development_utils.py. Run tests sequentially, make all listed gates green,
compare against /tmp/full_suite_005_verifier.log and full_suite_004b.log, write
/tmp/restore-green-development-quality-gates-slice-005a-report.md, reply with
REPORT_PATH and STATUS, then STOP before slice 006. Never access a non-test
database. No install, task edit, commit, or push.
```
