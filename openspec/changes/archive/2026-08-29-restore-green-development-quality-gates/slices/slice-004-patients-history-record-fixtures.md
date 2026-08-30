# Slice 004 - Patients History and Record-Tracking Fixtures

## Handoff for a zero-context implementer

Read all standard project/change artifacts, approved reports 001-003,
`apps/accounts/tests/factories.py`, the listed patient test modules, relevant
models/migrations, and this slice. Implement only after slice 003 approval.

Initial failures include removed `profession` arguments, string
`profession_type='doctor'`, and lifecycle setup drift. Existing supported
fixtures use numeric profession choices and `NavigationReadyUserFactory`.

## Mandatory DeepSeek4-Flash protocol

Run each listed module before edits and record exact failure IDs/signatures.
Use those failures as RED. Inspect current user, record-number, signal, and
history contracts before changing tests. Prefer the shared factory; do not
change production models merely to accept obsolete test fields. Each target
module must end fully green. Run static checks and the full-suite comparison,
write the report, and stop.

## Objective

Restore history and record-tracking tests by replacing obsolete user/setup
contracts while preserving all history, audit, and record-number assertions.

## Requirements

- **R1:** use supported profession values/fields and navigation-ready lifecycle
  state where requests are exercised.
- **R2:** preserve historical-record, signal, actor, and audit assertions.
- **R3:** remove local fixture duplication when the shared factory expresses the
  same contract.
- **R4:** no patient model, record-number policy, or migration changes.

## Expected files

- `apps/patients/tests/test_history.py`
- `apps/patients/tests/test_record_tracking_models.py`
- `apps/patients/tests/test_record_tracking_views.py`
- `apps/accounts/tests/factories.py` only if a missing reusable supported
  factory capability is proven

Production code, migrations, forms, and patient-identity files are forbidden.

## TDD

The existing setup exceptions are RED. Make setup minimal and rerun one module
at a time. If a business assertion then fails, inspect its authority; do not
silently update it. Ambiguous behavior means `INCOMPLETE` and planner review.

## Mandatory inspections

```bash
rg -n \
  "profession=|profession_type|create_user|NavigationReady" \
  apps/patients/tests/test_history.py \
  apps/patients/tests/test_record_tracking_models.py \
  apps/patients/tests/test_record_tracking_views.py \
  apps/accounts/tests/factories.py
git diff --check
git diff --stat
```

## Verification commands

```bash
./scripts/test.sh apps.patients.tests.test_history
./scripts/test.sh apps.patients.tests.test_record_tracking_models
./scripts/test.sh apps.patients.tests.test_record_tracking_views
./scripts/test.sh apps.core.tests.test_lifecycle_guard_rail
docker exec eqmd_dev ruff check \
  apps/patients/tests/test_history.py \
  apps/patients/tests/test_record_tracking_models.py \
  apps/patients/tests/test_record_tracking_views.py
docker exec eqmd_dev python manage.py check
./scripts/test.sh
openspec validate restore-green-development-quality-gates --strict
markdownlint-cli2 \
  openspec/changes/restore-green-development-quality-gates/tasks.md \
  /tmp/restore-green-development-quality-gates-slice-004-report.md
```

## Binary acceptance criteria

- [ ] All three target modules exit 0 with zero failures/errors.
- [ ] Obsolete user fields are absent from the cohort.
- [ ] History/record assertions are not weakened.
- [ ] No production code or migration changed.
- [ ] Full suite has no new unexplained failure IDs.

## Automatic `INCOMPLETE` conditions

Any target failure, changed domain assertion without contract evidence,
production edit, duplicated ad hoc factory, unexpected file, new full-suite
failure, missing report, PII, install, commit, or push.

## Required report

Create `/tmp/restore-green-development-quality-gates-slice-004-report.md` with
failure-ID baseline, authority evidence, fixture before/after, module results,
full comparison, scope audit, and verifier handoff.

## Ready-to-run implementer prompt

```text
Implement ONLY slice 004. Use existing failing setup as RED, replace obsolete
patient-test user fixtures with supported numeric/lifecycle-ready factories,
preserve every history and record-tracking business assertion, make all three
modules green, run the full comparison, write the exact /tmp report, and STOP.
Do not edit production code, install packages, commit, or push. Ambiguous
contract or any failed gate means INCOMPLETE.
```
