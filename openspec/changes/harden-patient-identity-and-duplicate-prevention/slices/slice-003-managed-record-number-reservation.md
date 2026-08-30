# Slice 003 - Managed Record-Number Reservation

## Handoff for a zero-context implementer

Read these files fully and in order:

1. `AGENTS.md`
2. `PROJECT_CONTEXT.md`
3. `docs/workflows/coding-standards.md`
4. `docs/workflows/llm-collab.md`
5. `docs/workflows/clean-code-skill.md`
6. `openspec/changes/harden-patient-identity-and-duplicate-prevention/proposal.md`
7. `openspec/changes/harden-patient-identity-and-duplicate-prevention/design.md`
8. `openspec/changes/harden-patient-identity-and-duplicate-prevention/specs/patients/spec.md`
9. `openspec/changes/harden-patient-identity-and-duplicate-prevention/tasks.md`
10. The verified reports for slices 001 and 002 from their `/tmp` paths
11. This slice file

Implement exactly one slice and stop. Do not rely on conversation history.

Current code facts to verify before planning:

- `PatientRecordNumber` has only
  `unique_current_record_per_patient`; it does not reserve a number globally.
- `PatientForm.clean_initial_record_number()`,
  `PatientRecordNumberForm.clean_record_number()`, and
  `QuickRecordNumberUpdateForm.clean_record_number()` validate format only.
- `Patient.update_current_record_number()` deactivates the current row before
  creating the new row and does not wrap the whole sequence in an explicit
  transaction.
- Creation, regular record change, quick change, update, delete, admin, and
  import commands are separate entry points.
- Slice 004 will add the database constraint for direct ORM/import concurrency.
  This slice protects ordinary interactive/admin flows and atomicity only.
- Existing dirty production data must not be inspected with identifiable
  output or modified during implementation.

## Mandatory protocol for DeepSeek4-Flash

If any protocol item fails, report `INCOMPLETE`, leave tasks unchecked, and
stop.

1. Record `BASE_REF=$(git rev-parse HEAD)` and `git status --short`. Preserve
   unrelated changes and stop if expected files contain unverified work.
2. Run the full pre-edit baseline `./scripts/test.sh`. Record exit code,
   `Ran N tests`, failures/errors/skips. A nonzero exit or any failure/error is
   an automatic blocker before edits.
3. Confirm `ruff` and `mypy` already exist inside `eqmd_dev`; never install
   tooling in a slice.
4. Before editing, write the report matrix
   `Requirement -> file(s) -> test(s)/inspection(s)` and inventory every
   `PatientRecordNumber` write/delete path found by the required `rg` command.
5. Create a real focused RED first. Setup, import, syntax, or migration errors
   do not count.
6. Implement only R1-R8. Do not create/edit migrations or attempt the slice 004
   constraint/concurrency implementation.
7. Apply GREEN minimally. Keep orchestration transactional, translate known
   conflicts to form/domain errors, and preserve old current state on failure.
8. REFACTOR with clean code, DRY, YAGNI, typed service helpers, functions at
   most 25 lines, and minimal integrations into oversized files.
9. Run every inspection and quality gate. Final full tests must be exit code 0,
   zero failures/errors, and no lower test count than baseline.
10. Create the exact `/tmp` Markdown report without real patient data. Do not
    commit or push; stop for third-LLM verification.

## Objective

Prevent ordinary user/admin workflows from assigning any current or historical
prontuário again, preserve the existing current assignment atomically on
failure, and make persisted record-number history immutable and non-deletable
through ordinary interfaces.

## Functional scope

### R1 - Canonical application comparison

Define one service normalizer for record numbers: trim external whitespace and
compare case-insensitively. Do not strip meaningful internal punctuation or
invent a new record format. Conflict lookup must inspect all
`PatientRecordNumber` rows, regardless of `is_current` or patient soft-delete.

### R2 - Initial patient creation guard

`PatientForm` must reject a canonical record number already present in any
current/historical assignment. The rejection creates neither patient nor
record. Include ownership by a soft-deleted patient and repeat within the same
patient history semantics.

### R3 - Regular and quick record-change guard

Both regular and quick record change forms must return a field/domain error for
an existing canonical number. The regular CreateView and quick POST must show a
controlled message/invalid form rather than HTTP 500.

