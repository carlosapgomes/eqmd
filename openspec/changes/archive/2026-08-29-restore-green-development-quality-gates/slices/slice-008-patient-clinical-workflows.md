# Slice 008 - Patient Admission, Status, and Soft-Delete Contracts

## Handoff for a zero-context implementer

Read the standard artifacts, reports 001-007, canonical patient/event specs,
status enums/FSM-equivalent rules, admission views/forms, soft-delete base, and
all listed tests. Start only after slice 007 approval.

Initial failures cover 24-hour edit permission, form messages/redirects,
status transitions, template action lists/badges, and soft-delete behavior.
These may be stale tests or real production defects; never guess in clinical
workflow code.

## Mandatory protocol

Baseline each module and build a scenario authority matrix before editing. Use
existing failures as RED. Test-only fixes require proof of stale expectation.
A production fix requires a behavior regression test, minimal code, explicit
rollback, and files listed below; ambiguity means `INCOMPLETE`. All targets
must be green, no new full-suite failures, report, stop.

## Objective

Restore admission, status, template, and patient soft-delete tests to the
canonical clinical workflow contracts.

## Requirements

- **R1:** preserve the 24-hour clinical edit rule and permission boundaries.
- **R2:** status transitions and available actions match canonical status rules.
- **R3:** UI messages, redirects, and badge semantics match the proven contract.
- **R4:** soft delete remains auditable and does not hard-delete retained data.
- **R5:** no migration or unrelated patient identity/tag change.

## Expected files

Tests:

- `apps/patients/tests/test_admission_edit_views.py`
- `apps/patients/tests/test_status_changes.py`
- `apps/patients/tests/test_status_template_tags.py`
- `apps/patients/tests/test_soft_delete.py`
- `apps/patients/tests/test_integration.py` only for its remaining status case

Production candidates, only if RED/spec proof requires and report justifies:

- corresponding admission/status view or form module
- corresponding patient status template-tag module
- `apps/core/models/soft_delete.py`

No model field, migration, patient-identity, or tag architecture change.

## TDD and inspections

```bash
rg -n "24|status|OUTPATIENT|INPATIENT|TRANSFERRED|DECEASED|soft.delete" \
  openspec/specs/patients docs/apps/patients.md \
  apps/patients/tests/test_admission_edit_views.py \
  apps/patients/tests/test_status_changes.py \
  apps/patients/tests/test_status_template_tags.py \
  apps/patients/tests/test_soft_delete.py
rg -n "permission|required|can_edit|available_status|hard_delete" \
  apps/patients apps/core/models/soft_delete.py
git diff --check
git diff --stat
```

## Verification commands

```bash
./scripts/test.sh apps.patients.tests.test_admission_edit_views
./scripts/test.sh apps.patients.tests.test_status_changes
./scripts/test.sh apps.patients.tests.test_status_template_tags
./scripts/test.sh apps.patients.tests.test_soft_delete
./scripts/test.sh apps.patients.tests.test_integration
docker exec eqmd_dev ruff check <CHANGED_PYTHON_FILES>
./scripts/typecheck.sh <CHANGED_PRODUCTION_PYTHON_FILES>
docker exec eqmd_dev python manage.py check
docker exec eqmd_dev python manage.py makemigrations patients --check --dry-run
./scripts/test.sh
openspec validate restore-green-development-quality-gates --strict
markdownlint-cli2 \
  openspec/changes/restore-green-development-quality-gates/tasks.md \
  /tmp/restore-green-development-quality-gates-slice-008-report.md
```

Replace placeholders with non-empty changed-file paths; if no production files
changed, record typecheck as not applicable with proof.

## Binary criteria

- [ ] Authority matrix covers every changed assertion/behavior.
- [ ] All five target modules are green.
- [ ] Clinical permissions/status/retention are not relaxed.
- [ ] Any production fix has RED proof and rollback.
- [ ] No migration or new full-suite failure exists.

## Automatic `INCOMPLETE`

Ambiguous clinical contract, relaxed permission/retention, target failure,
production edit without RED/spec proof, migration, unexpected file, empty
placeholder command, new full-suite failure, missing report, PII, install,
commit, or push.

## Required report

Create `/tmp/restore-green-development-quality-gates-slice-008-report.md` with
scenario authority matrix, RED/GREEN, test-vs-production decisions, rollback,
all gates, full comparison, and verifier handoff.

## Ready-to-run implementer prompt

```text
Implement ONLY slice 008. Establish authoritative admission/status/soft-delete
scenarios before edits. Fix stale tests or minimal production defects only with
proof and RED tests; never relax clinical permissions, 24-hour rules, or data
retention. Make every listed module green, run all gates/full comparison, write
the required report, and STOP. Ambiguity or any failure is INCOMPLETE.
```
