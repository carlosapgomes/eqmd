# Slice 004 - PostgreSQL Record-Number Constraint

## Handoff for a zero-context implementer

Read every file completely, in order:

1. `AGENTS.md`
2. `PROJECT_CONTEXT.md`
3. `docs/workflows/coding-standards.md`
4. `docs/workflows/llm-collab.md`
5. `docs/workflows/clean-code-skill.md`
6. `openspec/changes/harden-patient-identity-and-duplicate-prevention/proposal.md`
7. `openspec/changes/harden-patient-identity-and-duplicate-prevention/design.md`
8. `openspec/changes/harden-patient-identity-and-duplicate-prevention/specs/patients/spec.md`
9. `openspec/changes/harden-patient-identity-and-duplicate-prevention/tasks.md`
10. Verified `/tmp` reports for slices 001-003
11. This slice file

Implement only slice 004 and stop. This is a PostgreSQL-only, migration-bearing,
CRITICAL slice.

Expected starting state:

- Managed forms/views/admin reject record reuse and preserve old current state.
- Direct ORM/import and concurrent transactions are not yet authoritative.
- `PatientRecordNumber.Meta` still contains
  `unique_current_record_per_patient` and no global record constraint.
- `apps/patients/migrations/0001_initial.py` is the only patient migration and
  must never be edited.
- The restored production copy has known collisions: 37 canonical groups
  across different patients and 3 repeats within one patient's history.
- Therefore this migration must **not** be applied to the restored production
  copy during implementation. It must fail closed there until a separate
  consolidation change is completed.

## Mandatory protocol for DeepSeek4-Flash

Any failed/missing item means `INCOMPLETE`; leave tasks unchecked and stop.

1. Record `BASE_REF=$(git rev-parse HEAD)` and `git status --short`. Preserve
   unrelated work and stop if expected files contain unverified modifications.
2. Before editing, run full `./scripts/test.sh`. Record exit code,
   `Ran N tests`, failures/errors/skips. Stop unless it returns exit 0 with zero
   failures/errors.
3. Verify `ruff` and `mypy` already exist inside `eqmd_dev`; do not install
   packages.
4. Write the R1-R7 matrix before editing. Confirm PostgreSQL is the test backend
   and inspect current migration leaf nodes.
5. Write tests first and capture a real RED: direct duplicate ORM persistence
   currently succeeds or the expected global constraint is absent. A migration
   setup/import error is not a valid RED.
6. Implement minimal GREEN. Create a new `0002` migration; never edit/squash
   `0001_initial.py`. The preflight is non-mutating and emits aggregate counts
   only.
7. Do not run `manage.py migrate` against the restored `eqmd_dev` database.
   Migration execution tests must use Django's clean PostgreSQL test database.
8. REFACTOR migration helper/test code for clarity, DRY, YAGNI, typed production
   changes, and functions at most 25 lines where normal Python standards apply.
9. Run every inspection and quality command. Final full suite must have exit 0,
   zero failures/errors, and no lower test count than baseline.
10. Create the exact temporary report. Never include collided values, patient
    identifiers, or production rows. Do not commit or push.

## Objective

Add a PostgreSQL-authoritative, case-insensitive and outer-whitespace-insensitive
lifetime uniqueness constraint for `PatientRecordNumber`, with aggregate-only
preflight, direct ORM coverage, and a deterministic concurrent-write test.

## Functional scope

### R1 - Functional global uniqueness

Add a named Django `UniqueConstraint` over
`Lower(Trim("record_number"))`, independent of `patient` and `is_current`.
Use the exact name:

`unique_patient_record_number_lifetime`

Preserve `unique_current_record_per_patient` and existing indexes.

### R2 - Full retained-history semantics

The constraint must reject:

- a canonical equivalent owned by another patient;
- a canonical equivalent in the same patient's history;
- current or historical rows;
- ownership by a soft-deleted patient;
- direct `PatientRecordNumber.objects.create()` and import paths that use ORM.

No condition on `is_current` or patient deletion is allowed.

### R3 - Aggregate-only preflight

