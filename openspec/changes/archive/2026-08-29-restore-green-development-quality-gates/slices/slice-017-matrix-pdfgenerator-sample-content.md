# Slice 017 - Matrix, PDF Generator, and Sample Content Cohorts

## Handoff for a zero-context implementer

Read standard artifacts and reports 001-016, current Matrix configuration and
commands, PDF generator escaping/table contracts, sample-content permissions,
and all listed tests. Start only after events/history approval.

Initial residuals include missing `MatrixConfig.bot_display_name`, outdated PDF
escaping/table expectations, and sample-content lifecycle `302` redirects.

## Mandatory protocol

Baseline all three app suites and build a small contract matrix. Existing
failures are RED. Update stale constructors/fixtures only when current dataclass,
templates, or permissions prove authority. Production changes require behavior
RED and current spec/security proof. Never weaken HTML escaping or access
control. Stop above five semantic files. All apps green, full comparison,
report, stop.

## Objective

Restore the final small non-patient cohorts before enforcing the repository
zero-failure baseline.

## Requirements

- **R1:** Matrix tests construct the complete current configuration and preserve
  room/localpart behavior.
- **R2:** PDF generator tests enforce safe escaping and required patient table
  output.
- **R3:** sample-content tests use lifecycle-ready users and preserve endpoint
  permissions.
- **R4:** all three app suites exit 0.

## Expected files

- `apps/matrix_integration/tests/test_commands.py`
- `apps/matrix_integration/tests/test_provisioning.py`
- `apps/pdfgenerator/tests/test_pdf_generation.py`
- `apps/sample_content/tests.py`
- one shared test helper only if justified

Production files require RED/spec proof and planner approval. No dependency,
migration, or more than five semantic files without reslicing.

## TDD and inspections

```bash
rg -n "MatrixConfig|bot_display_name|localpart|escape|patient.*table|302" \
  apps/matrix_integration/tests \
  apps/pdfgenerator/tests/test_pdf_generation.py \
  apps/sample_content/tests.py
rg -n "class MatrixConfig|bot_display_name|escape|permission|required" \
  apps/matrix_integration apps/pdfgenerator apps/sample_content
git diff --check
git diff --stat
```

## Verification commands

```bash
./scripts/test.sh apps.matrix_integration
./scripts/test.sh apps.pdfgenerator
./scripts/test.sh apps.sample_content
./scripts/test.sh apps.core.tests.test_lifecycle_guard_rail
docker exec eqmd_dev ruff check <CHANGED_PYTHON_FILES>
docker exec eqmd_dev ruff format --check <CHANGED_PYTHON_FILES>
./scripts/typecheck.sh <CHANGED_PRODUCTION_PYTHON_FILES>
docker exec eqmd_dev python manage.py check
docker exec eqmd_dev python manage.py makemigrations --check --dry-run
./scripts/test.sh
openspec validate restore-green-development-quality-gates --strict
markdownlint-cli2 \
  openspec/changes/restore-green-development-quality-gates/tasks.md \
  /tmp/restore-green-development-quality-gates-slice-017-report.md
```

## Binary criteria

- [ ] Matrix, PDF generator, and sample-content app suites exit 0.
- [ ] Matrix configuration behavior remains explicit.
- [ ] Escaping and permission assertions remain strict.
- [ ] No more than five semantic files change without reslicing.
- [ ] No migration or new unexplained full-suite failure exists.

## Automatic `INCOMPLETE`

Any app red, weakened escaping/access, production default added only to hide a
stale test, excessive files, migration, new failure, missing report, PII,
install, commit, or push.

## Required report

Create `/tmp/restore-green-development-quality-gates-slice-017-report.md` with
contract matrix, per-app RED/GREEN, security/access audit, all gates,
full-suite comparison, rollback, and verifier handoff.

## Ready-to-run implementer prompt

```text
Implement ONLY slice 017. Restore Matrix, PDF generator, and sample-content
tests against current contracts; never weaken HTML escaping or permissions.
Stop above five semantic files, make all three apps green, run all gates/full
comparison, write the report, and STOP. No install, commit, or push.
```
