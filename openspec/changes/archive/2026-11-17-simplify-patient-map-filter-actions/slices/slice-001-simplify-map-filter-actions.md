# PMFA-S1 — Patient-map actions and truthful empty results

## Identity

- Change: `simplify-patient-map-filter-actions`.
- Task: [tasks.md §1 / 1.1](../tasks.md#1-deliver-the-map-filter-contract).
- Dependency: operator approval of implementation; valid verification fixtures.
- One vertical slice, map presentation only.

## Objective

Users can apply, genuinely clear or restore map filters and understand empty
wards/totals without duplicate actions or false preference/result claims.

## Read First

- `AGENTS.md`, `PROJECT_CONTEXT.md`, `openspec/config.yaml`.
- `docs/workflows/coding-standards.md`.
- This change's proposal, design, tasks, verification and
  [delta spec](../specs/patient-tag-filtering/spec.md).
- `openspec/specs/patient-tag-filtering/spec.md`.
- WardPatientMapView and the tag-filter context in `apps/patients/views.py`.
- Full/AJAX map templates and shared tag-filter/selector partials.
- `apps/patients/services/patient_list_filter_actions.py`.
- `apps/patients/services/tag_filters.py` and `ward_tag_overlay.py` there.
- `apps/accounts/services/tag_preferences.py`.
- `assets/js/tag-selector.js`, `assets/js/patient-filter-form.js` and
  `assets/js/ward_patient_map.js`: read only.
- Existing ward-map, selector, list-action and preference tests.
- `.pi/skills/verify-eqmd/SKILL.md`: safety/tooling, not unrelated journeys.

## Requirements and Planned Evidence

- **R1:** One named filter action bar, configured-default restore and read-only
  applied summary; no duplicate clear/restore in selector or empty recovery.
  Evidence: full/AJAX HTML counts and browser.
- **R2:** Clear-all drops q/ward/tags/show-empty, resets ANY and retains
  manual-empty on refresh without changing eligibility or preferences.
  Evidence: rendered URL/follow tests, snapshots and saved-X browser.
- **R3:** Restore preserves applied q/ward/show-empty and discards pending edits.
  Evidence: applied-versus-pending browser and GET/default-state tests.
- **R4:** Draft ×, native empty Apply and clean enhanced Apply retain the
  accepted explicit-Apply semantics without another bulk-clear control.
  Evidence: RED render/request tests and JS/no-JS browser.
- **R5:** Totals label uses effective applied q/ward/tags, not manual origin,
  mode alone or empty-ward display alone; origin remains separately visible.
  Evidence: full/AJAX matrix and browser.
- **R6:** Checkbox helper, filter-aware per-ward copy and one visible global
  zero notice are consistent in both variants, without adding counts or
  misclassifying invalid/updating data. Evidence: fixture matrix and browser.
- **R7:** Preference labels describe resolved applied source/effective tags.
  Evidence: saved/manual/empty/principal/no-default/error/unavailable matrix.
- **R8:** List/reports, scoped URLs, permissions, cache and requester visibility
  stay unchanged. Evidence: existing regressions, source diff and browser smoke.

## Expected Blast Radius

Approved new paths:

- `apps/patients/services/ward_map_filter_actions.py`.
- `apps/patients/views_ward_map_filters.py`.
- `apps/patients/tests/test_ward_map_filter_actions.py`.
- `apps/patients/tests/test_ward_map_empty_states.py`.
- `apps/patients/tests/ward_map_filter_fixtures.py`, if a dedicated shared
  fixture is needed; existing fixture helpers may instead be imported read-only.
- `apps/patients/templates/components/_ward_map_empty_notice.html`, if sharing
  the new notice avoids drift between the two map renderers.

Approved existing edits:

- `apps/patients/urls.py`: existing named map route to inherited adapter only.
- `apps/patients/templates/patients/ward_patient_map.html`.
- `apps/patients/templates/patients/ward_patient_map_tree_only.html`.
- `apps/patients/templates/components/_tag_filter.html`.
- `apps/patients/templates/components/_tag_selector.html`: map opt-in only.
- `apps/patients/tests/test_ward_map_tag_filters.py`: obsolete assertions only.
- `apps/patients/tests/test_patient_list_filter_actions.py`: operator-authorized
  update to its obsolete map-only compatibility guard; no other list test edits.
- `apps/patients/tests/test_tag_selector_template.py`: only if opt-in
  assertions need intentional updates.
- `apps/patients/tests/test_tag_filter_rendering.py`, if intentional map
  markup assertions need updating.

New feature tests belong in the new bounded modules. Record the existing
812-line map and 419-line selector test baselines; do not grow their feature
matrices or perform a broad split in this slice.

Sensitive/outside scope: legacy views.py, list/report code, shared or map JS,
source assets, tag parser/default/preference services, ward_tag_overlay,
cache utilities/generator/model/schema, endpoints and permission policy.
Do not change those without escalation. No shared generator/cache/profile
operation is authorized. Evidence-only writes follow verification.md plus
the report path below.

## Operator-Authorized Visual Homologation Amendment

The operator approved matching the list/map action bars on the left and moving
map display options out of the tag-filter block into a bordered section.
This is a bounded presentation amendment to PMFA-S1, not a new behavior slice.

Additional approved paths:

- `apps/patients/templates/patients/patient_list.html`: action alignment only.
- `apps/patients/templates/components/_ward_map_display_options.html`: checkbox,
  explanatory text and existing tree controls in a named bordered section.
- `apps/patients/tests/test_patient_filter_layout.py`: new bounded DOM tests.

Map template reorganization may put the GET form around separate filter and
visualization blocks. The checkbox must remain a descendant of that form so
existing dirty tracking, explicit Apply and native submission remain intact.
Preference saving stays an independent POST outside the GET form; present its
panel separately using the list's card conventions. Keep the dirty status by
Apply, not inside the visualization section. Keep existing JS hooks and IDs.

Verify matching action order/styles, left alignment at 1440/390/320px, bordered
options below the complete filter block, independent/non-nested forms, checkbox
helper association, draft-only toggle, native submission and existing regressions.
No service, JavaScript, asset/build, cache or permission change is authorized.

## Failing-Before Plan

Use RED → GREEN → REFACTOR:

1. Saved X/ALL fixture: rendered genuine clear action is missing on baseline,
   or the old root reset reapplies X. Follow the real link before changing it.
2. Pin duplicates, manual preference claim and missing native manual submitter.
3. Pin manual-empty falsely labelled filtered, full and AJAX.
4. Seed a healthy fixture cache: show-empty plus nonmatching search retains
   wards, but the baseline claims no inpatients and lacks the global notice.
   Include a genuinely empty/ward-only case to prevent overcorrection.
5. Capture browser before behavior with meaningful defaults and actual draft
   edits. Tooling/login/cache-unavailable failures are not valid feature RED.

## Implementation Constraints

Follow repository engineering policy in AGENTS.md and preserve existing
conventions. Prefer the smallest correct change; avoid speculative abstraction
and unrelated refactoring. Design D1–D6 is the behavior contract.

Use a small inherited adapter, not growth in the 1,948-line legacy view.
Consume its already resolved context; no second preference resolution.
Keep URL/visibility/label logic in the typed map service.
The map opt-in must not change the accepted list flag/default shared behavior.

Keep full and AJAX variants equivalent. Do not repurpose a manual-origin flag
as the only effective-predicate test. Per-ward text uses search/tags, not ward
selection alone. Do not add pre-filter patient counts or repair cache fallback.
Keep independent save, existing JS/clean Apply and legacy scoped URLs intact.

## Validation

### Focused Validation

```bash
./scripts/test.sh apps.patients.tests.test_patient_filter_layout \
  apps.patients.tests.test_ward_map_filter_actions \
  apps.patients.tests.test_ward_map_empty_states \
  apps.patients.tests.test_ward_map_tag_filters \
  apps.patients.tests.test_tag_selector_template \
  apps.patients.tests.test_tag_filter_rendering \
  apps.patients.tests.test_patient_list_filter_actions \
  apps.patients.tests.test_tag_filters \
  apps.accounts.tests.test_tag_preferences \
  apps.reports.tests.test_template_catalogue_s3 \
  apps.reports.tests.test_template_creation_s4
```

Compare preference IDs/tags/mode, membership/profile context and cache payload
before/after all GET actions. Test no specialty/default, saved-empty without a
principal, principal-only, unavailable subset/all, invalid IDs, trimmed search,
mode-only and show-empty-only. Verify anonymous/unauthorized gates and privacy
under a warm cache.

### Project-Required Gates

Run AGENTS.md and canonical scoped lint/type/format checks. Document legacy
findings by comparing baselines, not by silently suppressing them. Recheck
Markdown with both the pre-commit Prettier version and markdownlint.
No source asset/build edit is planned.

### Runtime Evidence

Execute verification.md with a healthy isolated cache, saved non-empty default
and full/AJAX rendering. Use desktop/narrow and JS/native cases.
Do not modify shared dev data/cache or restart/remount the stack.

## Acceptance Criteria

- [x] R1: Unique filter actions and informational applied summaries.
- [x] R2: Clear-all remains genuinely unfiltered under existing eligibility.
- [x] R3: Restore preserves applied map fields and discards pending drafts.
- [x] R4: Draft, native empty Apply and enhanced clean Apply work.
- [x] R5: Totals label distinguishes effective filters from origin/display.
- [x] R6: Per-ward/global empty copy and helper agree in full/AJAX rendering.
- [x] R7: Applied preference-source matrix is truthful without new persistence.
- [x] R8: Regressions pass and cache/list/reports/privacy remain unchanged.
- [x] Focused/project gates and required runtime evidence are recorded.

The visual amendment is also accepted: matching left actions at all three
widths, separate bordered map options, unchanged checkbox form ownership and
independent preference POST. Final proof: 235 focused tests (31 skips) and
30 Chrome groups; see tasks.md and the layout report. The operator authorized
these completion marks and archive after manual homologation on 2026-11-17.

## Escalation Conditions

Return BLOCKED_NEEDS_DECISION for contradictory artifacts, a new product or
architecture decision, material/unlisted expansion, public compatibility break,
persistence/migration/FSM changes, new security/privacy/clinical implications or
inability to meet acceptance. Missing healthy isolated fixtures/identity is a
blocker, not grounds to run the shared generator or accept stale-cache output.

## Evidence Report and Worker Handoff

Path: `/tmp/sirhosp-slice-PMFA-S1-report.md`.

Include READY_FOR_REVIEW or BLOCKED_NEEDS_DECISION, R-to-evidence mapping,
changed paths, RED/GREEN proof, commands/exit statuses, source/runtime identity,
fixture ownership/cleanup, expansion justification and unresolved limitations.

```text
Implement only approved PMFA-S1 using this slice and referenced artifacts.
Reconstruct fresh context; follow repository engineering policy.
Produce failing-before evidence, implement minimally and validate.
Write /tmp/sirhosp-slice-PMFA-S1-report.md and stop for review.
Do not update tasks.md, commit, push, merge, archive or start another slice.
Escalate new decisions as BLOCKED_NEEDS_DECISION with evidence.
Otherwise finish READY_FOR_REVIEW and REPORT_PATH pointing to the report.
```
