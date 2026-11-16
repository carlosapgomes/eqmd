# TFUX S1 — Filter language and recovery

## Identity

- Change: `improve-tag-filter-discovery-ux` (TFUX).
- Task: [tasks.md §1 / 1.1](../tasks.md#1-s1--clarify-filter-language-and-recovery).
- Dependency: none; planning and these artifacts must be approved before work.

## Objective

Make filter meaning, primary/removal actions and zero-result recovery clear on
patient list, patient map and report-template catalogue without changing when
requests run or which records match.

## Read First

- `AGENTS.md`, `PROJECT_CONTEXT.md`, `openspec/config.yaml`.
- `docs/workflows/coding-standards.md`.
- This change's `proposal.md`, `design.md` D1–D4/D7–D9 and `tasks.md`.
- This change's `verification.md` and both delta specs; for this slice, only
  language, accessible naming and filtered-empty requirements are activated.
- Baseline `openspec/specs/patient-tag-filtering/spec.md` and
  `openspec/specs/reports/spec.md` for behavior that must not change.
- `apps/patients/services/tag_filters.py`.
- Patient list/map templates and their tag-filter partials.
- Report template filter/results partials, list/create templates and current
  discovery controller enough to avoid a behavior change in shared wording.
- Existing tag-filter, ward-map, template-discovery and template-selection tests.
- `.pi/skills/verify-eqmd/SKILL.md` for the shared-stack rules.

## Requirements and Planned Evidence

- **R1:** Patient list/map and both report consumers expose the canonical
  correspondence/origin/historical wording and visible Correspondência labels
  from design D3. ANY/ALL values and matching behavior remain unchanged.
  Evidence: template/context tests and rendered text assertions.
- **R2:** Patient list/map's principal action says Aplicar filtros, not only an
  icon. Every touched tag-removal action has a specific accessible name and
  clear/reapply wording matches its existing effect. Evidence: DOM/a11y tests
  and browser assertions for draft versus applied removal scope.
- **R3:** Filtered-zero patient and catalogue states explain no match and
  provide existing scoped recovery; a genuinely unfiltered empty collection
  retains the normal creation explanation only under current authorization.
  Manual empty is not presented as an untagged-record predicate. Evidence:
  isolated view tests for both empty types and filtered-zero browser checks.
- **R4:** Current initial/default/manual precedence, GET parameters, name-query
  timing, clinical behavior and report-creation controller remain unchanged in
  S1. Evidence: focused existing behavior tests and explicit no-scope-change
  report diff review.

## Expected Blast Radius

Expected implementation paths:

- `apps/patients/services/tag_filters.py` for shared presentation labels only.
- `apps/patients/templates/components/_tag_selector.html`.
- `apps/patients/templates/patients/patient_list.html` and
  `patients/ward_patient_map.html`.
- `apps/reports/templates/components/_report_template_filters.html`.
- `apps/reports/templates/reports/partials/_reporttemplate_results.html`.
- `apps/reports/templates/reports/report_create_form.html` only if shared
  wording/accessible link names require direct parity.
- Focused existing tests in `apps/patients/tests/test_tag_filters.py`,
  `test_ward_map_tag_filters.py`, `apps/reports/tests/test_template_discovery.py`
  and `test_template_selection.py`; one narrowly named alternative test module
  per app is acceptable if reported.

No controller query, model, service matching, preference resolver, JS transport
or state-history changes are required in S1. Do not edit generated assets.
`verification.md` permits only its external evidence directory in addition to
application/tests above.

Sensitive/outside scope: no pending-state implementation, no searchable-report
selector, no preference/clear-all semantic changes, no global style or result
row/badge redesign, no report-creation clinical form changes.

## Failing-Before Plan

Use RED → GREEN → REFACTOR for rendered text and empty states:

1. Add focused assertions for visible correspondence wording, text Apply,
   accessible tag-removal labels and filtered/manual-empty context. Run them on
   the baseline and preserve failures tied to each missing behavior.
2. Add a filtered-zero template test with existing records outside the result;
   it must fail because the current empty CTA describes first-record creation.
3. Add a genuinely unfiltered empty test to protect the legitimate create CTA;
   this is a guard and may already pass, so do not claim it as RED.
4. Capture the current ambiguous controls and filtered-zero UI through the
   verification script before implementation.

## Implementation Constraints

Follow repository engineering policy in `AGENTS.md` and preserve existing
conventions. Prefer the smallest correct change without speculative abstraction
or unrelated refactoring.

Change labels and conditionally presented empty-state content only. Reuse
existing clear/reapply/removal URLs rather than introducing new preference or
clear-all behavior. Do not make report creation consistent with explicit Apply
yet; S3 owns catalogue transport and S4 owns creation behavior. Preserve native
fallback and restricted metadata handling. Do not replace current dynamic name
search or show-empty submission in this slice.

## Validation

### Focused Validation

```bash
./scripts/test.sh apps.patients.tests.test_tag_filters \
  apps.patients.tests.test_ward_map_tag_filters \
  apps.patients.tests.test_tag_selector_template \
  apps.reports.tests.test_template_discovery \
  apps.reports.tests.test_template_selection
./scripts/test.sh apps.reports
```

Inspect both initial/automatic and explicit/manual markup for list and map.
Compare equal GETs before/after where practical: result identities/counts,
correspondence values and repeat-tag URL semantics must not change. If a test
expects legacy wording, update only assertions whose UX contract this slice
explicitly replaces; never relax result/privacy expectations.

### Project-Required Gates

Run all applicable gates in `AGENTS.md` and
`docs/workflows/coding-standards.md`, including project tests, scoped Python
checks and `git diff --check`. Run Markdown lint on any touched `.md`.

### Runtime / Verification Evidence

Follow `verification.md` and its S1 obligations:

1. Prove current rendered labels and filtered-empty behavior before editing.
2. At desktop and 390 px, verify Apply/find/reset/recovery labels and accessible
   tag-specific removal names on all three requested pages.
3. Produce filtered-zero patient, map and catalogue states with real server
   responses. Confirm correct no-match copy/actions and no inappropriate
   first-record CTA.
4. Confirm automatic/manual origin and saved-default context remain accurate,
   and no browser action performs a preference or clinical POST.
5. Include no-JS assertions for shared text/native Apply and empty-state copy.

## Acceptance Criteria

- [ ] R1: Canonical wording is used without changing ANY/ALL or origins.
- [ ] R2: Apply and tag-removal actions have clear visual/accessibility names.
- [ ] R3: Filtered and unfiltered empty states are distinct and recoverable.
- [ ] R4: Result semantics, request timing and shared clinical controllers are
      unchanged, with regression evidence.
- [ ] RED/GREEN, focused/project gates and required browser scenarios are
      recorded with exit statuses and served-checkout identity.

## Escalation Conditions

Stop with `BLOCKED_NEEDS_DECISION` for contradictory spec/design, new product or
architecture decisions, material scope expansion, authorization/privacy/clinical
implications, persistence requirements or inability to provide required
runtime evidence. Unlisted but necessary paths need justification and approval
before editing. If filtered recovery requires a new global clear-all preference
semantic, stop rather than introducing it.

## Evidence Report

Path: `/tmp/sirhosp-slice-TFUX-S1-report.md`.

Include status (`READY_FOR_REVIEW` or `BLOCKED_NEEDS_DECISION`), R-to-evidence
mapping, changed paths, RED/GREEN artifacts, commands and exit statuses,
runtime manifest/run IDs, screenshots/probes, limitations and unexpected scope.
Record which behavior remained unchanged. Hand off actual shared wording/context
keys to S2; do not duplicate the diff as evidence.

## Worker Handoff

```text
Implement only TFUX S1. Reconstruct context from this contract and referenced
files; do not rely on the planning conversation. Follow repository engineering
policy. Produce failing-before evidence, implement the smallest correct change,
validate and write the evidence report. Do not update tasks.md, commit, push,
merge, archive or start another slice. If a decision is required, stop with
BLOCKED_NEEDS_DECISION and evidence. Otherwise finish READY_FOR_REVIEW with
REPORT_PATH=/tmp/sirhosp-slice-TFUX-S1-report.md.
```
