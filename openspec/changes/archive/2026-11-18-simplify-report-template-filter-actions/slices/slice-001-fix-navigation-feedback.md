# RTFA-S1 — AJAX-safe navigation feedback

## Identity and Objective

Change: simplify-report-template-filter-actions.
Task: [tasks.md 1.1](../tasks.md#1-truthful-navigation-feedback).
Dependency: explicit implementation approval.
Make shipped discovery actions usable without a false 15-second page mask,
while keeping real navigation feedback and one overlay per document.

## Read First

Read AGENTS.md, PROJECT_CONTEXT.md, openspec/config.yaml and
docs/workflows/coding-standards.md, then:

- ../proposal.md, ../design.md D1-D2/D6-D7 and ../verification.md.
- ../specs/page-navigation-feedback/spec.md.
- assets/js/page-loading.js and webpack.config.js.
- templates/base.html, templates/base_app.html.
- assets/js/report-template-discovery.js catalogue click/fetch handlers.
- apps/core/templatetags/static_assets.py and its tests, read-only behavior.
- .pi/skills/verify-eqmd/SKILL.md for runtime/fixture safety.
- Diagnostic report if available; its core reproduction is also in the design.

## Requirements and Planned Evidence

- **R1:** Intercepted click/submit cannot trigger a global mask, even when
  cancellation occurs after an earlier listener scheduled display.
  Evidence: deterministic event/timer harness and real Chrome integration.
- **R2:** Success/failure/no-op/lookup/pagination leave in-place UI usable
  without the navigation timeout. Evidence: controller-plus-global browser cases.
- **R3:** Real eligible navigation retains its feedback and existing opt-outs;
  load/pageshow clears it. Evidence: harness plus real disposable navigation.
- **R4:** One overlay ID on inherited pages; safe without an overlay.
  Evidence: Django HTML counts and harness.
- **R5:** Current built loading code is requested through the existing
  content-versioned main-bundle URL. Evidence: HTML/version helper and asset hashes.
- **R6:** Catalogue/creation scopes, patient surfaces and all read/write
  boundaries remain unchanged. Evidence: regressions and snapshot/browser smoke.

## Expected Blast Radius

Approved existing edits:

- assets/js/page-loading.js: cancellation and delayed-feedback lifecycle only.
- templates/base_app.html: remove its redundant overlay, no layout redesign.
- templates/base.html: version main-bundle.js; retain the base overlay.
- apps/core/tests/test_static_assets.py: only relevant versioned-bundle assertions.

Approved new paths:

- apps/core/tests/test_page_navigation_loading.py.
- apps/core/tests/page_navigation_loading_harness.cjs.
- apps/core/tests/page_navigation_loading_fixtures.py, only if needed.

Generated Webpack output is verification output, not hand-edited source.
Do not modify catalogue action scopes, shared filter markup, discovery
controllers, creation forms, parser/policy, cache, clinical models or endpoints.
Any unlisted/material expansion requires operator approval with evidence.

## Failing-Before Plan

Use RED -> GREEN -> REFACTOR. New DOM/event tests must fail because current
page-loading.js ignores defaultPrevented and inherits duplicate overlay IDs.
Use fake timers to expose late/deferred callbacks deterministically.

Browser before proof must show a real successful catalogue fragment hidden by
the global mask; fixture/auth/asset failures are not valid RED. Also pin real
navigation so a blanket loading disable cannot pass.

## Implementation Constraints

Follow repository engineering policy and preserve existing conventions.
Do not shorten the timeout to conceal the issue or make AJAX simulate page load.
Do not stop propagation as a workaround or change who owns filter requests.
Keep the loader optional and preserve current opt-outs and native navigation.
New modules/functions meet canonical limits; legacy base_app edits are bounded
deletion only. No generic loading framework or service-worker rewrite.

## Validation

Focused command:

```bash
./scripts/test.sh apps.core.tests.test_page_navigation_loading \
  apps.core.tests.test_static_assets \
  apps.reports.tests.test_template_catalogue_s3 \
  apps.reports.tests.test_template_creation_s4 \
  apps.patients.tests.test_patient_list_filter_actions \
  apps.patients.tests.test_ward_map_filter_actions
node apps/core/tests/page_navigation_loading_harness.cjs
npm run build
```

Run scoped project lint/type/format and Markdown/OpenSpec gates.
Node absence inside the container does not waive the explicit host harness.
Run verification.md's S1 matrix with actual compiled global and page scripts.
Label TestCase routing versus live dev; compare source/built hashes.
No shared fixture, migration, package install, generator, restart or remount.

## Acceptance Criteria

- [ ] R1: Early/late cancellation prevents delayed global feedback.
- [ ] R2: Successful/failed in-place actions never wait behind a page mask.
- [ ] R3: Genuine document navigation and current opt-outs still work.
- [ ] R4: Unique overlay and safe no-overlay behavior are proven.
- [ ] R5: Build and cache-safe main-bundle delivery are proven.
- [ ] R6: Protected surfaces and snapshots remain unchanged.

## Escalation and Handoff

Return BLOCKED_NEEDS_DECISION for contradictions, new product/architecture
decisions, unlisted/material scope, public compatibility breaks, persistence,
security/privacy/clinical implications or inability to meet the contract.

Write /tmp/sirhosp-slice-RTFA-S1-report.md with R-to-evidence mapping,
changed paths, RED/GREEN, commands/exit codes, runtime/asset identity,
fixture ownership/cleanup, baselines and unresolved limitations.

Implement only this approved slice. Reconstruct fresh context from artifacts.
Do not update tasks.md, sync specs, commit, push, merge, archive or start S2.
Stop with READY_FOR_REVIEW and REPORT_PATH, or BLOCKED_NEEDS_DECISION.
