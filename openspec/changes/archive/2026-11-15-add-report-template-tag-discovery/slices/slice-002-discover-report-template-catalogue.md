# S2 — Discover report templates in the catalogue

## Identity

- Change: `add-report-template-tag-discovery`.
- Task: [tasks.md §2 / 2.1](../tasks.md#2-s2--discover-models-in-the-catalogue).
- Dependency: S1 accepted; its schema is available in the test/runtime checkout.

## Objective

Users find report models in `/reports/templates/` using existing specialty
defaults, manual multi-tag filtering and dynamic name search.

## Read First

- `AGENTS.md`, `PROJECT_CONTEXT.md`, `openspec/config.yaml`.
- `docs/workflows/coding-standards.md`.
- This change's `proposal.md`, `design.md` D3–D5, D7–D8 and `tasks.md`.
- This change's `verification.md` and the accepted
  `/tmp/sirhosp-slice-S1-report.md` implementation-interface handoff.
- This change's `specs/reports/spec.md`: visibility, matching, specialty
  defaults, explicit override and dynamic discovery requirements.
- `openspec/specs/patient-tag-filtering/spec.md`,
  `openspec/specs/team-tag-governance/spec.md`.
- `apps/accounts/services/tag_preferences.py`.
- `apps/patients/services/tag_filters.py`, `tag_projection.py`,
  `tag_lookup.py`; read for reuse, not modification.
- S1's report tag services and existing `views/template_views.py`,
  `reporttemplate_list.html`, `tests/test_template_views.py`.
- `webpack.config.js`, `package.json`, `.pi/skills/verify-eqmd/SKILL.md`.

## Requirements and Planned Evidence

- **R1:** Catalogue results remain public-or-own, including inactive models, and
  combine distinct ANY/ALL tag matching with accent/case-insensitive name search.
  Evidence: query and full/fragment view tests.
- **R2:** Apply existing manual > saved > principal > none defaults, including
  saved-empty, no valid specialty, unavailable defaults and unchanged preference
  storage. Evidence: preference matrix and database non-mutation assertions.
- **R3:** Clear/reapply, manual historical filters, q and pagination preserve
  canonical state; invalid explicit filters return generic HTTP 400 without
  successful results. Enhanced historical options load without navigation or
  lost selections. Evidence: URL round-trip, full/fragment option parity,
  unknown/hidden/malformed ID tests and the historical-toggle browser scenario.
- **R4:** Show filter origin, visible tags, mode, warning and zero/error states,
  including tags used only by templates. Evidence: HTML tests and browser proof.
- **R5:** Dynamic q uses 250 ms debounce, bounded server pages, stale-response
  protection and accessible status feedback; no-JS GET remains usable.
  Evidence: browser scenarios below and server pagination tests.
- **R6:** Catalogue, existing copy/view/edit actions and patient list/map behavior
  remain intact. Evidence: reports plus existing tag/preferences regression tests.

## Expected Blast Radius

Approved existing paths:

- `apps/reports/views/template_views.py`.
- `apps/reports/templates/reports/reporttemplate_list.html`.
- S1's `apps/reports/services/template_tag_projection.py`.
- `apps/reports/tests/test_template_views.py`,
  `apps/reports/tests/tag_fixtures.py` if S1 created it.
- `webpack.config.js`.

Approved new paths:

- `apps/reports/services/template_discovery.py`.
- `apps/reports/forms_template_discovery.py` for query validation if needed.
- `apps/reports/templates/components/_report_template_filters.html`.
- `apps/reports/templates/reports/partials/_reporttemplate_results.html`.
- `apps/reports/tests/test_template_discovery.py`.
- `assets/js/report-template-discovery.js`.

Webpack outputs, including `static/js/report-template-discovery.js`, are
generated artifacts only; edit source, not generated files. Record the build
output paths without manually changing unrelated tracked generated assets.
The only additional non-repo write area is the verification deliverable directory
named in `verification.md`; no repository harness changes.

Sensitive/outside scope: no schema/migrations, no changes to accounts/patients
preference or tag policy, no new profile-save action, no shared tag-selector
rewrite, no clinical selector endpoint/application yet.

## Failing-Before Plan

Use RED → GREEN → REFACTOR for deterministic behavior:

1. Add catalogue tests with A={X,Y}, B={X}, C={} and a name containing accents;
   baseline must fail ANY/ALL/default/search expectations.
2. Add tests for invalid explicit IDs/mode, saved-empty, unavailable defaults,
   historical filters and pagination before implementing each branch.
3. Capture the current absence of dynamic search through a reproducible browser
   action or DOM assertion. Use this as failing-before evidence for frontend
   behavior; do not invent a new frontend test framework merely for this slice.

## Implementation Constraints

Follow repository engineering policy in `AGENTS.md` and preserve existing
conventions. Prefer the smallest correct change, without speculative abstraction
or unrelated refactoring.

Implement D4/D5 using reports relation paths, not patient joins. Handle the
preference resolver's error state before requesting results. Do not let a
malformed explicit filter become successful unfiltered discovery.
Do not convert automatic defaults into manual state just because q changes.
Keep the existing endpoint and management eligibility. Add abstractions only
needed for this catalogue; S3 can reuse them later. Read S1's accepted interface
manifest before using its exports. Optional form/test helpers are not required;
reuse only those actually delivered and named in that handoff. Do not create an
empty helper or move modules solely to match a candidate path.

## Validation

### Focused Validation

```bash
./scripts/test.sh apps.reports.tests.test_template_discovery \
  apps.reports.tests.test_template_views \
  apps.accounts.tests.test_tag_preferences \
  apps.patients.tests.test_tag_filters
./scripts/test.sh apps.reports
npm run build
```

Check full-page and fragment result IDs/counts agree for the same actor/query.
Use more than 20 candidates and duplicate names to verify bounded stable pages.
Check all forms/links encode repeated tags and retain manual-empty on refresh.
Assert full-page and fragment options include active readable tags by default,
historical choices on explicit request and already-selected readable historical
tags even when the toggle is off. Verify hidden metadata never enters the inert
options block and option-request errors preserve current selections.

### Project-Required Gates

Run the gates in `AGENTS.md` and `docs/workflows/coding-standards.md` for the
changed paths, including frontend build and scoped Python checks.

### Runtime / Verification Evidence

Follow `verification.md`: use the operator-supplied fixture manifest and a
standalone Playwright evidence script. Use `page.route`/`route.fetch`/
`route.fulfill` to delay real responses and induce HTTP failure; use a separate
no-JS context for fallback proof. No missing fixture/tooling may be improvised.

On the verified served checkout with those approved disposable fixtures:

1. Open catalogue with a saved specialty default; see its mode/source and the
   correct models. Include one tag used only on a template.
2. Switch ANY/ALL; combine with an unaccented name query. Clear and refresh:
   untagged models return without restoring defaults. Reapply restores defaults.
   With JS enabled, turn historical choices on, select a readable archived tag
   and Apply: its model matches. Turn the toggle off and confirm that selection
   remains. No full navigation, hidden options or implicit predicate change is
   allowed from toggling alone.
3. Type quickly and deliberately reorder network responses; only the latest q
   may update results. Exercise HTTP failure and observe a visible error.
4. Page beyond 20 models and verify no duplicates/lost filters. Check keyboard
   access, polite status and a narrow viewport.
5. Disable JS and exercise GET filtering/pagination. Confirm original copy/view
   and authorized edit controls still work.
6. Inspect outsider HTML/fragment output for hidden tag metadata and private
   foreign models. Record action, assertion, screenshot/trace and role per check.

## Acceptance Criteria

- [ ] R1: Results honor scope, conjunctive search and distinct ANY/ALL semantics.
- [ ] R2: Shared preference/default matrix passes without preference writes.
- [ ] R3: Historical options update live; override/URL/error cases pass safely.
- [ ] R4: Effective state and template-only tags are visible without leaks.
- [ ] R5: Dynamic, paginated, accessible and no-JS flows have browser evidence.
- [ ] R6: Catalogue actions and patient preference/filter regressions pass.
- [ ] Focused/project gates and runtime proof are recorded with exit statuses.
- [ ] D7 handoff lists discovery exports, response shapes and optional helpers.

## Escalation Conditions

Stop with `BLOCKED_NEEDS_DECISION` for conflicting spec/design, a new
product/architecture decision, material scope expansion, unapproved public
compatibility or persistence/FSM change, a new security/privacy/integrity/clinical
implication, or inability to satisfy the contract. Additional unlisted paths
require a concrete justification and approval before editing. Missing runtime
or command prerequisites are blockers, not passing evidence.
Do not add a search index or modify shared patient filtering to work around an
unmeasured performance concern. No persistence change is approved in S2.

## Evidence Report

Path: `/tmp/sirhosp-slice-S2-report.md`.

The report must contain status (`READY_FOR_REVIEW` or
`BLOCKED_NEEDS_DECISION`), R-to-evidence mapping, changed paths, failing-before
and passing-after evidence, commands with exit statuses, runtime evidence,
unexpected blast radius with justification, limitations and human decisions.
Include the runtime artifacts and implementation-interface manifest required by
`verification.md` and design D7: actual query exports/signatures, return shapes,
fragment/option data attributes, filter/asset consumers and tests. Name optional
helpers delivered or explicitly record that none were needed. Do not duplicate
the diff as before/after snippets.

## Worker Handoff

```text
Implement only this approved slice. Treat this contract and the referenced
OpenSpec artifacts as authority; reconstruct fresh context from the listed files.
Follow repository engineering policy. Produce failing-before evidence, implement
the smallest correct change, validate and write the evidence report. Do not
update tasks.md, commit, push, merge, archive or start another slice. If a new
decision is required, stop with BLOCKED_NEEDS_DECISION and evidence. Otherwise
finish READY_FOR_REVIEW with REPORT_PATH=/tmp/sirhosp-slice-S2-report.md.
```
