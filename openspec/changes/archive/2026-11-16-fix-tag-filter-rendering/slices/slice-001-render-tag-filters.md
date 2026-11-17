# FIX1 — Correct shared tag-filter rendering

## Identity and Objective

Change `fix-tag-filter-rendering`, task 1.1. One vertical corrective slice:
usable first-load lookup, readable controls and clean report markup.

## Read First

Read AGENTS.md, canonical coding standards, this change's proposal/design/specs,
and the archived improve-tag-filter-discovery-ux design. Inspect current selector
markup, existing selector JS hooks, host controllers and rendered-template tests.
Preserve current explicit Apply, draft/applied semantics and all authorization.

## Requirements and Evidence

- R1: Found rows are visible and clickable on independent first entry even after
  legacy URL caching. Evidence: asset-token tests and Chrome legacy/current run.
- R2: Panels anchor under the input; readable responsive rows and action footers.
  Evidence: rendered structure plus 1440/390/320 browser geometry/hit tests.
- R3: No raw comments in catalogue/creation. Evidence: rendered-template tests.
- R4: No filter/auth/clinical behavior changes. Evidence: patients/reports/core
  regressions, existing JS harnesses and creation browser sentinel.

## Allowed Paths

- apps/core/templatetags/static_assets.py (new).
- apps/core/tests/test_static_assets.py (new).
- apps/patients/tests/test_tag_filter_rendering.py (new).
- templates/base.html.
- apps/patients/templates/components/\_tag_filter.html.
- apps/patients/templates/components/\_tag_selector.html.
- apps/patients/templates/patients/patient_list.html.
- apps/patients/templates/patients/ward_patient_map.html.
- apps/reports/templates/components/\_report_template_filters.html.
- apps/reports/templates/components/\_report_template_tag_selector.html.
- apps/reports/templates/reports/reporttemplate_list.html.
- apps/reports/templates/reports/report_create_form.html.
- assets/scss/\_tag_filters.scss (new).
- assets/scss/main.scss (import only; existing selector styles remain).
- Generated static outputs from npm run build, not hand-edited.
- /tmp/eqmd-tag-filter-rendering/ for verification deliverables.

No database, permission, patient data, renderer or host-controller refactor.

## Failing-Before

RED: add and run isolated template tests for raw comments, cache-safe script
URLs and direct input anchoring before fixing them. Reproduce an old selector
against new panel markup in Chrome; source-string tests alone are insufficient.

## Validation

Use eqmd_dev only for Python. If /app is a different checkout, copy this
worktree into a dedicated container /tmp directory and execute the same
PostgreSQL test runner there with --keepdb --noinput and config.test_settings.
Do not silently patch the shared checkout to make tests pass.

Focused tests: apps.core.tests.test_static_assets and
apps.patients.tests.test_tag_filter_rendering. Then run selector-template,
tag-filter, reports and relevant core regressions, npm run build and existing
host JS harnesses. Follow AGENTS.md project gates and Markdown lint.

Runtime: official verify-eqmd fixture identity/cleanup; fresh browser per surface,
legacy-cache case, result visibility and hit target, Escape/reopen/keyboard,
responsive alignment, no-JS and report-creation sentinels. Label workspace preview
versus deployed evidence explicitly.

## Acceptance Criteria

- [x] R1: Versioned assets and visible first-load matches proven.
- [x] R2: Aligned desktop/mobile controls and input-anchored bounded panel proven.
- [x] R3: Catalogue/creation contain no raw developer comments.
- [x] R4: Regression tests and content preservation pass.
- [x] Gate results, limitations and exact fixture cleanup are recorded.

Completion evidence and validation limits: [verification.md](../verification.md).

## Escalation and Handoff

Stop with BLOCKED_NEEDS_DECISION on new product/security/persistence decisions,
material scope expansion or inability to validate this checkout. Do not edit
unlisted application paths without approval. No commit or additional slice.

Write /tmp/sirhosp-slice-FIX1-report.md with requirements-to-evidence, failing
and passing outcomes, paths, commands/exit statuses, runtime limits and cleanup.
Finish READY_FOR_REVIEW only with evidence; otherwise report the exact blocker.