### R4 - Atomic record transition and known race translation

The update operation must wrap conflict recheck, current deactivation, new row
creation, and denormalized patient update in one transaction. If validation or
persistence fails, the old row remains current and
`Patient.current_record_number` remains unchanged.

Prepare the interactive create/change adapters for the planned PostgreSQL
constraint name `unique_patient_record_number_lifetime`. An `IntegrityError`
from that exact constraint must be translated to the same controlled duplicate
outcome after rollback; unrelated integrity errors must be re-raised.

This pre-save recheck reduces stale-form risk but is not the concurrent database
guarantee; slice 004 supplies that constraint.

### R5 - Same-patient history is also reserved

A patient cannot reactivate or create a second row for one of its own old
numbers. Multiple distinct historical numbers remain supported.

### R6 - Persisted assignment number is immutable

`PatientRecordNumberForm` may continue to edit allowed metadata if existing
behavior requires it, but changing `record_number` on a persisted assignment
must be rejected. Do not mutate historical rows to represent a change; append a
new assignment through the existing dedicated flow.

### R7 - Ordinary deletion is disabled

The user-facing record delete endpoint must reject the operation without
removing data. `PatientRecordNumberAdmin` must not expose delete permission for
persisted assignments. Preserve view authentication/permissions and avoid URL
removal; a controlled rejection is less disruptive.

Direct SQL and `QuerySet.delete()` are trusted/out-of-band operations and are
not expanded in this slice.

### R8 - Entry-point inventory and deferral

Classify every write path from the mandatory search as:

- protected now by service/form/model method/admin behavior; or
- explicitly protected by slice 004 database constraint.

Do not modify import commands in this slice. The report must prove that direct
ORM/import coverage is intentionally deferred, not forgotten.

## Expected files

Modify/create only:

- `apps/patients/services/patient_identity.py`
- `apps/patients/models.py`
- `apps/patients/forms.py`
- `apps/patients/views.py`
- `apps/patients/admin.py`
- `apps/patients/tests/test_patient_identity_record_numbers.py` (new)
- `openspec/changes/harden-patient-identity-and-duplicate-prevention/tasks.md`
  only after all gates pass

Six production/test files are justified because this vertical flow has service,
model transaction, three existing entry adapters, and focused tests. Any other
file needs planner approval. Forbidden:

- migrations or changes to `0001_initial.py`;
- signals, URLs, permission utilities, import/sync commands;
- CPF/CNS/name candidate behavior;
- concurrency test/constraint from slice 004;
- broad refactor of models/forms/views/admin;
- dependencies or generated assets.

## TDD: RED -> GREEN -> REFACTOR

### RED

Create the focused module first. At minimum test:

1. patient creation rejects a current number owned by another patient;
2. patient creation rejects a historical number;
3. case/external-whitespace canonical equivalents conflict;
4. a soft-deleted patient's record remains reserved;
5. a patient cannot reactivate its own historical number;
6. regular record change returns controlled form error and keeps old current;
7. quick record change returns controlled message and keeps old current;
8. a simulated violation named `unique_patient_record_number_lifetime` rolls
   back state and becomes the controlled duplicate outcome;
9. an unrelated simulated `IntegrityError` rolls back state and is re-raised;
10. changing `record_number` on a persisted assignment is invalid;
11. ordinary delete view preserves the row;
12. admin reports no delete permission for the assignment;
13. assigning a distinct new number still creates one new current row,
    deactivates one old row, and synchronizes the denormalized field;
14. existing authentication and record permissions remain enforced.

Run:

```bash
./scripts/test.sh apps.patients.tests.test_patient_identity_record_numbers
```

Record at least one assertion failing due to missing reservation/atomicity.

### GREEN

Implement minimal canonical lookup, form adapters, transaction, controlled
view outcomes, and admin immutability. Reuse the existing identity service; do
not create another `services` module.

### REFACTOR

- Keep canonicalization and conflict lookup single-source.
- Keep view changes transport-only and model transaction cohesive.
- Use domain-specific validation errors, not broad `except Exception`.
- Avoid boolean flags and duplicated query fragments.
- Add types to new/changed functions; new functions at most 25 lines.
- Report before/after line counts for every oversized legacy file.

