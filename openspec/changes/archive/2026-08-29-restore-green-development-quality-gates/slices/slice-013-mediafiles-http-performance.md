# Slice 013 - Mediafiles HTTP, Integration, and Performance

## Handoff for a zero-context implementer

Read all standard artifacts, reports 001-012, approved media foundation
contract map, current media URLs/views/templates/permissions, and listed tests.
Start only after slice 012 approval.

This slice covers remaining mediafiles view, template, integration, performance,
and UAT failures after foundational fixtures are green.

## Mandatory protocol

Run each target before edits and classify lifecycle/setup versus functional
failures. Build an HTTP/permission/performance scenario matrix. Existing
failures are RED; production changes need spec proof and regression tests. Do
not relax access controls, upload limits, query/time thresholds, or UAT
assertions. Entire mediafiles app must end green, full comparison, report, stop.

## Objective

Restore end-to-end mediafiles behavior tests and establish a green complete
mediafiles app baseline.

## Requirements

- **R1:** views reach intended permission and response paths using supported
  fixtures.
- **R2:** templates/integration preserve secure media rendering and access.
- **R3:** performance tests retain explicit thresholds and realistic synthetic
  fixtures.
- **R4:** UAT scenarios use current APIs without bypassing business behavior.
- **R5:** `./scripts/test.sh apps.mediafiles` exits 0.

## Expected files

- `apps/mediafiles/tests/test_views.py`
- `apps/mediafiles/tests/test_templates.py`
- `apps/mediafiles/tests/test_integration.py`
- `apps/mediafiles/tests/test_performance.py`
- `apps/mediafiles/tests/test_uat_scenarios.py`

Production URL/view/template candidates require RED/spec proof and planner
approval. More than six semantic files requires a split.

## TDD and inspections

```bash
rg -n \
  "status_code|assertNumQueries|performance|permission|Hospital|birth_date" \
  apps/mediafiles/tests/test_views.py \
  apps/mediafiles/tests/test_templates.py \
  apps/mediafiles/tests/test_integration.py \
  apps/mediafiles/tests/test_performance.py \
  apps/mediafiles/tests/test_uat_scenarios.py
rg -n "permission|required|login|media" apps/mediafiles/urls.py apps/mediafiles/views.py
find apps/mediafiles/templates -type f | sort
git diff --check
git diff --stat
```

## Verification commands

```bash
./scripts/test.sh apps.mediafiles.tests.test_views
./scripts/test.sh apps.mediafiles.tests.test_templates
./scripts/test.sh apps.mediafiles.tests.test_integration
./scripts/test.sh apps.mediafiles.tests.test_performance
./scripts/test.sh apps.mediafiles.tests.test_uat_scenarios
./scripts/test.sh apps.mediafiles
docker exec eqmd_dev ruff check <CHANGED_PYTHON_FILES>
docker exec eqmd_dev ruff format --check <CHANGED_PYTHON_FILES>
./scripts/typecheck.sh <CHANGED_PRODUCTION_PYTHON_FILES>
docker exec eqmd_dev python manage.py check
./scripts/test.sh
openspec validate restore-green-development-quality-gates --strict
markdownlint-cli2 \
  openspec/changes/restore-green-development-quality-gates/tasks.md \
  /tmp/restore-green-development-quality-gates-slice-013-report.md
```

## Binary criteria

- [ ] Five target modules and full mediafiles app are green.
- [ ] Permissions/upload limits/performance thresholds remain strict.
- [ ] Any production fix has RED/spec proof and rollback.
- [ ] No more than six semantic files change without a split.
- [ ] Full suite has no new unexplained failure.

## Automatic `INCOMPLETE`

Any mediafiles failure, relaxed security/threshold, production edit without
proof, too many files, generated static edit, real media/PII, new failure,
missing report, install, commit, or push.

## Required report

Create `/tmp/restore-green-development-quality-gates-slice-013-report.md` with
scenario matrix, RED/GREEN, threshold/security audit, app/full results,
production rollback if any, and verifier handoff.

## Ready-to-run implementer prompt

```text
Implement ONLY slice 013 after media foundations are green. Restore media view,
template, integration, performance, and UAT contracts without relaxing
security or thresholds. Require the full mediafiles app green, stop for planner
split above six semantic files, run full comparison, write the report, and
STOP. No real data, install, commit, or push.
```
