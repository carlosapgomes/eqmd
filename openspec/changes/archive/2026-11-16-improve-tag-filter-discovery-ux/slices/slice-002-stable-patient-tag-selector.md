# TFUX S2 — Stable patient/map tag selector

## Identity

- Change: `improve-tag-filter-discovery-ux` (TFUX).
- Task: [tasks.md §2 / 2.1](../tasks.md#2-s2--stabilize-patientmap-explicit-selection).
- Dependency: S1 accepted, including `/tmp/sirhosp-slice-TFUX-S1-report.md`.

## Objective

Make the existing searchable patient/map selector spatially stable, accessible
and explicitly applied, with honest draft-versus-applied state across every
patient/map predicate.

## Read First

- `AGENTS.md`, `PROJECT_CONTEXT.md`, `openspec/config.yaml` and coding standards.
- This change's `proposal.md`, `design.md` D1–D5/D7–D9 and `tasks.md`.
- This change's `verification.md`, especially S2 measurements and interactions.
- This change's `specs/patient-tag-filtering/spec.md`; baseline
  `openspec/specs/patient-tag-filtering/spec.md` for unchanged matching/history.
- Accepted S1 report and its actual shared wording/context handoff.
- `apps/patients/templates/components/_tag_selector.html`, patient list/map
  templates, `assets/js/tag-selector.js`, `assets/scss/main.scss`,
  `assets/index.js`, `webpack.config.js` and `package.json`.
- Patient GET/filter helpers in `apps/patients/services/tag_filters.py` and
  view context only as needed; matching/visibility services are read-only here.
- Existing selector/filter/ward-map/preference tests and generated build paths.
- `.pi/skills/verify-eqmd/SKILL.md`.

## Requirements and Planned Evidence

- **R1:** With enhancement, normalized draft values for list q/status/tags/mode
  and map q/ward/tags/mode/show-empty remain unapplied until text-labelled
  Aplicar filtros. Reverting draft values clears dirty; Apply's full GET retains
  canonical repeated tags/manual origin/other predicates. Evidence: DOM
  assertions, browser request/result matrix and existing URL tests.
- **R2:** Ordinary changes never submit implicitly. In particular, show-empty
  cannot call `form.submit()` or commit an unrelated draft. Existing scoped
  links continue using server-derived last-applied GET state and never include
  uncommitted form B. After full navigation, controls reflect the newly applied
  server state rather than claiming B was applied. Evidence: browser/network
  tests before and after.
- **R3:** Option results occupy a bounded anchored scrolling overlay. Focus and
  outside/Escape close/reopen behavior preserves terms/results/selection, and
  loading options cannot shift card/Apply geometry. Existing keyboard, inert
  row, inert-to-active removal and live announcements remain. Evidence:
  measured DOM rectangles/heights and real-browser keyboard/mobile scenarios.
- **R4:** Filter-editor chips/removal controls use neutral readable foreground,
  specific accessible names, long-name wrapping and measured 24/44 px hit areas.
  Errors preserve current selections/applied state; no unrelated result badge
  styling changes. Evidence: computed CSS/contrast measurement and 320/390 px
  overflow/target assertions.
- **R5:** Existing ANY/ALL, manual/saved/principal/none defaults, historical
  lookup, legacy URLs, preference save, privacy, filtered totals and native
  no-JS repeated-tag contract remain intact. Evidence: focused regressions and
  S2 runtime no-JS/default/historical scenarios.

## Expected Blast Radius

Expected existing paths:

- This change's already-touched patient templates/shared label contract.
- `apps/patients/templates/components/_tag_selector.html`.
- Patient list/map page script blocks and applicable filter partials.
- `assets/js/tag-selector.js`, `assets/index.js` and `webpack.config.js` only
  if a new source entry needs wiring.
- `assets/scss/main.scss` or one newly scoped selector stylesheet imported by
  the existing source build.
- Focused patient selector/filter/ward-map/preference tests.

An additional narrowly scoped `assets/js/patient-filter-form.js` (or similarly
named existing-host module) is approved only if needed for normalized host-form
state; expose actual attributes/events in the handoff. A focused test fixture
or evidence-only mock is allowed under the existing test conventions, not a new
runtime dependency. Generated Webpack outputs are allowed only through build;
never edit them directly.

Sensitive/outside scope: no report controller/template implementation yet, no
schema, matching/authorization/preference-precedence changes, no global
clear-all redesign, no patient association mutation and no broad table/layout
refactor. Preserve S1 recovery/language.

## Failing-Before Plan

1. RED DOM/view assertions for the new dirty-host hooks and visible scoped
   status, without weakening existing native form assertions.
2. Reproduce in browser: selecting/changing form controls has no pending text,
   show-empty submits immediately, opening/loading real options expands the host
   card and populated results do not reopen by simple focus after Escape.
3. Measure undersized chip-close target and text contrast before edits; capture
   long-name/320 px failure safely with approved fixtures.
4. Convert those reproductions into persistent postconditions. Existing keyboard,
   privacy or preference behaviors that are already green are guards, not RED.

## Implementation Constraints

Follow repository engineering policy in `AGENTS.md` and preserve existing
conventions. Prefer the smallest correct change without speculative framework
creation or unrelated refactoring.

Do not introduce a separate client filtering model; the current GET remains the
source of applied results. Tag-option search is not patient q. Normalize draft
from actual form controls and compare against the last server-applied state.
Do not mark a form dirty during initialization merely because historical lookup
loads. Listen to actual selected-tag changes without duplicating hidden inputs
or preference-save values. Do not commit drafts on shortcut links.

Position/size only the option layer; do not clip focus rings or make the whole
card globally overflow-visible without evidence. Preserve an operable native
fallback. Add only the scoped CSS/DOM attributes needed for S3 to consume the
same selector later; do not implement S3/report controllers in this slice.

## Validation

### Focused Validation

```bash
./scripts/test.sh apps.patients.tests.test_tag_selector_template \
  apps.patients.tests.test_tag_filters \
  apps.patients.tests.test_ward_map_tag_filters \
  apps.patients.tests.test_tag_lookup \
  apps.patients.tests.test_tag_visibility \
  apps.accounts.tests.test_tag_preferences
./scripts/test.sh apps.patients apps.accounts
npm run build
```

Check draft normalization for trimmed/reverted q, deduplicated tag IDs and all
other host predicates. Check existing option-result pagination remains 20/page
and the panel's internal `scrollHeight > clientHeight` when applicable. Check
button accessible names and neutral chip computed contrast repeatedly for new
and server-rendered tags. Direct generated output must come only from the build.

### Project-Required Gates

Run all applicable gates in `AGENTS.md` and
`docs/workflows/coding-standards.md`: project suite, scoped Python checks, build,
Markdown lint for touched docs and `git diff --check`.

### Runtime / Verification Evidence

Follow `verification.md` S2 at 1440x900, 390x844 and 320 px:

1. Capture RED browser geometry/interaction before implementation.
2. Exercise typed/reverted/applied filter matrices and verify request type,
   result IDs/counts, origin and URL. No ordinary input event may cause patient
   result navigation.
3. Exercise clear/reapply, badge removal and pagination with pending controls;
   prove form B is absent from resulting GET and is not presented as applied
   after the new full-page render.
4. Exercise panel opening, both pages of results, click-outside/Escape/focus
   reopening, full keyboard selection/removal and option-request failure.
5. Measure host-card/panel/Apply geometry, chip targets/contrast and 320 px
   horizontal overflow. Inspect focus rings in actual screenshots.
6. Verify native no-JS Apply/repeated tags/historical fallback and retained
   explicit preference/default behavior without writing fixture preferences.

## Acceptance Criteria

- [ ] R1: All patient/map predicates have normalized explicit draft/Apply proof.
- [ ] R2: No implicit/shortcut submission silently applies unrelated drafts.
- [ ] R3: Bounded overlay and open/close/keyboard behavior have measured proof.
- [ ] R4: Contrast, labels, targets and long-name mobile behavior pass.
- [ ] R5: Existing matching, visibility, preference and no-JS contracts pass.
- [ ] Handoff names actual selector hooks/events/host draft-state contract for
      report reuse; focused/project/runtime evidence is accepted.

## Escalation Conditions

Stop with `BLOCKED_NEEDS_DECISION` for new behavior/authorization/persistence
decisions, need for a new package/harness, unresolved clipping/mobile strategy,
reports implementation required prematurely or inability to satisfy evidence.
Unlisted paths require concrete justification and prior approval. Do not change
filter matching, authorization or preference precedence to simplify dirty state.

## Evidence Report

Path: `/tmp/sirhosp-slice-TFUX-S2-report.md`.

Include status, requirement mapping, files, RED/GREEN evidence, command exits,
runtime run identity and measured geometry/targets, screenshots/probes and
limitations. Identify every extra path and why it was necessary. Hand off actual
selector lifecycle events, selected-ID extraction, historical-option semantics,
host pending-state interface and build consumers for S3. Name optional helpers
created or explicitly record none.

## Worker Handoff

```text
Implement only TFUX S2. Reconstruct fresh context from this contract, referenced
artifacts and S1's accepted handoff. Follow repository engineering policy.
Produce failing-before evidence, implement the smallest correct change, validate
and write the report. Do not update tasks.md, commit, push, merge, archive or
start S3. If a decision is required, stop with BLOCKED_NEEDS_DECISION and
evidence. Otherwise finish READY_FOR_REVIEW with
REPORT_PATH=/tmp/sirhosp-slice-TFUX-S2-report.md.
```
