# Slice 014 - PDF Forms Domain Foundations

## Handoff for a zero-context implementer

Read standard artifacts and reports 001-013, all active PDF-form OpenSpec
changes/specs, current models/services/mapping code, and listed tests. Start
after mediafiles is approved green.

Initial failures cover required JSON/PDF validation, form-data sanitization,
field type compatibility, linked-field map keys, choice counts, overlay
validation, and service concurrency. Active PDF-form feature changes make
contract inspection mandatory.

## Mandatory protocol

Baseline each target and produce a contract table citing active specs/models.
Existing failures are RED. Do not make tests match implementation by default.
Production fixes require behavior RED and current-spec proof. Do not implement
active duplication/procedure features early. Stop for planner split if more
than six semantic files are needed. Targets green, full comparison, report,
stop.

## Objective

Restore PDF forms domain-level model, service, mapping, linked-field, and
sanitization contracts before HTTP/admin repair.

## Requirements

- **R1:** model validation matches current required/optional field contracts.
- **R2:** sanitization preserves security properties and intended `None`/empty
  semantics.
- **R3:** mapping, linked-field keys, choices, and overlay validation follow
  active specs.
- **R4:** service/concurrency tests remain deterministic on PostgreSQL.
- **R5:** no active PDF feature is implemented ahead of its change.

## Expected files

- `apps/pdf_forms/tests/test_models.py`
- `apps/pdf_forms/tests/test_services.py`
- `apps/pdf_forms/tests/test_field_mapping.py`
- `apps/pdf_forms/tests/test_linked_fields.py`

Production model/service/mapping candidates require RED/spec proof. No migration
or more than six semantic files without planner split.

## TDD and inspections

```bash
rg -n "form_data|sanitize|linked|choices|compatibility|validate|concurrent" \
  apps/pdf_forms/tests/test_models.py \
  apps/pdf_forms/tests/test_services.py \
  apps/pdf_forms/tests/test_field_mapping.py \
  apps/pdf_forms/tests/test_linked_fields.py
rg -n "Requirement:|form_data|linked|duplication|procedure" \
  openspec/changes/*pdf* openspec/specs 2>/dev/null | head -240
rg -n "def (sanitize|validate|build_linked|generate)|class PDF" apps/pdf_forms
git diff --check
git diff --stat
```

## Verification commands

```bash
./scripts/test.sh apps.pdf_forms.tests.test_models
./scripts/test.sh apps.pdf_forms.tests.test_services
./scripts/test.sh apps.pdf_forms.tests.test_field_mapping
./scripts/test.sh apps.pdf_forms.tests.test_linked_fields
docker exec eqmd_dev ruff check <CHANGED_PYTHON_FILES>
docker exec eqmd_dev ruff format --check <CHANGED_PYTHON_FILES>
./scripts/typecheck.sh <CHANGED_PRODUCTION_PYTHON_FILES>
docker exec eqmd_dev python manage.py check
docker exec eqmd_dev python manage.py makemigrations --check --dry-run
./scripts/test.sh
openspec validate restore-green-development-quality-gates --strict
markdownlint-cli2 \
  openspec/changes/restore-green-development-quality-gates/tasks.md \
  /tmp/restore-green-development-quality-gates-slice-014-report.md
```

## Binary criteria

- [ ] Four target modules are green.
- [ ] Contract table cites active specs for changed behavior/assertions.
- [ ] Sanitization/security assertions are not weakened.
- [ ] No early active feature, migration, or broad refactor exists.
- [ ] No new unexplained full-suite failure exists.

## Automatic `INCOMPLETE`

Ambiguous/active spec conflict, target red, weakened sanitization, early feature,
more than six semantic files, migration, new failure, missing report, PII,
install, commit, or push.

## Required report

Create `/tmp/restore-green-development-quality-gates-slice-014-report.md` with
contract table, RED/GREEN, security/mapping decisions, gates, full comparison,
rollback, and verifier handoff.

## Ready-to-run implementer prompt

```text
Implement ONLY slice 014. Resolve PDF domain/model/service/mapping failures
against active specs, never by assuming current code or legacy tests are right.
Preserve sanitization/security, do not implement active PDF features early,
stop above six semantic files, make all targets green, run full comparison,
write the report, and STOP. No install, commit, or push.
```
