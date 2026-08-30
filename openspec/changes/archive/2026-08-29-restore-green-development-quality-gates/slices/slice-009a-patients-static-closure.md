# Slice 009A - Patients Static Closure for CI Gates

## Handoff for a zero-context implementer

Read all standard artifacts and approved reports 001-009. This is a
planner-authorized reslice after slice 009 correctly stopped: the patients
app is fully green (484 tests), but the three CI quality gates that this
change itself installed (ADR-0001, slice 002: `ruff check`,
`ruff format --check`, `mypy` — each run over PR-changed files) would fail
on the Python files this change touches. This slice closes exactly that
gap. It is mechanical plus two documented config ignores; it is not
permission for refactoring or behavior changes.

Planner decision context (from slice 009 report sections 2.1/2.2/7):

- Category A (files covered by slices 003-008): already clean, keep clean.
- Category B (`models.py` 16 + `views.py` 37) and Category C
  (`test_views.py` 7): files owned by this change; fix here.
- Category D (97 findings / 33 never-touched files): FROZEN inventory,
  untouched here; slice 018 enforces no-regression against it.

## Objective

Make the three CI quality gates pass over the exact set of Python files
changed by this change, with zero test-behavior change and zero
production-behavior change.

The changed-file set (24 files) is exactly:

```bash
git diff --name-only bcb9aa0 -- '*.py'
```

## Requirements

- **R1:** `ruff check` exit 0 on all 24 changed files. Permitted fix
  classes only: I001/F401/F811/F541 (safe autofix); F841 (drop the unused
  name, keep the call and side effects); RUF010 (explicit f-string type
  conversion); SIM201 (explicit `not (a == b)`); RUF012 (annotate with
  `typing.ClassVar`, the accepted slice-003 precedent).
- **R2:** the ONLY non-fix dispositions are two `pyproject.toml`
  per-file-ignores, each with a justification comment:
  `apps/patients/views.py = ["BLE001"]` (the broad `except Exception` is
  the documented 006/006A production contract for the 500 path) and
  `apps/patients/models.py = ["DTZ011"]` (replacing `date.today()` with a
  timezone-aware call is a behavior change deferred to clinical timezone
  work).
- **R3:** `ruff format` the changed-but-unformatted files; no manual
  reformat beyond the tool's output; `ruff format --check` then exits 0
  on all 24 files.
- **R4:** add `[[tool.mypy.overrides]]` with
  `module = ["apps.patients.models", "apps.patients.views"]`,
  `ignore_errors = true`, and a comment citing the frozen pre-existing
  inventory (82 findings, see slice 009 report). All other changed files
  must remain mypy-clean WITHOUT any override.
- **R5:** `apps.patients` stays 484/484 OK; duplicate-review 21 OK;
  lifecycle guard 0 patients violations; `makemigrations patients
--check --dry-run` stays clean; full suite identical to slice 008
  (2,026 tests / 94 failures / 334 errors / 12 skips / 428 headers,
  zero added).
- **R6:** production edits limited to mechanical lint/format/typing hunks
  in `models.py`, `views.py`, `test_views.py` (test), and the two config
  entries in `pyproject.toml`. No Category D file. No migration edit. No
  `noqa`. No ignore beyond R2/R4.

## TDD and inspections

This is a static-closure slice: RED is the three CI-equivalent commands
failing today; GREEN is exit 0 with unchanged test outcomes.

```bash
CHANGED=$(git diff --name-only bcb9aa0 -- '*.py')
docker exec eqmd_dev ruff check $CHANGED            # RED: 60 findings
./scripts/typecheck.sh $CHANGED                     # RED: 82 errors / 2 files
docker exec eqmd_dev ruff format --check $CHANGED   # RED: ~22 files
rg -n "BLE001|DTZ011|ignore_errors|per-file-ignores" pyproject.toml
git diff --check
git diff --stat
```

## Verification commands

```bash
CHANGED=$(git diff --name-only bcb9aa0 -- '*.py')
docker exec eqmd_dev ruff check $CHANGED
docker exec eqmd_dev ruff format --check $CHANGED
./scripts/typecheck.sh $CHANGED
./scripts/test.sh apps.patients
./scripts/test.sh apps.patients.tests.test_duplicate_review_flow
./scripts/test.sh apps.core.tests.test_lifecycle_guard_rail
docker exec eqmd_dev python manage.py check
docker exec eqmd_dev python manage.py makemigrations patients --check --dry-run
./scripts/test.sh
openspec validate restore-green-development-quality-gates --strict
markdownlint-cli2 \
  openspec/changes/restore-green-development-quality-gates/tasks.md \
  /tmp/restore-green-development-quality-gates-slice-009a-report.md
```

## Binary criteria

- [ ] All three CI-equivalent gates exit 0 on the 24-file changed set.
- [ ] Patients suite stays 484/484; duplicate-review 21; guard rail clean.
- [ ] Full suite identical to slice 008 (no added header, no test-count
      change).
- [ ] Per-finding disposition table complete (every one of the 60 check
      findings mapped to a fix class or the R2 ignore).
- [ ] Only permitted files edited; `pyproject.toml` gains exactly the two
      R2 ignores and the R4 override, each justified.

## Automatic `INCOMPLETE`

Any behavior change beyond R1-R4 classes, any new ignore/noqa, any
Category D file touched, any migration, any patients or full-suite
regression, empty verification command, missing report, PII, install,
commit, or push.

## Required report

Create `/tmp/restore-green-development-quality-gates-slice-009a-report.md`
with the RED/GREEN evidence for the three gates, the per-finding
disposition table, diff audit (before/after checksums of touched
production files), full-suite comparison versus slice 008, scope audit,
and verifier handoff.

## Ready-to-run implementer prompt

```text
Implement ONLY slice 009A. Close the three CI quality gates (ruff check,
ruff format --check, mypy) over the Python files changed by this change,
using only the permitted mechanical fix classes and the two documented
config ignores from the slice. Never change behavior, never touch
Category D files, never add noqa. Patients must stay 484/484 and the full
suite identical to slice 008. Write the report with the disposition table
and STOP.
```
