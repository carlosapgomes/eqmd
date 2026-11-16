# TFUX S3 — Searchable explicit template catalogue

## Identity

- Change: `improve-tag-filter-discovery-ux` (TFUX).
- Task: [tasks.md §3 / 3.1](../tasks.md#3-s3--unify-report-catalogue-discovery).
- Dependency: S2 accepted and its real selector/host-state interface handoff at
  `/tmp/sirhosp-slice-TFUX-S2-report.md`.

## Objective

Unify `/reports/templates/` with explicit searchable tag discovery and reliable
applied/draft/history behavior while retaining its catalogue eligibility,
fragment transport and no-JavaScript fallback.

## Read First

- `AGENTS.md`, `PROJECT_CONTEXT.md`, `openspec/config.yaml` and coding standards.
- This change's `proposal.md`, `design.md` D1–D9 and `tasks.md`.
- This change's `verification.md`, especially S3, and
  `specs/reports/spec.md` including MODIFIED Dynamic report template name discovery.
- Baseline `openspec/specs/reports/spec.md` and
  `openspec/specs/patient-tag-filtering/spec.md` for unchanged semantics.
- Accepted S1/S2 reports; use only actual delivered selector hooks/events.
- `apps/patients/services/tag_lookup.py`, `tag_projection.py`,
  `forms_tag_filters.py`, `views_tag_filters.py`; read for reuse/boundary, not
  permission weakening.
- `assets/js/tag-selector.js`, patient/map consumer integration and scoped CSS.
- Reports `services/template_discovery.py`, `views/template_views.py`, `urls.py`,
  filters/results/list templates and `assets/js/report-template-discovery.js`.
- Existing template discovery/selection/view/privacy tests, Webpack source/build
  config and the earlier report discovery verification artifacts if present.
- `.pi/skills/verify-eqmd/SKILL.md`.

## Requirements and Planned Evidence

- **R1:** Catalogue q/tags/mode have normalized explicit draft/Apply behavior.
  Typing q alone issues no model-result request; reverted edits clear dirty.
  Enhanced Apply uses one fragment request and successful results reconcile
  controls/summary/URL. Failure leaves last results/URL plus draft/error/dirty.
  Evidence: DELAY/503 browser network assertions and full/fragment view tests.
- **R2:** Enhanced native multi-select is replaced by the S2 searchable/chip
  selector using a reports-owned read-only lookup. Active/template-only,
  historical, long and selected tags retain correct requester-safe projection;
  report permission does not derive from patient-record permission and patient
  lookup permission is unchanged. Evidence: view/payload/privacy tests and
  outsider/reader browser proof.
- **R3:** Clear/reapply, applied-badge removal and pagination operate from
  last-applied state and preserve unrelated draft values visibly pending.
  Historical lookup is option-only and never causes a second/replayed query
  that commits pending edits. No-JS native repeated-tag GET remains usable.
  Evidence: browser matrix and URL/response parity tests.
- **R4:** Successful applied result actions create deliberate history only on
  canonical change; historical options replace; draft/failure/no-op do not push.
  Back/Forward fetches and reconciles popped results/controls without another
  push loop. Evidence: recorded history lengths, URL/results and Back/Forward
  browser proof.
- **R5:** S1 filtered-empty recovery and S2 bounded/accessible selector behavior
  carry into catalogue. Existing 20-model paginated eligibility/ANY/ALL,
  invalid 400s, active/default semantics and current report creation controller
  remain working without duplicate activation. Evidence: focused regressions,
  mobile/keyboard/no-JS browser checks and creation regression guard.

## Expected Blast Radius

Expected existing paths:

- Reports `services/template_discovery.py`, `views/template_views.py`, `urls.py`
  and current tests.
- Reports filters/results/list templates and
  `assets/js/report-template-discovery.js`.
- Accepted S2 selector JavaScript/styles/host-state hooks only where necessary
  for reports integration and shared regression.
- `webpack.config.js`, `assets/index.js` and focused tests/fixtures only if the
  actual build requires explicit wiring.
- Generated Webpack assets only via the frontend build.

Additional reports-owned lookup view/form/test modules and a report-owned
selector partial are approved if needed to meet D5 without sharing patient URL
permissions or duplicating tag-result rendering. Name actual choices in the
report. Do not create speculative generic frameworks.

Sensitive/outside scope: no schema/migrations, no patient lookup or tag/policy
matching modifications, no template association editing, no report-creation
selector activation/clinical behavior change yet, no preference-storage/global
clear redesign and no result-table rewrite. Any lookup permission weakening is
explicitly prohibited.

## Failing-Before Plan

1. RED Django tests for reports-owned lookup availability and its safe selected
   pagination/projection; verify patient endpoint permission baseline separately
   before any shared extraction.
2. RED catalog full/fragment assertions for enhanced selector hooks/explicit name
   behavior while preserving existing native/no-JS and matching guards.
3. Browser failing-before evidence: real q typing updates results without Apply;
   native multiple remains; pending state is absent; Back after successful
   pushed filters does not restore result state; old fragments carry no safe
   searchable lookup contract.
4. Separate newly absent behavior from existing successful safeguards (400s,
   privacy, eligibility, content preservation), which remain green regression
   checks rather than invented RED claims.

## Implementation Constraints

Follow repository engineering policy in `AGENTS.md` and preserve existing
conventions. Prefer the smallest correct integration without speculative
abstraction or unrelated refactoring.

Use S2's actual delivered selector API. Do not create a second tag-result
renderer in `report-template-discovery.js`; the reports controller owns only
applied/draft/transport/history. Do not let template-specific lookup bypass
requester projections or require `patients.view_patient`.

Remove typing-to-model-result debounce; retain 250 ms only for tag-option
lookup if needed. Do not silently convert automatic tag defaults to manual
origin except through an explicit Apply of the visible draft. A failed request
must not pushState. popstate must not call the normal push path.

Opt only catalogue into this selector/transport now. If a template partial is
shared with creation, use an explicit backend/DOM opt-in that leaves creation
on its accepted controller and native control until S4. Do not keep duplicate
historical toggles or initialize both catalogue and creation controllers.

## Validation

### Focused Validation

```bash
./scripts/test.sh apps.reports.tests.test_template_discovery \
  apps.reports.tests.test_template_views \
  apps.reports.tests.test_template_selection \
  apps.patients.tests.test_tag_lookup \
  apps.patients.tests.test_tag_filters \
  apps.patients.tests.test_tag_selector_template
./scripts/test.sh apps.reports apps.patients
npm run build
```

Assert reader and outsider option/lookup result sets, including hidden-tag
absence and selected historical identity preservation. Assert an equal applied
GET produces identical full-page and fragment IDs/count/context, repeated tags,
manual-empty and 20-model pagination. Test q >255 as HTTP 400 without false
success entries. Check a report-catalogue reader lacking `view_patient` still
gets only catalogue-authorized badge metadata; no existing permission is
reduced.

Inspect history helper seams directly where practical: no push on equal/failed
state, replace for option-only updates, one pop reconcile per navigation.
Template-selection controller and clinical content tests remain untouched or
are strengthened only as regression guards for S4.

### Project-Required Gates

Run all applicable `AGENTS.md`/coding-standards gates, project tests, scoped
Python lint/type checks, build, touched-Markdown lint and `git diff --check`.

### Runtime / Verification Evidence

Follow `verification.md` S3 with approved reader/outsider fixtures:

1. Record failing-before native selector, typing behavior and Back mismatch.
2. Verify tag search/chips for active, template-only, historical and long tags;
   measure panel and mobile targets, keyboard flow and outsider DOM/payload.
3. Verify q/tags/mode pending/revert/Apply, errors and stale responses, repeated
   tags and ANY/ALL results without full navigation.
4. Separately exercise clear/reapply/badge/page with pending values and prove
   no replay commits them. Historical toggle only changes options/replaces URL.
5. Apply A then B, then Back/Forward; assert history count, canonical URL,
   controls and result IDs. Verify draft/failure/no-op adds no applied entry.
6. Check filtered-zero and no-JS native repeated-tag Apply/pagination. Confirm
   report creation still has one functioning legacy controller as an S3 guard,
   not evidence that S4 happened.

## Acceptance Criteria

- [ ] R1: Explicit catalogue Apply/dirty/failure/stale contracts proven.
- [ ] R2: Searchable safe lookup and selected-chip behavior work without new
      patient permission or metadata leak.
- [ ] R3: Scoped actions/history choices/native fallback preserve draft/GET
      semantics without implicit replay.
- [ ] R4: Back/Forward and history-entry assertions pass deterministically.
- [ ] R5: Empty/a11y/pagination/eligibility and creation regressions pass.
- [ ] Actual reports integration/hook/API consumers and S4 limitations are
      handed off with focused/project/runtime evidence.

## Escalation Conditions

Stop with `BLOCKED_NEEDS_DECISION` for required permission changes, duplicated
controller activation, incompatible shared selector contract, material new
architecture/dependency, altered matching/preference persistence or lack of
safe runtime fixtures. Do not weaken patient permissions or switch to an
unprojected catalogue lookup. Unlisted paths need justification/approval.

## Evidence Report

Path: `/tmp/sirhosp-slice-TFUX-S3-report.md`.

Include status, requirement/evidence map, changed paths, RED/GREEN artifacts,
command exits, served checkout, role/viewport/network history proof and risks.
Name actual reports lookup endpoint/response shape, selector APIs consumed,
applied/draft/history helpers, DOM opt-ins and generated assets. State exactly
how report creation remains isolated; that interface is S4's starting point.

## Worker Handoff

```text
Implement only TFUX S3. Reconstruct context from this contract and accepted S1/S2
handoffs; do not rely on prior conversation. Follow repository engineering
policy. Produce failing-before evidence, implement the smallest correct change,
validate and write the report. Do not update tasks.md, commit, push, merge,
archive or start S4. If a decision is required, stop with BLOCKED_NEEDS_DECISION
and evidence. Otherwise finish READY_FOR_REVIEW with
REPORT_PATH=/tmp/sirhosp-slice-TFUX-S3-report.md.
```
