# Slice 009 - Entire Patients App Green

## Handoff for a zero-context implementer

Read all standard artifacts and approved reports 001-008. Inspect the latest
aggregate patients run and the original baseline. This is a closure/gap slice,
not permission for broad cleanup.

## Mandatory protocol

Run `./scripts/test.sh apps.patients` before editing and record every residual
failure ID. If zero, make no application/test edit and proceed to verification.
If residuals exist, classify them against prior slice scope. Edit at most three
planner-approved files; otherwise stop and propose a new focused slice. The app
suite, patient static gates, and migrations must all finish green. Compare the
full suite, report, and stop.

## Objective

Establish a verified zero-failure baseline for the complete patients app before
stabilizing other applications.

## Requirements

- **R1:** `apps.patients` exits 0 with zero failures/errors.
- **R2:** Ruff/format/Mypy pass for patient Python files changed by this change.
- **R3:** lifecycle guard reports no unapproved patients-test violation.
- **R4:** patient migrations show no drift.
- **R5:** rerun duplicate-review tests to preserve blocked identity slice 001.

## Expected files

- no code file if prior slices are complete
- at most three residual test/production files after planner approval
- `tasks.md` and the temporary report

Do not perform broad patient refactors or start patient-identity slice 002.

## TDD and inspections

Residual tests are RED. No speculative edit is allowed without a failure ID and
contract authority.

```bash
rg -n "max_allowed" apps/core/tests/test_lifecycle_guard_rail.py
git status --short
git diff --check
git diff --stat
```

## Verification commands

```bash
./scripts/test.sh apps.patients
./scripts/test.sh apps.patients.tests.test_duplicate_review_flow
./scripts/test.sh apps.core.tests.test_lifecycle_guard_rail
docker exec eqmd_dev ruff check apps/patients
docker exec eqmd_dev ruff format --check apps/patients
./scripts/typecheck.sh apps/patients/services/patient_identity.py \
  apps/patients/forms.py
docker exec eqmd_dev python manage.py check
docker exec eqmd_dev python manage.py makemigrations patients --check --dry-run
./scripts/test.sh
openspec validate restore-green-development-quality-gates --strict
markdownlint-cli2 \
  openspec/changes/restore-green-development-quality-gates/tasks.md \
  /tmp/restore-green-development-quality-gates-slice-009-report.md
```

If whole-directory Ruff exposes unrelated files not covered by slices 003-008,
report exact IDs and stop for planner reslicing rather than adding ignores.

## Binary criteria

- [ ] Entire patients suite exits 0.
- [ ] Patient static/type/migration gates pass or a new bounded slice is raised.
- [ ] Duplicate-review 21-test module remains green.
- [ ] No more than three approved residual files changed.
- [ ] Full suite has no new unexplained failure.

## Automatic `INCOMPLETE`

Any patients failure, unresolved patient static gate, more than three residual
files, unapproved ignore, identity slice 002 work, new full-suite failure,
missing report, PII, install, commit, or push.

## Required report

Create `/tmp/restore-green-development-quality-gates-slice-009-report.md` with
patients baseline/final summary, residual classification, all gate outputs,
full comparison, scope audit, and verifier handoff.

## Ready-to-run implementer prompt

```text
Implement ONLY slice 009 as a patients closure gate. Run the whole app first;
if residual fixes need more than three files, STOP INCOMPLETE and ask for a new
slice. Require zero patients failures plus static/type/migration gates, preserve
the duplicate-review flow, compare the full suite, write the report, and STOP.
Do not start identity slice 002, install, commit, or push.
```
