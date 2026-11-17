# PLFA-S1 — Simplify patient-list filter actions

## Identity

- Change: `simplify-patient-list-filter-actions`.
- Task: [tasks.md §1 / 1.1](../tasks.md#1-deliver-the-patient-list-action-contract).
- Dependency: operator approval of this change and verification prerequisites.
- Scope: one vertical slice, patient list only.

## Objective

Users can apply drafts, genuinely clear all filters or restore specialty tags
without duplicate controls, misleading preference labels or cross-page changes.

## Read First

- `AGENTS.md`, `PROJECT_CONTEXT.md`, `openspec/config.yaml`.
- `docs/workflows/coding-standards.md`.
- This change's `proposal.md`, `design.md`, `tasks.md`,
  `verification.md` and `specs/patient-tag-filtering/spec.md`.
- `openspec/specs/patient-tag-filtering/spec.md`.
- `apps/patients/views.py`: PatientListView and \_tag_filter_context.
- `apps/patients/urls.py`, list template and shared tag components below.
- `apps/patients/services/tag_filters.py`;
  `apps/accounts/services/tag_preferences.py`.
- `assets/js/tag-selector.js`, `assets/js/patient-filter-form.js`: read only.
- Existing selector/filter/profile tests and report selector regressions below.
- `.pi/skills/verify-eqmd/SKILL.md` for runtime safety, not unrelated journeys.

## Requirements and Planned Evidence

- **R1:** One list action bar, conditional configured-default restore and no
  repeated applied-clear/restore controls, including empty states. Applied
  summaries are read-only. Evidence: rendered counts/labels/HTML and browser.
- **R2:** Clear-all immediately removes q/status/admission/tags, resets ANY/page,
  encodes manual-empty, survives refresh/page and never saves preferences.
  Evidence: URL generation/follow tests, database invariants and browser.
- **R3:** Specialty restore changes tags/mode only, preserves applied non-tag
  predicates, discards pending edits and revalidates current defaults.
  Evidence: GET/default-state matrix and pending-versus-applied browser journey.
- **R4:** Existing × edits remain draft until Apply; no-JS empty Apply suppresses
  default fallback. No bulk-clear control is introduced.
  Evidence: bound GET/render tests, native browser and dirty-state checks.
- **R5:** Preference labels reflect applied source and effective tags, preserving
  empty/invalid/unavailable distinctions. Evidence: source matrix and live
  saved-nonempty-default case, not only an empty-profile preview.
- **R6:** Map/reports, lookup/permissions, saved settings, first-entry defaults
  and clean enhanced Apply keep their behavior.
  Evidence: shared-surface regression tests and scoped browser smoke checks.

## Expected Blast Radius

Approved new paths:

- `apps/patients/services/patient_list_filter_actions.py`.
- `apps/patients/views_patient_list_filters.py`: narrow inherited view adapter.
- `apps/patients/tests/test_patient_list_filter_actions.py`.

Approved existing paths:

- `apps/patients/urls.py`: wire existing named list route to the adapter.
- `apps/patients/templates/patients/patient_list.html`.
- `apps/patients/templates/components/_tag_filter.html`.
- `apps/patients/templates/components/_tag_selector.html`: list opt-in only.
- `apps/patients/tests/test_tag_selector_template.py`.
- `apps/patients/tests/test_tag_filters.py`: obsolete list assertions only.
- `apps/patients/tests/test_tag_filter_rendering.py`, if its assertions need
  intentional list-specific updates.

New feature tests belong in the new bounded module. Keep legacy test updates
minimal and identify their existing size; do not hide a broad test refactor here.

Sensitive/outside scope: no legacy views.py or shared JS edit, map/report
template change, parser/default/preference-service mutation, migration,
permission change, new endpoint/dependency or asset-build wiring. The existing
named route, view gates and query/pagination behavior must remain inherited.

Allowed non-repo writes are only the run-specific evidence deliverables in
`verification.md` and the slice report below.

## Failing-Before Plan

Use RED → GREEN → REFACTOR:

1. Add a saved-default fixture test that follows the rendered clear-all action.
   Baseline must fail because the new action is absent or defaults reappear.
2. Add action-count/summary/preference-source and no-JS empty Apply tests before
   changing those behaviors. Update obsolete old-label assertions only after
   recording their intentional contract change; preserve matching/privacy tests.
3. Record baseline browser URLs/results with default X and manual Y:
   current root reset restores X and duplicate actions exist.
4. Use reproducible browser failing-before evidence for interactions that a
   Django test cannot prove. Login/fixture/environment failures are not valid RED.

## Implementation Constraints

Follow repository engineering policy in `AGENTS.md` and preserve existing
conventions. Prefer the smallest correct change; avoid speculative abstraction
and unrelated refactoring.

Design D1–D4 are the contract. Keep list action context distinct from shared
clear_tags_querystring/reapply helpers; bookmarked scoped URLs remain valid.
Use the opt-in flag only on the list, with false/default preserving the map.
Keep shared JS and the existing preference-save endpoint untouched. Presentation
flags must not bypass authentication, patient eligibility or tag visibility.

Do not create a parameter-free "clear" link or construct global-action URLs
from pending form fields. Mark explicit native-empty Apply reliably even when
the initial hidden origin is automatic. Do not treat a saved preference existing
as proof that it is currently applied.

## Validation

### Focused Validation

```bash
./scripts/test.sh apps.patients.tests.test_patient_list_filter_actions \
  apps.patients.tests.test_tag_selector_template \
  apps.patients.tests.test_tag_filters \
  apps.patients.tests.test_tag_filter_rendering \
  apps.accounts.tests.test_tag_preferences \
  apps.reports.tests.test_template_catalogue_s3 \
  apps.reports.tests.test_template_creation_s4
```

Include saved X/manual Y, q/status/admission/page, saved-empty, principal-only,
no valid specialty, no configured default, unavailable/invalid tags and clean
Apply. Compare saved preference IDs/tags/mode before/after all GET actions.
Prove canonical old scoped URLs still work even though list duplicates disappear.
Check anonymous/unauthorized requests retain inherited behavior.

### Project-Required Gates

Run `AGENTS.md` and canonical coding-standard gates for touched paths.
If /app serves another checkout, test the changed worktree in an isolated
container /tmp copy via docker exec eqmd_dev and document the exact command.
Do not pass off baseline tests from a different tree as implementation proof.
No source assets are planned; if an asset change becomes necessary, stop for
scope approval and include its required build.

### Runtime / Verification Evidence

Execute the complete `verification.md` journey with the mandatory saved-default
profile at desktop and narrow widths. Record link destinations, result IDs,
applied versus pending controls, source labels and no preference/clinical POSTs.
Cover true clear-all versus tag-scoped restore, no-JS empty Apply and unchanged
map/report behavior. Identify served versus preview evidence explicitly.

## Acceptance Criteria

- [x] R1: Unique action bar and read-only summary, including filtered-empty.
- [x] R2: Genuine clear-all persists without modifying saved preferences.
- [x] R3: Restore preserves applied non-tag filters and discards pending edits.
- [x] R4: Draft × and no-JS empty Apply work without another bulk-clear button.
- [x] R5: All applied-source labels and the saved-default browser case pass.
- [x] R6: Shared-surface, legacy-URL, defaults and authorization checks pass.
- [x] Focused/project gates and complete runtime evidence are recorded.

## Escalation Conditions

Stop with `BLOCKED_NEEDS_DECISION` for a contradictory contract, new product or
architecture choice, material/unlisted scope expansion, public compatibility
break, unapproved persistence/FSM change, new security/privacy/clinical risk,
or inability to satisfy acceptance. Missing saved-default fixtures or runtime
identity is a blocker, not a reason to substitute an empty-profile success.
Do not repair unrelated preference-save behavior or refactor shared JS here.

## Evidence Report

Path: `/tmp/sirhosp-slice-PLFA-S1-report.md`.

Include status `READY_FOR_REVIEW` or `BLOCKED_NEEDS_DECISION`, R-to-evidence
mapping, actual changed paths, failing-before/passing-after results, commands
and exit statuses, source identity, runtime artifacts, cleanup outcome/handoff,
unexpected blast radius and justification, limitations and human decisions.
Do not duplicate the diff as before/after snippets.

## Worker Handoff

```text
Implement only approved PLFA-S1 using this slice and referenced OpenSpec artifacts.
Reconstruct fresh context; follow repository engineering policy.
Produce failing-before evidence, make the smallest correct change and validate.
Write /tmp/sirhosp-slice-PLFA-S1-report.md with evidence and exact gate outcomes.
Do not update tasks.md, commit, push, merge, archive or start another slice.
If a new decision is needed, stop BLOCKED_NEEDS_DECISION with evidence.
Otherwise finish READY_FOR_REVIEW and REPORT_PATH pointing to that report.
```