Before `AddConstraint`, a `RunPython` operation must query canonical collision
groups. If any group has more than one row, abort before schema modification.
The exception contains aggregate group and row counts only. It must not contain
record numbers, patient IDs, names, CPF, CNS, or row representations.

The forward operation never updates/deletes/merges data. The reverse preflight
is a no-op; rolling back removes only the constraint.

### R4 - Clean migration path

On a clean PostgreSQL test database, migration applies and retains all existing
rows unchanged. `makemigrations --check --dry-run` must report no drift.

### R5 - Concurrent-write guarantee

A `TransactionTestCase` using independent database connections and a
synchronization barrier must attempt the same available canonical key from two
transactions. Exactly one assignment succeeds; the other receives the known
uniqueness failure; one row exists afterward.

Do not replace this with two sequential writes and call it a concurrency test.
Avoid sleep-based timing.

### R6 - Dirty migration refusal test

Test the preflight against migration state/data containing a synthetic
collision. Assert:

- it raises before constraint addition;
- synthetic rows are unchanged;
- exception text contains aggregate counts;
- exception text omits all synthetic record and patient identifiers.

Tests may import the migration module with `importlib`; restore database state
cleanly for subsequent tests.

### R7 - Deployment remains blocked

Completing this implementation slice does not authorize applying the migration
to the restored production copy. The report must state `Release: BLOCKED` until
tasks 5.1 and 5.2 prove the separate consolidation and zero aggregate
collisions.

## Expected files

Modify/create only:

- `apps/patients/models.py`
- `apps/patients/migrations/0002_patient_record_number_lifetime_unique.py`
  (new; use this deterministic name)
- `apps/patients/tests/test_patient_identity_record_numbers.py`
- `openspec/changes/harden-patient-identity-and-duplicate-prevention/tasks.md`
  only after all implementation gates pass

Any extra file requires prior planner approval. Forbidden:

- editing/deleting/squashing `0001_initial.py`;
- any data-fixing migration or production record mutation;
- forms, views, templates, service, admin, signals, URLs, permissions, imports;
- CPF/CNS constraints, new fields, dependencies, SQLite fallbacks;
- running migration against the restored production-copy database;
- destructive database or Docker-volume commands.

## TDD: RED -> GREEN -> REFACTOR

### RED

Extend the slice 003 focused test module before production edits. At minimum
cover:

1. direct ORM duplicate across patients is rejected by the named constraint;
2. same-patient repeat is rejected;
3. case and external-whitespace equivalents are rejected;
4. different values remain allowed;
5. historical/current and soft-deleted ownership remain covered;
6. two real concurrent transactions produce one winner;
7. dirty preflight raises with aggregate-only text and leaves rows unchanged;
8. clean preflight permits migration and leaves rows unchanged;
9. model migration state contains both old per-patient-current and new global
   constraints.

First run:

```bash
./scripts/test.sh apps.patients.tests.test_patient_identity_record_numbers
```

Capture an assertion failure proving absent database enforcement. If existing
slice 003 application validation prevents the test setup, use direct ORM or the
historical migration state appropriately; do not weaken application behavior.

### GREEN

Add model metadata and one new migration with preflight before constraint.
Implement only enough tests/helpers to prove R1-R7.

### REFACTOR

- Keep preflight query aggregate and deterministic.
- Separate thread worker and assertion orchestration in the concurrency test.
- Use a barrier, close/reopen thread-local connections correctly, and collect
  explicit outcomes.
- Avoid duplicating canonical expression definitions where Django migration
  serialization requires a snapshot; explain unavoidable migration duplication
  in the report.
- Keep new normal Python functions at most 25 lines and typed where applicable.

## Mandatory inspection checks

Run and interpret all:

