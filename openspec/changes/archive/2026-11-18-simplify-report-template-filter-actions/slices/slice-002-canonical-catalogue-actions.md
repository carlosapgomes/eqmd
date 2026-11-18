# RTFA-S2 — Canonical catalogue filters

## Identity and Objective

Change: simplify-report-template-filter-actions.
Task: [tasks.md 2.1](../tasks.md#2-canonical-catalogue-actions).
Dependency: accepted RTFA-S1 plus explicit S2 implementation approval.
Users can apply, truly clear or restore catalogue filters with a clean,
consistent UI, without changing report creation or stored preferences.

## Read First

Read AGENTS.md, PROJECT_CONTEXT.md, openspec/config.yaml and canonical coding
standards, then proposal.md, design.md D3-D7, verification.md and both deltas.
Read RTFA-S1's report and inspect its accepted code; do not infer it is complete.

Relevant source:

- apps/reports/views/template_views.py and apps/reports/urls.py.
- apps/reports/services/template_discovery.py.
- apps/accounts/services/tag_preferences.py.
- apps/patients/services/tag_filters.py and current list/map action services.
- apps/reports/templates/components/\_report_template_filters.html.
- apps/reports/templates/reports/reporttemplate_list.html and results partial.
- assets/js/report-template-discovery.js: distinguish both controllers.
- assets/js/report-catalogue-filter-form.js, assets/js/tag-selector.js.
- Existing S3/S4 tests/harness, discovery tests and creation template.
- apps/reports/tests/test_template_selection.py and test_report_create_view.py.
- .pi/skills/verify-eqmd/SKILL.md for safety.

## Requirements and Planned Evidence

- **R1:** One left-aligned wrapping bar; read-only summary and single empty
  recovery reference. Evidence: real rendered counts, keyboard and three widths.
- **R2:** Clear-all fresh manual/ANY URL drops name/tags/options/page/fragment;
  reload stays empty without changing eligibility/default storage.
  Evidence: rendered href/follow tests and saved-X browser snapshots.
- **R3:** Restore preserves applied name/historical option, restores shared
  tags/mode and discards pending drafts. Evidence: Ana versus pending Bruno,
  full GET and immediate no-request Apply.
- **R4:** Restore availability follows resolved context initially and after
  AJAX/history changes, including saved-empty. Evidence: state matrix and
  automatic-X -> AJAX-manual-Y -> visible restore.
- **R5:** Canonical links navigate natively, with or without JS; they abort
  stale fragment work and reset controls cleanly. Evidence: delayed-response,
  native empty/default cases and Back/Forward.
- **R6:** Ordinary AJAX Apply/pagination, late edits and lookup-only history
  retain current behavior. Evidence: existing and new harness/browser cases.
- **R7:** Legacy tag-only URLs preserve scopes; errors, visibility and generic
  warnings stay safe, including readers without patient permission.
  Evidence: existing discovery tests and dedicated negative assertions.
- **R8:** Creation remains in-place and preserves selected model/title/date/
  EasyMDE and authorization. Evidence: S4 plus real editor smoke.
- **R9:** Single controller, bounded legacy edits, real built assets and no
  preference/clinical mutation. Evidence: diff, build, snapshots and cleanup.

## Expected Blast Radius

Approved new paths:

- apps/reports/services/template_catalogue_filter_actions.py.
- apps/reports/views/template_catalogue_filters.py.
- apps/reports/tests/test_template_catalogue_filter_actions.py.
- apps/reports/tests/catalogue_filter_action_fixtures.py, if needed.
- apps/reports/tests/catalogue_filter_actions_harness.cjs.

Approved existing edits:

- apps/reports/urls.py: only existing catalogue route to inherited adapter.
- apps/reports/templates/reports/reporttemplate_list.html.
- apps/reports/templates/components/\_report_template_filters.html:
  explicit catalogue opt-in; creation/default branch unchanged.
- apps/reports/templates/reports/partials/\_reporttemplate_results.html.
- assets/js/report-template-discovery.js: D4-D5 bounded catalogue-only bridge.
- apps/reports/tests/test_template_catalogue_s3.py and
  apps/reports/tests/test_template_discovery.py: only obsolete catalogue
  assertion updates, not feature-matrix growth or weakened coverage.

Keep template_views.py and initializeSelection read-only. Do not change
report creation, shared selector/host JS, accounts/preferences, parser/policy,
models, selection JSON endpoints, patient list/map, base loading fixed by S1
or Webpack configuration without escalation. No new dependency or CSS is needed.

## Failing-Before Plan

Use RED -> GREEN -> REFACTOR with genuine saved X/ALL, manual Y and untagged
models. Pin old scoped clear retaining name, stale chips/mode after restore,
Apply undoing restore, unconditional restore and repeated recovery controls.
Pin that AJAX Apply currently cannot supply new conditional toolbar metadata.

Add a harness using the actual new catalogue hooks, not only the old S3
tag-scoped stub. Browser before must reproduce real UI defects, not an absent
test symbol or unhealthy fixture. R1-R5 need direct failing-before proof.

## Implementation Constraints

Follow repository engineering policy; implement design D3-D5, not a new client
state machine. Use native GET for canonical clear/restore and consume resolved
DiscoveryState once in a typed service. Preserve compatible hooks; never let
legacy link reconciliation rewrite clear-all back into tag-only clear.

The 1,575-line JS controller receives at most 40 added non-comment executable
lines, all in initializeDiscovery/local helpers. No initializeSelection edits
or competing catalogue controller. New modules stay below 300 lines and
functions at most 40. Legacy tests/harness stay bounded as documented.
If that is insufficient, stop with a split proposal rather than expanding.

A hidden restore anchor is allowed only if unavailable to sight, keyboard and
assistive actions. Refresh its server-derived visibility after every applicable
fragment/popstate; do not infer saved/default availability from draft tags.
Cancelling in-flight work must prevent stale URL/history changes during native
navigation and subsequent Back/Forward.

## Validation

Focused command:

```bash
./scripts/test.sh apps.reports.tests.test_template_catalogue_filter_actions \
  apps.reports.tests.test_template_catalogue_s3 \
  apps.reports.tests.test_template_discovery \
  apps.reports.tests.test_template_creation_s4 \
  apps.reports.tests.test_template_selection \
  apps.reports.tests.test_report_create_view \
  apps.reports.tests.test_template_views \
  apps.accounts.tests.test_tag_preferences \
  apps.core.tests.test_page_navigation_loading \
  apps.patients.tests.test_patient_list_filter_actions \
  apps.patients.tests.test_ward_map_filter_actions
node apps/reports/tests/catalogue_filter_actions_harness.cjs
npm run build
```

Run project-required scoped checks and verification.md's S2 matrix.
Existing Node skips require host execution of affected legacy scenarios too.
Show that tests cover real catalogue opt-in and creation isolation, not only a
passing legacy branch. Use the actual built/global scripts in Chrome.
Record all GET/preference/clinical invariants and exact-owner fixture cleanup.

## Acceptance Criteria

- [ ] R1: One aligned action bar, accessible draft controls and read-only summary.
- [ ] R2: True clear-all and manual-empty reload work under unchanged eligibility.
- [ ] R3: Applied name survives restore; pending controls do not undo it.
- [ ] R4: Restore visibility is correct initially and after AJAX/history updates.
- [ ] R5: Native navigation, no-JS, stale-request and browser-history cases pass.
- [ ] R6: Ordinary draft/Apply/pagination/lookup behavior remains intact.
- [ ] R7: Legacy URLs, validation and privacy gates pass.
- [ ] R8: Creation editor, selected model and authorization remain unchanged.
- [ ] R9: Bounds, build identity, snapshots and cleanup are recorded.

## Escalation and Handoff

Return BLOCKED_NEEDS_DECISION for contradictions, a new behavior/architecture
choice, material/unlisted expansion, compatibility/persistence changes or new
security/privacy/clinical implications. Missing fixtures do not authorize
shared profiles/cache writes, migrations, generator execution or remounts.

Write /tmp/sirhosp-slice-RTFA-S2-report.md with R-to-evidence mapping,
changed paths, RED/GREEN, commands/exit codes, runtime/asset identity, fixture
ownership/cleanup, baselines, scope expansion decisions and limitations.

Implement only this approved slice. Reconstruct fresh context from artifacts.
Do not update tasks.md, sync specs, commit, push, merge, archive or start more work.
Stop with READY_FOR_REVIEW and REPORT_PATH, or BLOCKED_NEEDS_DECISION.
