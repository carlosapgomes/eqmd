# S3 — Discover models during report creation

## Identity

- Change: `add-report-template-tag-discovery`.
- Task: [tasks.md §3 / 3.1](../tasks.md#3-s3--discover-models-during-report-creation).
- Dependency: S2 accepted with query service, filter component and runtime proof.

## Objective

The report-creation selector shares catalogue discovery semantics while keeping
in-progress clinical content and a still-authorized current choice unchanged.

## Read First

- `AGENTS.md`, `PROJECT_CONTEXT.md`, `openspec/config.yaml`.
- `docs/workflows/coding-standards.md`.
- This change's `proposal.md`, `design.md` D3–D8 and `tasks.md`.
- This change's `verification.md` and accepted S1/S2 interface handoffs in
  `/tmp/sirhosp-slice-S1-report.md` and `/tmp/sirhosp-slice-S2-report.md`.
- This change's `specs/reports/spec.md`: visibility, discovery requirements and
  Discovery preserves report creation state.
- `openspec/specs/reports/spec.md` including duplication semantics.
- S2's `services/template_discovery.py`, filter component and discovery asset.
- `apps/reports/forms.py`, `views/report_views.py`, `urls.py`,
  `services/report_service.py`, `templates/reports/report_create_form.html`.
- `apps/reports/tests/test_report_create_view.py`,
  `test_report_duplicate_view.py`, `test_report_service.py`.
- `.pi/skills/verify-eqmd/SKILL.md` for verified runtime and EasyMDE interaction.

## Requirements and Planned Evidence

- **R1:** New authenticated selectable lookup and initial form use S2 semantics,
  but active public-or-own eligibility only. Evidence: endpoint/form tests and
  catalogue-versus-selector parity on the same fixtures.
- **R2:** Return bounded 20-item pages, safe historical `tag_options` and other
  fields from D6; reject invalid explicit filters/UUIDs generically. Evidence:
  schema/count/option/permission, anonymous and session-revocation endpoint tests.
- **R3:** Keep authorized selected choices outside results pinned separately,
  not counted or silently cleared. Reproject the choice on lookup; unavailable
  choices reveal no metadata and cannot submit successfully.
  Evidence: selected-choice lifecycle tests, full-queryset validation and browser.
- **R4:** Enhanced search/apply/clear/reapply/paging/historical toggle must never
  navigate, submit, re-render or change title/date/markdown/selection. Evidence:
  reproducible browser checkpoints on edited EasyMDE content and network activity.
- **R5:** Manual report creation, explicit model GET prefill, validation-error
  rerender, duplication and update behavior remain intact. No-JS discovery has a
  separate GET form and navigation warning. Evidence: form/view regressions,
  DOM no-nesting assertions and browser.
- **R6:** Catalogue still behaves as accepted in S2 after shared asset reuse.
  Evidence: catalogue smoke browser checks and reports discovery tests.

## Expected Blast Radius

Approved existing paths:

- `apps/reports/forms.py`, `apps/reports/views/report_views.py`,
  `apps/reports/urls.py`.
- S2's `apps/reports/services/template_discovery.py`,
  `apps/reports/forms_template_discovery.py` if created.
- S1's `apps/reports/services/template_tag_projection.py`.
- `apps/reports/templates/reports/report_create_form.html`.
- `apps/reports/templates/components/_report_template_filters.html`.
- `apps/reports/templates/components/_report_template_tags.html`.
- `assets/js/report-template-discovery.js`.
- `apps/reports/tests/test_report_create_view.py`,
  `apps/reports/tests/test_template_discovery.py`,
  `apps/reports/tests/tag_fixtures.py` if created.

Approved new paths:

- `apps/reports/views/template_selection_views.py`.
- `apps/reports/widgets.py` for bounded rendering independent of validation.
- `apps/reports/tests/test_template_selection.py`.

Rebuild generated assets but do not hand-edit `static/`. No schema changes,
patient/account permissions, new dependencies, PDF/renderer changes, report
duplication/update selector changes or replacement for explicit model application.
The only additional non-repo write area is the verification deliverable directory
named in `verification.md`; no repository harness changes.

## Failing-Before Plan

Use RED → GREEN → REFACTOR:

1. Add an endpoint test for active, default-filtered selection: baseline should
   fail because the endpoint/behavior is missing.
2. Add bound-form tests for a selected authorized model outside q/tags/current
   page and for an inactive/private-foreign choice before implementation.
3. Record a baseline browser reproduction: selector lacks the new search/filter
   controls; capture the existing GET prefill separately.
4. Add failing-before DOM/browser evidence for discovery interactions where a
   Django test cannot prove EasyMDE state or absence of navigation.

An unrelated login/mount/fixture error is not valid failing-before evidence.

## Implementation Constraints

Follow repository engineering policy in `AGENTS.md` and preserve existing
conventions. Prefer the smallest correct change, without speculative abstraction
or unrelated refactoring.

Consume actual exports/return shapes from the accepted S1/S2 interface manifests.
Optional helpers are not prerequisites. Keep the required projection/discovery
module paths stable; an unlisted module move requires approval, not improvisation.

Follow D6: lookup returns no markdown/patient data; filter controls stay outside
the clinical form; bounded widget rendering must not narrow the authorized
ModelChoiceField validation queryset. Do not evaluate/render every eligible
template to implement browser-side filtering.

Changing result options must not dispatch the current selection change handler.
Keep existing explicit model application as a separate action; filtering has no
permission to replace content. No new asynchronous rendering endpoint is allowed.
Handle an unavailable current choice with generic metadata and server validation,
not a successful silent substitution.

## Validation

### Focused Validation

```bash
./scripts/test.sh apps.reports
./scripts/test.sh apps.accounts.tests.test_tag_preferences apps.patients.tests.test_tag_filters
npm run build
```

Assert lookup output keys, page limits, projected tags, no foreign private model
names/IDs and no hidden metadata/count. Include q with accents, duplicate names,
ANY/ALL, saved-empty, principal fallback, no specialty, invalid defaults,
historical filters, manual-clear refresh and invalid explicit IDs. Compare
`tag_options` with D5's fragment option builder; verify the toggle exposes only
readable history, retains selected history when off and never applies a tag.

Prove a selected authorized model outside visible options submits, while a
now-ineligible choice fails. On form errors, bound title/date/content/selection
and filter context must survive. Assert duplicate/update forms gain no selector.

### Project-Required Gates

Run the gates in `AGENTS.md` and `docs/workflows/coding-standards.md` for
changed paths. Rebuild source assets before accepting live UI evidence.

### Runtime / Verification Evidence

Follow `verification.md`: operator-owned fixtures, coordinated revocation and
cleanup, standalone Playwright script, real-response routing for network cases
and separate no-JS context. Record exact editable values and main-frame/POST
activity. Missing prerequisites mean blocked, not an improvised fixture mutation.

On the verified served checkout with those approved disposable fixtures:

1. Open patient report creation with saved specialty defaults; compare active
   result identities with the filtered catalogue.
2. Select a model using the current explicit GET prefill flow. Then edit title,
   date and EasyMDE text with a unique sentinel and record their exact values.
3. Search, Apply tags/ANY/ALL, clear, reapply, page and toggle historical choices.
   Select and apply a readable archived tag, then disable the toggle and confirm
   that the selected tag remains. After each discovery action assert
   identical title/date/text/selected ID, no document navigation and no clinical
   POST. Filter away the chosen model and verify its separate pinned label/count.
4. Submit once with the out-of-results authorized choice: saved content must be
   the edited sentinel, not regenerated model text. Verify manual creation too.
5. Revoke access/inactivate a disposable selected model between requests. Lookup
   must not return stale metadata; submission must reject it without saving.
6. Reorder responses, exercise network failure, keyboard/mobile controls and
   no-JS fallback. Record fallback warning and absence of nested forms.
7. Smoke-check S2 catalogue search/clear/pagination again.
8. Record URLs, served revision/path, fixture ownership, exact assertions,
   screenshots/trace, request log and read-only report row verification.

The existing draft-supervision harness journeys do not cover these behaviors.
Do not claim those unrelated green journeys as feature evidence.

## Acceptance Criteria

- [ ] R1: Selector and catalogue share semantics while retaining active-only scope.
- [ ] R2: Lookup is authenticated, bounded, validated and metadata-safe.
- [ ] R3: Pinning, current eligibility and full validation-queryset cases pass.
- [ ] R4: Every enhanced discovery interaction preserves edited clinical state.
- [ ] R5: Manual/prefill/error/no-JS/duplication/update regressions pass.
- [ ] R6: S2 catalogue remains working after asset reuse.
- [ ] Focused/project gates and runtime proof are recorded with exit statuses.

## Escalation Conditions

Stop with `BLOCKED_NEEDS_DECISION` for conflicting spec/design, a new
product/architecture decision, material scope expansion, unapproved public
compatibility or persistence/FSM change, a new security/privacy/integrity/clinical
implication, or inability to satisfy the contract. Additional unlisted paths
require a concrete justification and approval before editing. Missing runtime
or command prerequisites are blockers, not passing evidence.
Stop rather than altering clinical authorization or introducing asynchronous
template application to simplify lookup. No persistence change is approved here.

## Evidence Report

Path: `/tmp/sirhosp-slice-S3-report.md`.

The report must contain status (`READY_FOR_REVIEW` or
`BLOCKED_NEEDS_DECISION`), R-to-evidence mapping, changed paths, failing-before
and passing-after evidence, commands with exit statuses, runtime evidence,
unexpected blast radius with justification, limitations and human decisions.
Include runtime artifacts and the final actual module/export/response-shape
manifest required by `verification.md` and design D7. Identify optional helpers
used or not delivered. Do not duplicate the diff as before/after snippets.

## Worker Handoff

```text
Implement only this approved slice. Treat this contract and the referenced
OpenSpec artifacts as authority; reconstruct fresh context from the listed files.
Follow repository engineering policy. Produce failing-before evidence, implement
the smallest correct change, validate and write the evidence report. Do not
update tasks.md, commit, push, merge, archive or start another slice. If a new
decision is required, stop with BLOCKED_NEEDS_DECISION and evidence. Otherwise
finish READY_FOR_REVIEW with REPORT_PATH=/tmp/sirhosp-slice-S3-report.md.
```
