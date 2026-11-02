# S9: Map parity, cache correctness and release verification

## Identity and objective

Change: `add-specialty-team-tag-governance`. Tasks: 9.1-9.4 in
[../tasks.md](../tasks.md). Depends on accepted S5 and S8. Deliver the same visible
filter/default contract on the cached ward map and close cross-surface release
gates without operating on production.

## Read first

- [Shared execution/report contract](README.md), `AGENTS.md`,
  `PROJECT_CONTEXT.md`, repository coding standards.
- [Design D6-D8, migration and rollback](../design.md),
  [filtering](../specs/patient-tag-filtering/spec.md),
  [governance](../specs/team-tag-governance/spec.md),
  [audit](../specs/patient-tag-audit/spec.md).
- Accepted S1-S8 code; reports are supplementary, not required `/tmp` inputs.
- `apps/patients/views.py:WardPatientMapView`, S7/S8 shared services/components;
  `apps/core/utils/cache.py`, `management/commands/update_ward_mapping_cache.py`;
  full/partial map templates and `assets/js/ward_patient_map.js`.

## Requirements and evidence

- **R1:** Map uses shared ANY/ALL, manual/clear/default precedence, historical
  selection and explicit save/reapply behavior. Evidence: list/map parity
  matrix.
- **R2:** Live batched tag/association/policy overlay prevents warm-cache leaks
  and stale assignment filters. Evidence: member/outsider, revoke, reclassify,
  assign/remove/rename/archive tests without rebuilding the base cache.
- **R3:** Result totals match filtered rows; refresh, partial HTML and empty-ward
  controls retain effective filters. Evidence: totals/links/AJAX regression tests.
- **R4:** Existing map eligibility remains INPATIENT with ward; docs and release
  evidence distinguish empty results, invalid defaults and stale base data.
  Evidence: outpatient-zero/browser cases and complete integration gates.

## Allowed blast radius

- `apps/core/utils/cache.py`,
  `apps/core/management/commands/update_ward_mapping_cache.py`.
- `apps/patients/views.py` map orchestration; services `tag_filters.py`,
  `tag_projection.py`; new `services/ward_tag_overlay.py` if needed to keep
  bounded lookup/serialization responsibilities separate.
- `apps/patients/templates/patients/ward_patient_map.html`,
  `ward_patient_map_tree_only.html`; `templates/components/_tag_filter.html`,
  `_tag_selector.html`; `assets/js/ward_patient_map.js`, `tag-selector.js`.
- New `apps/patients/tests/test_ward_map_tag_filters.py`,
  `apps/core/tests/test_cache_tag_overlay.py`;
  existing `apps/core/tests/test_cache_utils.py`, `test_cache_tag_privacy.py`,
  patient tag navigation and visibility tests for full/partial regressions.
- `docs/performance/dashboard-cache.md`, `docs/patients/tags_management.md`
  map/filter-cache guidance only. Earlier catalogue, permission and audit docs
  remain their delivering slice's responsibility, not deferred work here.

No new statuses in the map, cache rebuild via GET, production cron/deploy changes,
Taggit dependency/table removal, broad permission rewrite or generated asset edits.

## Failing-before plan

Capture RED for filtered header totals staying global, cache missing a newly
added/removed association, and missing map multi-tag/default behavior. Current
metadata redaction and revoked-membership privacy must already pass S5: rerun
those warm-cache tests as regressions, not new RED claims. Verify each case
against main map HTML and the AJAX tree variant.

## Implementation constraints

Rehydrate catalogue data and assignments for only the map's bounded patient set;
avoid per-patient queries. Apply requester visibility before serialization and
shared filters; never leak metadata through hidden DOM attributes/dropdowns.
Refresh is a reload retaining query parameters, not a management-command call.
Use the same saved preference as the list and preserve explicit cleared state.
Do not let an outpatient match extend the map's population. Keep empty-ward
semantics explicit when counting returned wards and patients.

## Validation

Focused:

```bash
./scripts/test.sh apps.patients.tests.test_ward_map_tag_filters
./scripts/test.sh apps.core.tests.test_cache_tag_overlay
./scripts/test.sh apps.core.tests.test_cache_tag_privacy
./scripts/test.sh apps.core.tests.test_cache_utils
./scripts/test.sh apps.patients apps.accounts apps.events
npm run build
```

Release gates:

```bash
./scripts/test.sh
docker exec eqmd_dev python manage.py check
docker exec eqmd_dev python manage.py makemigrations --check --dry-run
openspec validate add-specialty-team-tag-governance --strict
git diff --check
```

Also run scoped Ruff/type checking and Markdown lint on every changed document
per `AGENTS.md`. Migration generation/checks do not authorize applying migrations
to a live database. Review evidence from all nine slices for migration ordering,
legacy identity preservation and privacy-reader coverage. Missing temporary
reports require reproducing evidence from accepted code, not guessing results.

Runtime evidence: desktop/mobile same selection on list/map, ANY/ALL toggle,
explicit save/clear/reapply, historical search, correct totals, and a warm-cache
permission change. Use fixtures, never real patient content in reports.

## Acceptance criteria

- [ ] R1: list/map share one selection/default contract and saved preference.
- [ ] R2: cache cannot delay tag privacy or assignment correctness.
- [ ] R3: totals and full/partial navigation reflect actual filtered results.
- [ ] R4: outpatient-zero/stale-data states and operational docs are accurate.
- [ ] Full tests, drift checks, scoped lint/types, build and spec/doc gates pass.
- [ ] No production deployment, data migration or destructive rollback occurred.

## Escalation and report

Stop `BLOCKED_NEEDS_DECISION` if eligibility changes, infrastructure operations,
unsafe downgrade or an undocumented reader is required. Report
`/tmp/eqmd-team-tags-slice-009-report.md` using the shared schema with R1-R4
matrix, files, RED/GREEN, command statuses, browser evidence, accumulated
migration/preflight results and the separate production approval requirement.

## Worker handoff

Implement only approved S9 from canonical artifacts and accepted S8 code.
Follow the shared contract. Do not update `tasks.md`, commit, push, merge, deploy
or archive. Mark this slice's checklist only after all verification. Return
`READY_FOR_REVIEW` with `REPORT_PATH` or `BLOCKED_NEEDS_DECISION` with evidence;
do not declare the change deployed.
