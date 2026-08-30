<!-- markdownlint-disable MD013 -->

# Slice 018C - Lifecycle Zero, Enforcement, and Change Closure

## Handoff for a zero-context implementer

Read standard artifacts, all approved reports 001-018 plus 018A/018B, and
slice 018's report section 8 (requested follow-up, items 1 and 5). Start
only after 018A and 018B approvals. This slice finishes the original slice
018 objective: enforced zero-violation lifecycle gate, blocking CI full
suite, and the patient-identity rerun evidence.

Residual at handoff: the 214-violation guard-rail manifest minus the
`apps/core` cohort converted by 018B (expected ≈168 violations in ≈60
files; regenerate `/tmp/guardrail_violations_018c.txt` before edits).
Distribution measured 2026-08-29: mediafiles 49, drugtemplates 26, patients
21, botauth 19, reports 10, dailynotes 10, events 9, outpatientprescriptions
7, consentforms 7, dischargereports 3, simplenotes 2, remainder in
accounts/sample-content family modules.

## Mandatory protocol

Baseline the scan and record the exact count. Convert fixtures
mechanically (`NavigationReadyUserFactory` / `SuperUserFactory`, or
`password_change_required=False, terms_accepted=True` on `create_user` when
a factory import is impractical). NEVER convert modules that genuinely test
lifecycle middleware — the scanner allowlist (6 modules) is exhaustive;
expanding it requires planner approval recorded in the report. Only after
the scan reports zero: set `max_allowed = 0`, add the negative synthetic
test, flip the CI job. Then rerun identity gates. No install, commit, push,
or migration. Stop above sixty semantic files without reslicing.

## Objective

Enforce lifecycle zero, make the CI full suite blocking, and complete tasks
18.1-18.5 evidence.

## Requirements

- **R1:** guard rail scans zero violations; `max_allowed = 0` in
  `apps/core/tests/test_lifecycle_guard_rail.py`; a focused test proves a
  synthetic violating file FAILS the rail (TDD: write the negative test
  first, watch it fail against `max_allowed=0` semantics, then land).
- **R2:** `.github/workflows/ci-pr.yml` full-suite job becomes blocking
  (remove `continue-on-error: true` at line ~224); every CI gate mirrors
  local gates (ruff check/format on `$CHANGED_PY_FILES`, scoped mypy, lock,
  check, migrations, full suite).
- **R3:** full suite exits 0 (count as stabilized by 018B); skip count
  unchanged; guard rail suite itself green with zero count.
- **R4:** patient-identity slice 001 original gates rerun green
  (`ruff check`/`format` on `apps/patients/services/patient_identity.py`,
  `apps/patients/forms.py`,
  `apps/patients/tests/test_duplicate_review_flow.py`; scoped mypy on the
  two production files; `./scripts/test.sh
apps.patients.tests.test_duplicate_review_flow` = 21 OK; migrations
  clean; full suite green). Identity tasks 1.1-1.5 remain UNCHECKED —
  marking them happens only after separate third-LLM approval; identity
  slice 002 does not begin here.
- **R5:** no NEW ruff findings versus the frozen inventories
  (`/tmp/ruff_repo_before_018.txt` and the post-018A/018B regenerations).

## Expected files

- `apps/core/tests/test_lifecycle_guard_rail.py` (max_allowed, negative test)
- `.github/workflows/ci-pr.yml`
- the ≈60 fixture files from the residual manifest (mechanical conversions
  only; each revertible with `git checkout -- <file>`)
- `openspec/changes/restore-green-development-quality-gates/tasks.md`
  (tasks 18.1-18.5 after evidence)

## TDD and inspections

```bash
./scripts/test.sh apps.core.tests.test_lifecycle_guard_rail  # count -> 0
rg -n "max_allowed" apps/core/tests/test_lifecycle_guard_rail.py
rg -n "continue-on-error|full-suite" .github/workflows/ci-pr.yml
rg -c "NavigationReadyUserFactory|password_change_required=False" \
  <converted files>
git diff --check
```

## Verification commands

```bash
./scripts/test.sh apps.core.tests.test_lifecycle_guard_rail  # OK, 0 violations, negative test passes
./scripts/test.sh                                            # exit 0, documented count
docker exec eqmd_dev ruff check $CHANGED_PY_FILES             # exit 0
docker exec eqmd_dev ruff format --check $CHANGED_PY_FILES    # exit 0
./scripts/typecheck.sh $CHANGED_PRODUCTION_FILES              # exit 0
docker exec eqmd_dev uv lock --check
docker exec eqmd_dev python manage.py check
docker exec eqmd_dev python manage.py makemigrations --check --dry-run
./scripts/test.sh apps.patients.tests.test_duplicate_review_flow  # 21 OK
openspec validate restore-green-development-quality-gates --strict
openspec validate harden-patient-identity-and-duplicate-prevention --strict
markdownlint-cli2 \
  openspec/changes/restore-green-development-quality-gates/slices/slice-018c-lifecycle-zero-enforcement-and-close.md \
  /tmp/restore-green-development-quality-gates-slice-018c-report.md
```

## Binary criteria

- [ ] Guard rail reports zero, `max_allowed = 0`, negative synthetic test
      fails-without-fix proven.
- [ ] CI full-suite job blocking; no `continue-on-error` remains on it.
- [ ] Full suite and every static/lock/migration gate exit 0; zero new
      findings.
- [ ] Identity rerun green; tasks 1.1-1.5 still unchecked; slice 002
      untouched.
- [ ] Tasks 18.1-18.5 marked with third-LLM-verifiable evidence.

## Automatic `INCOMPLETE`

Any remaining violation, nonzero gate, allowlist expansion without planner
approval, count/skip regression, new finding, identity task marked
prematurely, slice 002 started, missing report, PII, install, commit, or
push.

## Required report

Create `/tmp/restore-green-development-quality-gates-slice-018c-report.md`
with the violation-manifest delta (before/after per app), enforcement
proof, negative-test TDD trace, CI diff, identity rerun outputs, tasks
marked, scope audit, and verifier handoff.

## Ready-to-run implementer prompt

```text
Implement ONLY slice 018C after 018A and 018B approvals. Convert the
remaining lifecycle fixtures to zero violations, set the guard rail to
enforced zero with a negative synthetic test, make the CI full suite
blocking, rerun the patient-identity slice 001 gates, mark tasks 18.1-18.5,
write the report, and STOP. Do not start identity slice 002. No install,
commit, or push.
```