```bash
find apps/patients/migrations -maxdepth 1 -type f -printf '%f\n' | sort
constraint_pattern='unique_current_record_per_patient'
constraint_pattern+='|unique_patient_record_number_lifetime|Lower|Trim'
rg -n "$constraint_pattern" apps/patients/models.py \
  apps/patients/migrations/0002_patient_record_number_lifetime_unique.py
preflight_pattern='RunPython|AddConstraint|UPDATE|DELETE|merge'
preflight_pattern+='|patient_id|record_number'
rg -n "$preflight_pattern" \
  apps/patients/migrations/0002_patient_record_number_lifetime_unique.py
concurrency_pattern='TransactionTestCase|Barrier|close_old_connections'
concurrency_pattern+='|IntegrityError|concurr'
rg -n "$concurrency_pattern" \
  apps/patients/tests/test_patient_identity_record_numbers.py
git diff -- apps/patients/migrations/0001_initial.py
docker exec eqmd_dev python manage.py showmigrations patients --plan
docker exec eqmd_dev python manage.py sqlmigrate patients \
  0002_patient_record_number_lifetime_unique
```

Expected interpretation:

- a new `0002` exists and `0001` diff is empty;
- both constraints remain in model state;
- preflight precedes `AddConstraint` and contains no data-mutation operation;
- the exception path uses aggregate counts only;
- concurrency test uses barrier and independent connections;
- generated SQL creates the expected functional unique constraint.

Do not paste SQL containing real values; `sqlmigrate` emits schema SQL only.

## Verification commands

Run all commands exactly. None may target the restored application database for
migration application:

```bash
docker exec eqmd_dev python manage.py check
docker exec eqmd_dev ruff check \
  apps/patients/models.py \
  apps/patients/migrations/0002_patient_record_number_lifetime_unique.py \
  apps/patients/tests/test_patient_identity_record_numbers.py
docker exec eqmd_dev ruff format --check \
  apps/patients/models.py \
  apps/patients/migrations/0002_patient_record_number_lifetime_unique.py \
  apps/patients/tests/test_patient_identity_record_numbers.py
./scripts/typecheck.sh \
  apps/patients/models.py \
  apps/patients/tests/test_patient_identity_record_numbers.py
./scripts/test.sh apps.patients.tests.test_patient_identity_record_numbers
docker exec eqmd_dev python manage.py makemigrations --check --dry-run
docker exec eqmd_dev python manage.py sqlmigrate patients \
  0002_patient_record_number_lifetime_unique
./scripts/test.sh
openspec validate harden-patient-identity-and-duplicate-prevention --strict
markdownlint-cli2 \
  openspec/changes/harden-patient-identity-and-duplicate-prevention/tasks.md \
  /tmp/harden-patient-identity-and-duplicate-prevention-slice-004-report.md
```

## Binary success criteria

- [ ] R1-R7 each have test/inspection evidence.
- [ ] Full baseline passed before edits with exit 0 and zero failures/errors.
- [ ] RED proves absent DB guarantee; focused GREEN passes.
- [ ] Named functional global constraint exists and old constraint remains.
- [ ] Direct, same-patient, canonical, historical, soft-delete, and distinct
      cases pass.
- [ ] Real barrier-based concurrency test has exactly one winner.
- [ ] Dirty preflight aborts before schema change, changes zero rows, and emits
      aggregate-only text.
- [ ] Clean migration path and migration drift checks pass.
- [ ] `0001_initial.py` has zero diff.
- [ ] No production-copy migration or data mutation was executed.
- [ ] Every quality gate passes and final full count is not lower than baseline.
- [ ] Tasks 4.1-4.5 are marked only after implementation verification.
- [ ] Tasks 5.1-5.5 remain unchecked until the separate release process.
- [ ] Exact temporary report exists, passes lint, contains no PII, and says
      `Release: BLOCKED`.

## Self-evaluation gates

Answer with evidence or mark incomplete:

1. Is uniqueness global across every retained row with no current/deleted
   condition?
2. Does the canonical expression exactly match `Lower(Trim(record_number))`?
3. Does preflight run before `AddConstraint` and perform no mutation?
4. Can exception/report text be proven free of synthetic collided values and
   patient identifiers?
5. Does the concurrency test use independent connections plus a barrier and
   produce exactly one winner without sleeps?
