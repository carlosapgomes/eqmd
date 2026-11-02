# S5: Privacy-safe readers and current timeline tag context

## Identity and objective

Change: `add-specialty-team-tag-governance`; tasks 5.1-5.3 in
[../tasks.md](../tasks.md). Predecessor: accepted S4. Deliver authorized tag
presentation across every existing reader, with generic historical actions for
outsiders and current visible tags in the patient timeline header.

## Read first

- [Shared execution/report contract](README.md), `AGENTS.md`,
  `PROJECT_CONTEXT.md`, repository coding standards.
- [Design D4-D5 and D7-D8](../design.md),
  [visibility requirements](../specs/team-tag-governance/spec.md),
  [audit presentation requirements](../specs/patient-tag-audit/spec.md).
- S4 event references/write services and S2/S3 catalogue policy.
- `apps/events/views.py`, `models.py`, `admin.py`, event excerpt/template helpers;
  patient list/detail/ward/map/tag API readers; `apps/core/utils/cache.py`.

## Requirements and evidence

- **R1:** Current visibility/union of memberships governs every response. Hidden
  metadata/IDs never appear in badges, lookup options, data attributes, counters,
  errors, JSON, print or cache output. Evidence: explicit reader inventory and
  member/outsider/revoked/administrator payload-negative assertions.
- **R2:** Single/mixed-bulk events use stable references and current policy;
  historical public-to-restricted changes and unresolved legacy events fail
  closed without rewriting stored snapshots. Evidence: HTML/JSON/print cases.
- **R3:** Timeline header displays current visible tags with historical state
  labels on desktop/mobile, distinct from removed historical assignments.
  Evidence: rendered header and browser fixture matrix.
- **R4:** Existing single-tag filter inputs reject inaccessible IDs, and warm cache
  metadata is reprojected per requester rather than trusted. Evidence: forged
  legacy filters, cross-user cache and immediate revocation/reclassification cases.

## Expected blast radius

Allowed production paths:

- New `apps/patients/services/tag_projection.py`; existing `tag_policy.py`;
  `apps/patients/views.py` readers and mutation response projections, `admin.py`,
  `templatetags/patient_tags.py`.
- `apps/events/views.py`, `admin.py`, `templatetags/event_tags.py`,
  `services/tag_audit.py`; `models.py` only for projection-safe presentation seams,
  not a new schema or changing stored snapshots.
- `apps/core/templatetags/permission_tags.py`, `utils/cache.py`,
  `permission_demo.py`, `test_views_role_permissions.py`.
- Patient templates: `patient_list.html`, `ward_detail.html`,
  `ward_patient_map.html`, `ward_patient_map_tree_only.html`,
  `tags/patient_tags.html`, `partials/tag_management.html`,
  `partials/tag_management_widget.html`, `partials/patient_tag_badge.html`,
  all beneath `apps/patients/templates/patients/`.
- Event templates: `patient_timeline.html`, `patient_events_list.html`,
  `user_events_list.html`, `widgets/recent_events.html`,
  `partials/event_card_base.html`, `partials/event_card_default.html`,
  new `partials/event_card_tag_action.html`, beneath
  `apps/events/templates/events/`.
- `apps/core/templates/core/object_level_permissions_test.html`,
  `permission_test.html`; new `templates/components/_patient_tag_badges.html`.

Tests: new `apps/patients/tests/test_tag_visibility.py`,
`apps/events/tests/test_tag_audit_projection.py`,
`apps/core/tests/test_cache_tag_privacy.py`; existing patient tag visualization,
navigation and core cache helper tests for impacted readers.
Docs: new `docs/patients/tag-privacy-surfaces.md`,
`docs/patients/tags_management.md`, `docs/security/audit-history.md`,
`docs/permissions/README.md`, `apps/core/permissions/PERMISSIONS.md` tag rules only.

No catalogue/event schema, leader page, multi-tag selector or preference work.
S9 owns live cache-assignment freshness, result totals and final map parity;
S5 owns current visibility of every field returned from that cache now.

## Failing-before plan

Inventory readers with `git grep` before editing and map each response variant
to a deterministic test. Capture RED exposing a restricted name in an existing
API, event excerpt, widget, HTML data attribute and cached full/partial map.
Include an outsider's direct legacy filter URL, not only hidden dropdowns.

## Implementation constraints

All readers consume requester-aware projections; CSS/client-side concealment is
not evidence. Current catalogue/membership lookup must override stale cached tag
labels/visibility before serialization, and must not mutate shared cached data
for another requester. Old single-tag selectors remain single-tag until S7, but
must enforce visibility now. Unknown/private filter IDs produce generic errors,
not an inferential patient result set. No extra schema or snapshot rewrite.

## Validation

Focused:

```bash
./scripts/test.sh apps.patients.tests.test_tag_visibility
./scripts/test.sh apps.events.tests.test_tag_audit_projection
./scripts/test.sh apps.core.tests.test_cache_tag_privacy
./scripts/test.sh apps.patients.tests.test_tag_visualization
```

Project gates: shared contract and `AGENTS.md`. Runtime evidence: compare the same
fixture profile/list/ward/timeline/map plus event JSON and print HTML as member
and outsider, then revoke membership and reclassify a public tag. Show current
header badges on desktop/mobile. No real patient output in evidence.

## Acceptance criteria

- [ ] R1: each inventoried reader has positive and payload-negative evidence.
- [ ] R2: mixed/legacy/historical events are safe under current policy.
- [ ] R3: current header badges and inactive/archived labels are proven.
- [ ] R4: forged filter URLs and warm full/partial cache cannot bypass visibility.
- [ ] Reader inventory/docs are complete; no unresolved reader is excluded.
- [ ] S9 freshness/parity and final deployment gates remain explicitly open.

## Escalation and evidence report

Apply shared conditions. An unlisted reader, missing identity information or new
privacy decision requires a contract amendment, not silent omission. Report
`/tmp/eqmd-team-tags-slice-005-report.md` with R1-R4 evidence, complete reader
inventory, negative payload checks and required project/runtime results.

## Worker handoff

Implement only approved S5 from canonical artifacts and accepted S4 code.
Do not update `tasks.md`, commit, push, merge, deploy, archive or start S6.
Return `READY_FOR_REVIEW` with `REPORT_PATH`, or `BLOCKED_NEEDS_DECISION` with
reader evidence and the decision required.