## Mandatory inspection checks

Run before editing for inventory and after editing for verification. Include
both interpretations in the report:

```bash
write_pattern='PatientRecordNumber\.objects\.(create|get_or_create'
write_pattern+='|update_or_create)|update_current_record_number'
write_pattern+='|PatientRecordNumberForm|QuickRecordNumberUpdateForm'
rg -n "$write_pattern" apps --glob '*.py' --glob '!**/migrations/**'
identity_pattern='normalize_record|record.*conflict|all_objects'
identity_pattern+='|is_current|transaction\.atomic|IntegrityError'
rg -n "$identity_pattern" \
  apps/patients/services/patient_identity.py \
  apps/patients/models.py apps/patients/forms.py apps/patients/views.py
immutability_pattern='PatientRecordNumber(Delete|Update)View'
immutability_pattern+='|has_delete_permission|get_readonly_fields|record_number'
rg -n "$immutability_pattern" apps/patients/views.py apps/patients/admin.py
rg -n "UniqueConstraint|Lower|Trim|AddConstraint|RunPython" \
  apps/patients/models.py apps/patients/migrations
permission_pattern="permission_required = 'patients\."
permission_pattern+='(add|change|delete)_patientrecordnumber'
rg -n "$permission_pattern" apps/patients/views.py
wc -l apps/patients/models.py apps/patients/forms.py \
  apps/patients/views.py apps/patients/admin.py \
  apps/patients/services/patient_identity.py
```

Expected interpretation:

- every write/delete path is in the report inventory;
- canonical conflict lookup is single-source and transactions are visible;
- update/delete/admin immutability is explicit;
- existing permission declarations remain;
- no new functional global constraint/migration appears yet;
- oversized-file growth is minimal and justified.

## Verification commands

Execute all:

```bash
docker exec eqmd_dev python manage.py check
docker exec eqmd_dev ruff check \
  apps/patients/services/patient_identity.py \
  apps/patients/models.py \
  apps/patients/forms.py \
  apps/patients/views.py \
  apps/patients/admin.py \
  apps/patients/tests/test_patient_identity_record_numbers.py
docker exec eqmd_dev ruff format --check \
  apps/patients/services/patient_identity.py \
  apps/patients/models.py \
  apps/patients/forms.py \
  apps/patients/views.py \
  apps/patients/admin.py \
  apps/patients/tests/test_patient_identity_record_numbers.py
./scripts/typecheck.sh \
  apps/patients/services/patient_identity.py \
  apps/patients/models.py \
  apps/patients/forms.py \
  apps/patients/views.py \
  apps/patients/admin.py
./scripts/test.sh apps.patients.tests.test_patient_identity_record_numbers
./scripts/test.sh apps.patients.tests.test_forms \
  apps.patients.tests.test_record_tracking_models \
  apps.patients.tests.test_record_tracking_views \
  apps.patients.tests.test_views
docker exec eqmd_dev python manage.py makemigrations --check --dry-run
./scripts/test.sh
openspec validate harden-patient-identity-and-duplicate-prevention --strict
markdownlint-cli2 \
  openspec/changes/harden-patient-identity-and-duplicate-prevention/tasks.md \
  /tmp/harden-patient-identity-and-duplicate-prevention-slice-003-report.md
```

## Binary success criteria

- [ ] R1-R8 map to test or inspection evidence.
- [ ] Full baseline passed before edits with exit code 0 and zero errors/fails.
- [ ] Real RED and focused GREEN are recorded.
- [ ] Initial, regular, quick, same-patient, historical, soft-deleted, and
      canonical-equivalence conflicts are controlled.
- [ ] Conflict/failure preserves current row and denormalized field atomically.
- [ ] Distinct new record change preserves existing valid behavior.
- [ ] Ordinary edit/delete and admin delete are rejected.
- [ ] Existing auth and permissions are unchanged and tested.
- [ ] Every write path is classified now or deferred to slice 004.
- [ ] No migration/constraint or future-slice work was introduced.
- [ ] All gates pass and final full test count is not lower than baseline.
- [ ] Only tasks 3.1-3.5 are marked after completion.
- [ ] Exact temporary report exists, is lint-clean, and contains no PII.

