# Slice 018 - Enforce and Close the Full Green Baseline

## Handoff for a zero-context implementer

Read every project/change artifact, correction reports 001A, 004A, 004B,
005A, and 006A, and approved reports 001-017. Read the lifecycle guard rail,
CI workflow, quality scripts, ADR-0001, and the blocked patient-identity
slice 001/report. Start only when all previous app cohorts are approved
green.

This final slice has **no baseline waiver**. Every target must return exit code
0 with zero failures/errors.

## Mandatory DeepSeek4-Flash protocol

1. Record clean ownership/status and run the complete final gate before edits.
2. If any residual failure exists, classify it and edit at most three
   planner-approved files; otherwise stop and request a focused follow-up slice.
3. Set lifecycle guard enforcement to zero only after its scan reports zero.
4. Run every command exactly; no omitted, informative, or tolerated failure.
5. Rerun patient-identity slice 001 from its original contract, not its waiver.
6. Mark tasks only after third-LLM-verifiable evidence is complete.
7. Write the final report and stop. Do not start identity slice 002.
8. Do not commit or push.

## Objective

Convert the progressive stabilization baseline into enforced zero-failure local
and CI gates, then re-verify the blocked patient-identity slice 001.

## Requirements

- **R1:** lifecycle guard rail allows zero unapproved violations and fails on a
  synthetic violation.
- **R2:** lock, Django parity, check, Ruff, format, Mypy, and global migration
  gates all exit 0.
- **R3:** every app and `./scripts/test.sh` exit 0 with zero failures/errors.
- **R4:** CI full suite is mandatory rather than informative/continue-on-error.
- **R5:** patient-identity slice 001 passes every original gate without waiver.
- **R6:** identity tasks 1.1-1.5 are marked only after separate third-LLM
  approval; slice 002 does not begin here.

## Expected files

- `apps/core/tests/test_lifecycle_guard_rail.py`
- `.github/workflows/ci-pr.yml`
- `openspec/changes/restore-green-development-quality-gates/tasks.md`
- patient-identity `tasks.md` only after its independent verification
- at most three planner-approved residual files

No feature implementation, migration, dependency, or broad cleanup.

## TDD and inspections

The pre-edit full gate is RED only if previous slices missed a residual. The
guard must have a focused test proving one synthetic violation fails.

```bash
rg -n "max_allowed|continue-on-error|full-suite|ruff|mypy|makemigrations" \
  apps/core/tests/test_lifecycle_guard_rail.py .github/workflows/ci-pr.yml
rg -n "\[x\].*1\.[1-5]|\[ \].*1\.[1-5]" \
  openspec/changes/harden-patient-identity-and-duplicate-prevention/tasks.md
git status --short
git diff --check
git diff --stat
```

## Verification commands

```bash
docker exec eqmd_dev uv lock --check
docker exec eqmd_dev python -c 'import django; print(django.get_version())'
docker exec eqmd_dev python manage.py check
docker exec eqmd_dev ruff check $CHANGED_PY_FILES
app-patients ruff/format no-regression check (see Static enforcement below)
./scripts/typecheck.sh <ALL_PHASED_TYPECHECK_PATHS>
docker exec eqmd_dev python manage.py makemigrations --check --dry-run
./scripts/test.sh apps.core.tests.test_lifecycle_guard_rail
./scripts/test.sh
./scripts/test.sh apps.patients.tests.test_duplicate_review_flow
openspec validate restore-green-development-quality-gates --strict
openspec validate harden-patient-identity-and-duplicate-prevention --strict
markdownlint-cli2 \
  openspec/changes/restore-green-development-quality-gates/**/*.md \
  openspec/changes/harden-patient-identity-and-duplicate-prevention/tasks.md \
  /tmp/restore-green-development-quality-gates-slice-018-report.md \
  /tmp/harden-patient-identity-and-duplicate-prevention-slice-001-report.md
```

Replace the phased typecheck placeholder with paths explicitly established by
reports 001-017 plus 001A, 004A, 004B, 005A, and 006A; an empty substitution
is forbidden.

## Static enforcement (planner amendment after slice 009)

Whole-repository zero-findings is NOT a gate of this change. Enforcement is:

1. `$CHANGED_PY_FILES` (every Python file touched by this change or the
   patient-identity change) must exit 0 on `ruff check`,
   `ruff format --check`, and `mypy` — mirroring the CI gates exactly.
2. No-regression against frozen pre-existing inventories: regenerate
   `docker exec eqmd_dev ruff check --output-format concise apps config >
/tmp/ruff_repo_final.txt` and require zero NEW finding lines versus the
   frozen baselines — patients: the 157-ID inventory in slice 009 report
   section 9 (`/tmp/ruff_patients_full.txt`); other apps: the frozen
   inventories recorded in their cohort reports (010-017). Zero new files
   and zero new finding IDs; decreases are recorded, never blocking.

## Binary criteria

- [ ] Every command exits 0 and the no-regression check adds zero findings.
- [ ] Full suite has zero failures/errors; no waiver or skip increase.
- [ ] Lifecycle guard threshold is zero and its negative test passes.
- [ ] CI full suite blocks failure.
- [ ] Patient-identity slice 001 original gates all pass.
- [ ] No more than three approved residual files changed.
- [ ] Identity slice 002 remains untouched.

## Automatic `INCOMPLETE`

Any nonzero gate, failure/error, increased skip without approval, lifecycle
threshold above zero, informative full CI, placeholder command, more than three
residual files, identity slice 002 work, missing report, PII, install, commit,
or push.

## Required report

Create `/tmp/restore-green-development-quality-gates-slice-018-report.md` with
all exact commands/exit codes, full test summary, skip comparison, lifecycle
negative proof, CI inspection, patient-identity rerun evidence, final file
scope, rollback, and verifier handoff.

## Ready-to-run implementer prompt

```text
Implement ONLY final slice 018 after reports 001-017, 001A, 004A, 004B,
005A, and 006A are approved. There is no
waiver: every lock/runtime/static/type/migration/lifecycle/full-test gate must
exit 0. Enforce lifecycle zero, make CI full suite blocking, rerun the original
patient-identity slice 001 gates, write both required evidence reports, and
STOP before identity slice 002. More than three residual files or any failing
command is INCOMPLETE. Do not install, commit, or push.
```
