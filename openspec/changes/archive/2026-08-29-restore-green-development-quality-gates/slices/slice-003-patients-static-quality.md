# Slice 003 - Patients Static Quality Gate

## Handoff for a zero-context implementer

Read the standard project/change artifacts, ADR-0001, approved reports 001-002,
`apps/patients/forms.py`, its focused tests, and this slice. Do not start before
the runtime/tooling foundation is approved.

Known blockers: legacy `forms.py` fails Ruff formatting; scoped Ruff reports
RUF012 Django `Meta` patterns and SIM102; Mypy reports an untyped
`InternalTransferForm.ward`. The patient-identity implementation is already in
the same file and must not change behavior.

## Mandatory DeepSeek4-Flash protocol

Record byte hash, line count, focused form/view/identity tests, Ruff, format,
and Mypy before editing. Treat current static failures as RED. Isolate the
mechanical formatting diff, inspect semantic diffs separately, and do not
refactor forms. Targeted static and behavior commands must all become green.
Run the full suite for no-new-failure comparison, report, and stop.

## Objective

Make the modified patient form file pass scoped Ruff, formatting, and Mypy
without changing patient, admission, status, or duplicate-review behavior.

## Requirements

- **R1:** apply Ruff formatting as one mechanical, reviewable operation.
- **R2:** resolve RUF012 using the narrow documented Django policy; no blanket
  project-wide ignore.
- **R3:** resolve SIM102 and the `ward` type error with behavior-preserving code.
- **R4:** patient forms, views, and duplicate-review regressions remain green.
- **R5:** no other oversized patient module is reformatted or refactored.

## Expected files

- `apps/patients/forms.py`
- `apps/patients/tests/test_forms.py` only if a missing regression is proven
- `pyproject.toml` only for a narrow, justified per-file/per-rule policy

Do not modify models, views, templates, migrations, services, or clinical
specs. Preserve the existing patient-identity hunks exactly in behavior.

## TDD

Use current static failures as RED and run behavior tests before edits. Apply
formatting, then make the smallest lint/type corrections. A test assertion may
not be weakened to accommodate cleanup.

## Mandatory inspections

```bash
sha256sum apps/patients/forms.py
wc -l apps/patients/forms.py
git diff --word-diff=porcelain -- apps/patients/forms.py
rg -n "RUF012|per-file|extend-ignore" pyproject.toml
git diff --check
git diff --stat
```

Explain why every semantic token change is behavior preserving.

## Verification commands

```bash
docker exec eqmd_dev ruff check apps/patients/forms.py
docker exec eqmd_dev ruff format --check apps/patients/forms.py
./scripts/typecheck.sh apps/patients/forms.py
./scripts/test.sh apps.patients.tests.test_forms \
  apps.patients.tests.test_views \
  apps.patients.tests.test_duplicate_review_flow
docker exec eqmd_dev python manage.py check
./scripts/test.sh
openspec validate restore-green-development-quality-gates --strict
markdownlint-cli2 \
  openspec/changes/restore-green-development-quality-gates/tasks.md \
  /tmp/restore-green-development-quality-gates-slice-003-report.md
```

## Binary acceptance criteria

- [ ] Ruff check, format, and Mypy all exit 0 for `forms.py`.
- [ ] Focused patient behavior tests exit 0.
- [ ] Mechanical and semantic diffs are separately explained.
- [ ] No broad ignore, unrelated refactor, or behavior change exists.
- [ ] Full suite has no new unexplained failure IDs.

## Automatic `INCOMPLETE` conditions

Any static target failure, focused regression, unreviewable semantic churn,
blanket ignore, unexpected file, changed identity behavior, missing full
comparison/report, PII, or commit/push.

## Required report

Create `/tmp/restore-green-development-quality-gates-slice-003-report.md` with
hash/line baseline, RED/GREEN static output, semantic-diff audit, test results,
full comparison, rollback, and verifier handoff.

## Ready-to-run implementer prompt

```text
Implement ONLY slice 003. Preserve all patient behavior while making
apps/patients/forms.py pass Ruff check, Ruff format, and scoped Mypy. Separate
mechanical formatting from semantic fixes, use no blanket ignores, run the
forms/views/duplicate-review regression bundle and full comparison, write the
required report, then STOP. Any failure or unexplained semantic diff is
INCOMPLETE. Do not commit or push.
```