## Self-evaluation gates

Answer with `YES` and evidence or mark incomplete:

1. Does lookup include current, historical, same-patient, and soft-deleted
   ownership?
2. Is canonical record normalization defined once and limited to trim/case?
3. Does the final transaction recheck immediately before mutation?
4. Does any raised known conflict leave the old current row and denormalized
   value unchanged?
5. Is only the planned constraint violation translated after atomic rollback,
   while unrelated integrity errors are re-raised?
6. Do regular and quick paths return controlled user feedback rather than 500?
7. Is a persisted assignment immutable and non-deletable in ordinary/admin
   interfaces?
8. Are direct ORM/import paths explicitly deferred to the slice 004 constraint?
9. Were permissions preserved and tested?
10. Are view/form integrations thin and service/model responsibilities cohesive?
11. Did all new functions receive types and stay within 25 lines?
12. Did baseline/final full suites pass with no lower final count?
13. Were migrations, signals, URLs, imports, future behavior, commits, pushes,
    and installs avoided?

### Automatic INCOMPLETE conditions

Mark incomplete if any applies:

- full pre-edit baseline was missing/nonzero or had failure/error;
- missing `ruff`/`mypy` or any ad hoc install;
- no valid behavior RED;
- any required test, inspection, or quality command missing/failing;
- final tests nonzero, contain failure/error, or count less than baseline;
- conflict can deactivate old current or change denormalized state partially;
- historical/same-patient/soft-deleted reuse is allowed;
- update/delete/admin can mutate or remove a persisted number ordinarily;
- permissions were relaxed or broad exceptions hide defects;
- write-path inventory is absent or an occurrence is unclassified;
- migration/constraint/import/signal/URL/future-slice work appears;
- unexpected file changed without approval;
- PII appears in report/evidence;
- tasks marked early, report missing, commit/push/install/destructive command.

## Required temporary report

Create exactly:

`/tmp/harden-patient-identity-and-duplicate-prevention-slice-003-report.md`

Include:

1. Status.
2. `BASE_REF`, initial status, and unrelated changes preserved.
3. R1-R8 matrix.
4. Pre-edit write/delete entry-point inventory with protection classification.
5. Full baseline command/exit/`Ran N tests`/failures/errors/skips.
6. RED failures and expected reasons.
7. GREEN/refactor evidence.
8. Before/after snippets for canonical lookup, transaction, form adapter,
   controlled view error, and admin/delete protection.
9. Inspection output/interpretation and before/after line counts.
10. Every quality command and exit code.
11. Baseline/final comparison with explicit zero failures/errors.
12. All self-evaluation answers.
13. Scope justification, privacy statement, and slice 004 residual risk.
14. `Handoff for verifier`: changed files, exact reruns, R1-R8 checklist,
    manual inspections, known limitations, and explicit no-migration statement.

## Ready-to-run prompt for the implementer

```text
With zero conversation context, read AGENTS.md, PROJECT_CONTEXT.md, all coding
workflow documents, every OpenSpec artifact for
harden-patient-identity-and-duplicate-prevention, verified slice 001/002
reports, and slice-003-managed-record-number-reservation.md. Implement ONLY
slice 003.

Follow the DeepSeek4-Flash protocol literally: record BASE_REF/status and a
complete write-path inventory; run FULL ./scripts/test.sh before editing and
stop if not fully green; verify ruff/mypy exist without installing; create a
real RED; implement minimal GREEN; REFACTOR with clean code/DRY/YAGNI, typed
functions <=25 lines and thin views/forms; run all inspections and quality
gates; compare baseline/final; create the exact temporary report.

Do not touch migrations, 0001_initial.py, signals, URLs, permissions, import
commands, CPF/CNS/name behavior, dependencies, or slice 004 concurrency work.
Do not expose patient data, install packages, commit, or push. Mark only tasks
3.1-3.5 after every gate passes. Any missing/failing gate, partial state on
conflict, final failure/error, or lower final count means Status: INCOMPLETE
and unchecked tasks.

Reply only with REPORT_PATH=/tmp/harden-patient-identity-and-duplicate-prevention-slice-003-report.md
and one-line status, then STOP for third-LLM verification.
```