6. Do direct ORM and same-patient duplicate tests fail by DB guarantee rather
   than form validation?
7. Are both constraints present and `0001_initial.py` untouched?
8. Did all migration tests run only against clean/synthetic test databases?
9. Does rollback remove only the constraint and never rewrite records?
10. Did baseline/final suites pass with no lower final test count?
11. Are tasks 5.x still unchecked and release explicitly blocked?
12. Were all out-of-scope files, installs, commits, pushes, and destructive
    commands avoided?

### Automatic INCOMPLETE conditions

Mark incomplete for any of the following:

- missing/non-green full baseline before edits;
- missing tooling or package installation during slice;
- no real behavior RED;
- any required test/inspection/quality command missing or failed;
- final tests nonzero, with failure/error, or lower count;
- migration modifies data, emits collided values, or lacks preflight;
- constraint is conditional on current/deleted or includes patient ownership;
- same-patient repeat remains possible;
- concurrency test is sequential, sleep-based, flaky, or lacks one-winner
  assertion;
- `0001_initial.py` changed or migration was squashed/renamed unexpectedly;
- migration was applied to the restored production copy;
- a production value or identifier appears in output/report;
- forms/views/service/admin/signals/imports/permissions changed;
- tasks 5.x were marked, report omits `Release: BLOCKED`, or report is absent;
- any commit, push, destructive command, or ad hoc install occurred.

## Required temporary report

Create exactly:

`/tmp/harden-patient-identity-and-duplicate-prevention-slice-004-report.md`

Required sections:

1. `Status: COMPLETE|INCOMPLETE` and separate `Release: BLOCKED`.
2. `BASE_REF`, initial status, and preserved unrelated changes.
3. R1-R7 matrix.
4. PostgreSQL backend/toolchain and migration-leaf preflight.
5. Full baseline command/exit/`Ran N tests`/failures/errors/skips.
6. RED failing assertions and expected reasons.
7. GREEN/refactor evidence.
8. Before/after snippets for model constraint, aggregate preflight, operation
   order, direct ORM test, and concurrency worker/orchestration.
9. Inspection output/interpretation, including empty `0001` diff.
10. Migration SQL summary without any patient values.
11. Every quality command and exit code.
12. Baseline/final comparison with explicit zero failures/errors.
13. Answers to every self-evaluation gate.
14. Privacy/no-data-mutation statement and rollback explanation.
15. `Handoff for verifier`: changed files, exact reruns, R1-R7 checklist,
    manual migration-order/security checks, known risks, and release blockers
    tasks 5.1/5.2.

## Ready-to-run prompt for the implementer

```text
Start with zero conversation context. Read AGENTS.md, PROJECT_CONTEXT.md, all
workflow standards, every artifact for
harden-patient-identity-and-duplicate-prevention, verified slice 001-003
reports, and slice-004-postgresql-record-constraint.md. Implement ONLY slice
004.

Follow the DeepSeek4-Flash protocol literally: record BASE_REF/status; run FULL
./scripts/test.sh before editing and stop if not fully green; verify ruff/mypy
exist without installing; create a real DB-enforcement RED; add only the named
PostgreSQL functional constraint plus aggregate non-mutating preflight; test
real barrier-based concurrency; REFACTOR cleanly; run every inspection/quality
gate; compare baseline/final; and create the exact temporary report with
Release: BLOCKED.

Never edit 0001_initial.py. Never run migration application against the
restored production-copy database. Do not mutate/print production data. Do not
touch forms, views, templates, service, admin, signals, URLs, permissions,
imports, CPF/CNS constraints, dependencies, or unrelated code. Do not install,
commit, push, or run destructive commands. Mark only tasks 4.1-4.5 after all
implementation gates pass; keep all tasks 5.x unchecked. Any missing/failing
gate, leaked value, data mutation, final failure/error, or lower final test
count requires Status: INCOMPLETE.

Reply only with REPORT_PATH=/tmp/harden-patient-identity-and-duplicate-prevention-slice-004-report.md
and one-line status, then STOP for third-LLM verification.
```
