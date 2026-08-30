# Slice 015 - PDF Forms Admin, HTTP, and Security

## Handoff for a zero-context implementer

Read standard artifacts, reports 001-014, the approved PDF domain contract
table, active PDF-form changes, current admin/views/URLs/permissions/template
tags/commands, and listed tests. Start only after slice 014 approval.

Initial failures include outdated URL counts/types, wrong mock targets,
validation setup, permission expectations, context keys, template escaping, and
management-command streams.

## Mandatory protocol

Baseline target modules and map routes/permissions/mocks before edits. Existing
failures are RED. Preserve permission denial and sanitization behavior; a `302`
from lifecycle is setup, not permission success. Production fixes require
active-spec proof and RED. Stop above eight semantic files. Entire `pdf_forms`
app must finish green, full comparison, report, stop.

## Objective

Restore PDF forms admin, HTTP, permission, security, command, URL, and template
contracts and establish a green complete app baseline.

## Requirements

- **R1:** tests target current import paths, UUID converters, and route names.
- **R2:** permission-denied scenarios reach and enforce the intended check.
- **R3:** admin/command tests use valid current model fixtures and streams.
- **R4:** template/security assertions remain strict and correctly escaped.
- **R5:** complete `apps.pdf_forms` suite exits 0.

## Expected files

- `apps/pdf_forms/tests/test_admin.py`
- `apps/pdf_forms/tests/test_views.py`
- `apps/pdf_forms/tests/test_permissions.py`
- `apps/pdf_forms/tests/test_security.py`
- `apps/pdf_forms/tests/test_template_tags.py`
- `apps/pdf_forms/tests/test_management_commands.py`
- `apps/pdf_forms/tests/test_urls.py`
- `apps/pdf_forms/tests/test_national_forms.py`

Production candidates require RED/spec proof. More than eight semantic files or
any active-feature conflict requires planner split.

## TDD and inspections

```bash
rg -n \
  "patch\(|reverse\(|PermissionDenied|status_code|context" \
  apps/pdf_forms/tests/test_admin.py apps/pdf_forms/tests/test_views.py \
  apps/pdf_forms/tests/test_permissions.py \
  apps/pdf_forms/tests/test_security.py \
  apps/pdf_forms/tests/test_template_tags.py \
  apps/pdf_forms/tests/test_management_commands.py \
  apps/pdf_forms/tests/test_urls.py apps/pdf_forms/tests/test_national_forms.py
rg -n "path\(|permission|required|def .*api|convert_from_path" \
  apps/pdf_forms/urls.py apps/pdf_forms/admin.py apps/pdf_forms/views \
  apps/pdf_forms/management 2>/dev/null
git diff --check
git diff --stat
```

## Verification commands

```bash
./scripts/test.sh apps.pdf_forms.tests.test_admin
./scripts/test.sh apps.pdf_forms.tests.test_views
./scripts/test.sh apps.pdf_forms.tests.test_permissions \
  apps.pdf_forms.tests.test_security
./scripts/test.sh apps.pdf_forms.tests.test_template_tags \
  apps.pdf_forms.tests.test_management_commands
./scripts/test.sh apps.pdf_forms.tests.test_urls \
  apps.pdf_forms.tests.test_national_forms
./scripts/test.sh apps.pdf_forms
docker exec eqmd_dev ruff check <CHANGED_PYTHON_FILES>
docker exec eqmd_dev ruff format --check <CHANGED_PYTHON_FILES>
./scripts/typecheck.sh <CHANGED_PRODUCTION_PYTHON_FILES>
docker exec eqmd_dev python manage.py check
./scripts/test.sh
openspec validate restore-green-development-quality-gates --strict
markdownlint-cli2 \
  openspec/changes/restore-green-development-quality-gates/tasks.md \
  /tmp/restore-green-development-quality-gates-slice-015-report.md
```

## Binary criteria

- [ ] Eight target modules and full PDF forms app are green.
- [ ] Permission tests reach intended checks and remain strict.
- [ ] Mock/URL/context contracts match current code/specs.
- [ ] No active feature or more than eight semantic files without split.
- [ ] No new unexplained full-suite failure exists.

## Automatic `INCOMPLETE`

Any PDF app failure, relaxed permission/security, wrong mock hidden by deletion,
early active feature, excessive files, new failure, missing report, real PII,
install, commit, or push.

## Required report

Create `/tmp/restore-green-development-quality-gates-slice-015-report.md` with
route/permission/mock matrix, RED/GREEN, app/full results, changed-production
rollback, scope audit, and verifier handoff.

## Ready-to-run implementer prompt

```text
Implement ONLY slice 015 after PDF domain foundations are green. Restore admin,
HTTP, permission, security, command, URL, and template tests contract-first;
require the full pdf_forms app green and preserve strict access/security. Stop
above eight semantic files or on active-spec conflict. Run all gates, write the
report, and STOP. No install, commit, or push.
```
