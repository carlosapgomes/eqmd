# Proposal: Specialty team tag governance and patient discovery

## Why

Patient tags need to support assistential teams without restricting access to
patients: controlled public/system classifications, leader-managed private
labels, visible audit history, and useful defaults for patient discovery.
Today the catalogue is global, filters accept one tag, the timeline omits current
tags, and the still-installed Taggit admin exposes an unrelated legacy catalogue.

## What Changes

- Treat each medical specialty as one team, with multiple members and leaders.
  Only administrators manage memberships and leadership; a user has at most one
  active specialty. Losing membership immediately removes team privileges while
  preserving membership history and preferences for a possible return.
- Extend the existing tag catalogue with independent origin (`system`/`custom`)
  and visibility (`public`/`restricted`), a specialty namespace, immutable creator,
  and transferable responsible leader. Restricted tags belong to exactly one team.
- Give administrators full catalogue governance in Django Admin. Give leaders a
  separate team page for their own responsible custom restricted tags only.
- Give each team one configurable public principal tag. All authorized users can
  see/filter it; only team members or administrators can assign/remove it.
- Distinguish active, inactive, and administratively archived tags. Archive is
  soft-delete; administrator-only restore returns the same tag inactive. Names
  remain reserved in their namespace in every state. No physical deletion or
  replacement-by-homonym workflow is introduced.
- Make patient-tag operations transactional and audited, including admin paths.
  Show current visible tags in the timeline header. For outsiders, historical
  restricted-tag operations show only a generic action, author, team and time;
  current visibility also governs older events after reclassification.
- Add searchable multi-tag selectors with ANY/ALL matching and explicit historical
  search. Store one shared list/map preference per user-specialty, including an
  intentionally empty selection; the principal tag is optional in saved settings.
- Apply specialty defaults only on initial entry. Manual filters do not silently
  save; provide explicit save, clear, and reapply-preferences actions.
- Repair map filter consistency: respect visibility, filter cached data safely,
  recalculate result totals, and avoid stale tag metadata/assignments.
- **BREAKING:** non-admin catalogue mutation, bulk removal and tag-event payloads
  become policy-checked/redacted; global tag-name uniqueness becomes namespace
  uniqueness. Keep existing catalogue IDs and legacy single-tag filter URLs.

## Capabilities

### New Capabilities

- `team-tag-governance`: catalogue classification, ownership, lifecycle, visibility
  and patient-assignment authorization.
- `patient-tag-audit`: atomic changes, stable event references, historical redaction
  and current tags on the patient timeline.
- `patient-tag-filtering`: searchable ANY/ALL filters, per-specialty preferences,
  explicit overrides and consistent patient-list/map results.

### Modified Capabilities

- `accounts`: active team membership, multiple leaders, membership-aware specialty
  switching, revocation and retention of per-specialty preferences.

## Impact

- Django/PostgreSQL migrations in accounts, patients and events; preserve existing
  tags, patient associations, event snapshots and identifiers.
- Accounts admin/profile/switching; patient catalogue/admin/assignment views and
  APIs; team tag page; timeline/list/ward/map projections; shared cache utilities.
- Existing `AllowedTag`/`Tag` remain authoritative. No Taggit migration or import
  of its unrelated rows, package removal or additional frontend dependency.
- Update misleading tag documentation and the Taggit claim in OpenSpec context
  during implementation, not as part of this proposal-only delivery.
- Restricted metadata is security-sensitive: partial implementation is not a
  production release. Deployment/migration approval is separate from this plan.

## Non-Goals

- Patient-level segregation, clinical-record permission overhaul, team membership
  expiry, supervisor account-renewal workflows, or leaders managing membership.
- Automatic tag assignment/removal on admission, discharge or specialty switching.
- Team hierarchy, cross-team restricted tags, mandatory operation justifications,
  or changing which patient statuses belong in the ward map.

## Delivery

Nine sequential TDD slices are defined in `tasks.md` and `slices/`.
The decomposition review and requirement coverage are in `slices/README.md`.
All implementation tasks remain unchecked. This change records the agreed
requirements; creating it does not authorize implementation or production work.
