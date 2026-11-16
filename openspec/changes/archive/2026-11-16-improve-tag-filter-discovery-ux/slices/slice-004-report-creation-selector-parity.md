# TFUX S4 — Report-creation selector parity

## Identity

- Change: `improve-tag-filter-discovery-ux` (TFUX).
- Task: [tasks.md §4 / 4.1](../tasks.md#4-s4--preserve-report-creation-with-selector-parity).
- Dependency: S3 accepted and its actual catalogue/selector/history handoff at
  `/tmp/sirhosp-slice-TFUX-S3-report.md`.

## Objective

Deliver searchable explicit model discovery during report creation without
changing clinical content, selected model eligibility or intentional model
application behavior.

## Read First

- `AGENTS.md`, `PROJECT_CONTEXT.md`, `openspec/config.yaml` and coding standards.
- This change's `proposal.md`, `design.md` D1–D9 and `tasks.md`.
- This change's `verification.md` S4 and `specs/reports/spec.md`, including the
  MODIFIED name-discovery contract and creation-state baseline requirements.
- Accepted S1–S3 reports; inspect the actual S3 catalogue opt-in/controller
  isolation and reusable interfaces before modifying any shared file.
- Reports `views/report_views.py`, `services/template_discovery.py`,
  `templates/reports/report_create_form.html`, shared filters/results components,
  `assets/js/report-template-discovery.js`, S3 lookup endpoint and selector.
- Existing template selection/create/permissions tests, EasyMDE interaction
  helper patterns, Webpack config and earlier report verification artifacts.
- `.pi/skills/verify-eqmd/SKILL.md`.

## Requirements and Planned Evidence

- **R1:** Creation model q/tags/mode follow the same explicit normalized
  draft/dirty/Apply requirements as catalogue. Ordinary edits produce neither
  result replacement nor main navigation; one Apply uses template-selection
  JSON, and failure keeps honest prior results/draft/error. Evidence: network/
  result/payload assertions and real form-control tests.
- **R2:** Searchable/chip selection, bounded overlay, historical options,
  accessible targets/long-name behavior and native fallback match S3. Actual
  model results remain active public-or-own models only; tag catalogue lookup
  remains safe and independent of patient-record permission. Evidence: existing
  eligibility/privacy tests plus browser desktop/mobile/no-JS proof.
- **R3:** During every enhanced filter interaction, title, document date,
  EasyMDE content and independently selected model remain byte-for-byte or
  value-for-value unchanged. No filter control causes clinical POST, accidental
  model application or placeholder re-render. Evidence: before/after sentinels,
  main-document navigation and request log after every required action.
- **R4:** Successful applied result actions and Back/Forward follow S3 history
  semantics while preserving R3 state. Selected models outside current results
  remain visibly separate/count-excluded; revoked choices still fail and manual
  creation is possible after deliberate clear. Evidence: JSON/history tests and
  operator-managed selected-model scenarios.
- **R5:** No duplicate selector/controller initialization or repeated hidden
  tags occurs. Explicit model choice follows only the existing prefill flow.
  No-JS separate GET has no nested clinical form and warns to filter before
  editing; duplicate/update forms remain unchanged. Catalogue/patient S1–S3
  behavior remains green. Evidence: focused suites, no-JS and final regression
  matrix.

## Expected Blast Radius

Expected existing paths:

- Reports `views/report_views.py` or its narrowly scoped discovery view/context;
  template selection tests/fixtures and `services/template_discovery.py` only
  if actual JSON parity requires.
- `apps/reports/templates/reports/report_create_form.html` and shared filter/
  results components from S3.
- `assets/js/report-template-discovery.js` and accepted shared selector/host
  state/style files only where required for creation integration.
- Existing frontend build source wiring and generated assets via build only.
- Focused report selection/create/view tests and final regression tests.

Any shared-file edit must cite S3's delivered integration and include its
catalogue regression. No additional backend lookup or persistence should be
necessary; a genuinely missing response identity must be justified before
adding it. No patient implementation changes are expected in S4.

Sensitive/outside scope: no clinical models/events/migrations, placeholder/PDF
renderer, report permissions or final-submission changes, no template content
application redesign, no preference/global clear behavior, no duplicate/update
selector, no tag governance or global result-table work.

## Failing-Before Plan

1. RED view/DOM assertions for creation opt-in selector hooks, normalized draft
   status and explicit native Apply contract without nested forms.
2. Browser failing-before: typing q in creation still drives the old result
   controller; new normalized dirty/searchable selector behavior is absent;
   Back after catalogue-style history integration has no creation contract.
3. Add expected-safe regression sentinels before modifications. Existing content
   preservation, eligibility, revocation and no-nested-form tests may already be
   green and MUST be reported as guards rather than invented failing tests.
4. Exercise S3 component on the S3 baseline's creation page only as a reproducible
   missing-opt-in check; do not partially activate it to manufacture RED.

## Implementation Constraints

Follow repository engineering policy in `AGENTS.md` and preserve existing
conventions. Prefer the smallest correct change without speculative abstraction
or unrelated refactoring.

Consume S3's actual hooks and transport helpers. Do not duplicate catalogue
rendering/lookup logic or bind both catalogue and creation initialization paths.
Filter controls remain outside the clinical POST form and no discovery listener
may dispatch the selected-model's prefill change event.

Never derive clinical submission eligibility from current filter results; use
existing selected-model projection and full server validation. Historical
options and pending tag queries cannot change title/date/editor content. When
restoring filter history, never write clinical fields or overwrite current model
selection with an entry captured earlier.

No-JS preserves existing explicit GET navigation and warning; enhanced behavior
must not remove that fallback. Do not implement preference redesign or apply
the new discovery widget to duplicate/update forms.

## Validation

### Focused Validation

```bash
./scripts/test.sh apps.reports.tests.test_template_selection \
  apps.reports.tests.test_template_discovery \
  apps.reports.tests.test_template_views \
  apps.reports.tests.test_report_create_view \
  apps.reports.tests.test_template_tag_history
./scripts/test.sh apps.reports
./scripts/test.sh apps.patients.tests.test_tag_filters \
  apps.patients.tests.test_ward_map_tag_filters \
  apps.patients.tests.test_tag_lookup
npm run build
```

Verify JSON eligibility/identity and full server validation are unchanged for
outside-page models, inactive/private foreign models and manual creation.
Assert controls stay outside the clinical form and no repeated tag/filter hidden
fields leak into that POST. Check duplicate initialization listeners do not
double-fetch or duplicate chip/hidden values after history restore and repeated
options toggles.

### Project-Required Gates

Run all applicable `AGENTS.md`/coding-standards gates: full project test suite,
scoped Python checks, build, touched-Markdown lint, `git diff --check` and
strict OpenSpec validation on the final artifacts.

### Runtime / Verification Evidence

Follow `verification.md` S4 using real login/form/editor interactions:

1. Record initial title/date/EasyMDE value/current selected-model projection.
   Change them to unique sentinels before discovery interactions.
2. Exercise pending/revert/Apply q/tags/mode, ANY/ALL results, historical on/off,
   clear/reapply, applied badge removal, pagination and a controlled 503. After
   each, compare every clinical sentinel and selected ID exactly; assert zero
   clinical POSTs and unexpected navigations.
3. Apply A then B and use browser Back/Forward. Filter results/controls restore
   canonical A/B while clinical sentinels and selected model remain unchanged;
   no duplicate history request/push loop occurs.
4. Filter selected model outside results and verify its separate indicator/count.
   Test current valid, inactive/private revoked and explicitly cleared manual
   cases using operator-managed fixture/checkpoint transitions.
5. Verify keyboard/mobile/long-name geometry and a11y as in S3, then separately
   no-JS native Apply/pagination/warning/no nested forms. Intentionally choosing
   a model still uses only the pre-existing prefill selection workflow.
6. Run a final mini-matrix over catalogue, patient list and map plus console
   error check. Do not declare S3 guard checks as evidence alone for S4.

## Acceptance Criteria

- [ ] R1: Creation uses explicit searchable draft/Apply with honest async state.
- [ ] R2: Selector/accessibility/native parity holds without eligibility changes.
- [ ] R3: Every required interaction preserves all clinical/model sentinels and
      emits no clinical POST/unexpected navigation.
- [ ] R4: Back/Forward and outside/revoked/clear model cases pass without state
      substitution or duplicate history.
- [ ] R5: No duplicate initialization, no-JS and non-target flows remain intact;
      S1–S3 regressions and final OpenSpec validation pass.
- [ ] Full evidence/report ownership is ready for operator/archive decision, but
      this slice performs no archive itself.

## Escalation Conditions

Stop with `BLOCKED_NEEDS_DECISION` for any required clinical behavior/security/
persistence change, model-application ambiguity, missing clinical-preservation
proof, duplicate-controller conflict that needs redesign, new dependency or
material scope expansion. Missing operator fixtures/revocation checkpoints are
blockers, not permission to simulate successful clinical authorization.

## Evidence Report

Path: `/tmp/sirhosp-slice-TFUX-S4-report.md`.

Include status, requirement/evidence map, files, genuine RED versus pre-existing
regression guards, command exits, served identity, complete network/history and
clinical-sentinel proof, runtime run/manifest and limitations. List actual shared
interfaces now consumed by catalogue and creation and any residual known issues.
Do not update tasks, commit or archive as part of this report.

## Worker Handoff

```text
Implement only TFUX S4. Reconstruct fresh context from this contract and accepted
S1-S3 handoffs. Follow repository engineering policy. Produce failing-before
evidence, implement the smallest correct change, validate and write the report.
Do not update tasks.md, commit, push, merge, archive or release. If a decision
is required, stop with BLOCKED_NEEDS_DECISION and evidence. Otherwise finish
READY_FOR_REVIEW with REPORT_PATH=/tmp/sirhosp-slice-TFUX-S4-report.md.
```
