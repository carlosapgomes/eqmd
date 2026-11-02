# Design: Specialty team tag governance

## Context

See `proposal.md` for motivation and scope. The current catalogue is
`apps/patients/models.py:AllowedTag`; `Tag` is a patient-owned association.
`UserSpecialty` already links users and specialties, and
`UserProfile.current_specialty` is the selected context. Do not repurpose the
unrelated account-renewal `EqmdCustomUser.supervisor` field or profession-based
Django groups as clinical teams.

Current hazards include unrestricted catalogue queries in patient/list/ward
partials, snapshots containing tag names in event descriptions, non-transactional
assignment/event writes, and a global JSON map cache. Existing archived tag
lookup needs `all_objects`, but only after requester visibility is applied.
The original models/views are large: introduce focused modules rather than
moving whole legacy modules merely to meet this change's needs.

## Goals / Non-Goals

Deliver the four capability contracts in `specs/` without changing universal
patient access, professional permissions unrelated to tags, admission lifecycle,
or the current map population (non-deleted INPATIENT patients with a ward).
No new tagging engine, team entity, package, or production operation is required.

## Decisions

### D1. Durable membership, not permission groups

Extend `UserSpecialty` with active-membership and leader state and actor/time
history. Multiple rows can be leaders for the same specialty. Existing rows
backfill as active, non-leader memberships; preserve `assigned_at`/`assigned_by`.
Membership removal in ordinary admin flows deactivates the row rather than
hard-deleting it. A leader must have active membership in an active specialty.

Validate membership at each request, not just at login or when switching.
Revocation clears an invalid current-specialty selection and denies leadership
immediately. If no current context remains valid, do not silently pick a different
team for filtering. Returning membership reuses the retained identity/preferences;
restoring membership does not automatically restore leadership.

Alternative rejected: membership deletion plus preferences cascades would lose
settings that the operator explicitly wants to retain.

### D2. Catalogue identity, namespace and principal relationship

Keep current integer catalogue IDs and patient-assignment UUIDs. Extend
`AllowedTag` with:

- origin: `system` or `custom`;
- visibility: `public` or `restricted`;
- nullable specialty namespace; restricted tags require exactly one specialty;
- immutable `created_by` plus nullable `responsible_user` for transferable control;
- latest activation/deactivation/restoration actor and timestamp fields, alongside
  existing `deleted_by`/`deleted_at` and complete immutable transition history.

Use the specialty abbreviation in display, not as a concatenated stored name.
Public tags without a specialty share a global namespace. Reserve normalized
names (`Lower(Trim(name))`) within the namespace across all lifecycle states;
PostgreSQL 15 must also enforce uniqueness in the null/global namespace. Preflight
case/whitespace collisions; never merge or rename clinical classifications silently.

Add a nullable `MedicalSpecialty.principal_tag` reference. It is singular, references
its own namespace, and must be public. Enforce this across ordinary model/service
and admin writes. A tag referenced as principal cannot be made restricted or moved
to another namespace until an administrator explicitly changes the mapping.
Specialty/tag references preserve historical rows rather than cascading deletion.
Existing specialties remain unmapped until an administrator configures them; do
not infer mappings from labels or automatically create tags.

### D3. Three states, one identity

Reuse `is_active` and `is_deleted` with canonical states:

| State    | is_active | is_deleted | New assignment | Automatic preference |
| -------- | --------- | ---------- | -------------- | -------------------- |
| Active   | true      | false      | Policy checked | Eligible             |
| Inactive | false     | false      | Denied         | Ignored with warning |
| Archived | false     | true       | Denied         | Ignored with warning |

Archive uses the user label "Arquivar" and is administrator-only. Restore is
administrator-only and returns the same row inactive; it never clones, recreates
or immediately reactivates it. Store the latest action actors/times and history
without requiring a reason. Preserve assignments and principal mappings. A
missing/unusable principal produces a warning and no implicit replacement.

Override catalogue-specific admin actions and query/bulk mutation paths; inheriting
`SoftDeleteModel.restore()` unchanged would preserve the wrong active state.
Do not globally alter every soft-delete model. No user-facing hard delete exists.

### D4. Authority and visibility are separate

"Administrator" means an active authorized Django-admin operator, not any account
with `is_staff`: superusers qualify; delegated staff also require the relevant
existing catalogue view/add/change/delete permissions for each operation.
Retain the existing patient-access and clinical mutation gates for assignment.
Leadership does not grant general Django Admin or user-management permissions.

A team leader creates only custom restricted tags in that team; the server derives
origin, team and initial responsibility. Only the responsible active leader can
edit/deactivate/reactivate them. Changing origin, visibility, namespace,
responsibility or archived state is administrative. After transfer, the former
responsible user loses management rights regardless of immutable authorship.
Transfer recipients must currently be leaders/members of the same team.

All public tags are readable; restricted metadata requires current membership
in its team or administrator authority. Read visibility is the union of all active
memberships, not just current specialty. This governs selectors, counts, HTML data
attributes, APIs, badges, error messages, print and cached projections.

Assignment/removal additionally requires per-tag authorization. Principal tags
require team membership or administrator override even though public. Restricted
tags require their membership; non-principal public tags retain the clinical
mutation baseline. Inactive/archived associations can be removed by the same
per-tag authority, but cannot be newly assigned. Bulk removal operates only on the
caller's authorized association set and preserves every other team's association;
label its UI accordingly rather than promising to erase hidden tags.

### D5. Atomic writes and stable event identity

Put policy/orchestration in focused services under `apps/patients/services/` and
membership services under accounts. Use `transaction.atomic()` for catalogue
change/history and assignment/event pairs; lock/revalidate the relevant catalogue
and membership/ownership state to avoid authorization races. Use database unique
constraints for duplicate assignment/name races. No failed event write may leave
a changed association; denied writes have no side effects.

Introduce structured tag-event references (for example an `EventTagReference`
relation) keyed by event and catalogue identity with action-time snapshots and team
attribution. Keep existing subclass snapshot fields for compatibility, but route
all user-facing output through a requester-aware projection. Bulk references are
per-tag, not a comma-separated string that cannot be safely redacted.

Outsiders see a generic restricted-tag action with author, team abbreviation and
time, never hidden names, colors, descriptions, notes or catalogue/association IDs.
Current visibility governs historical output, including public-to-restricted
changes and membership revocation. Render mixed bulk events from visible references
plus generic restricted actions, never the legacy raw `tag_names` field. Audit
events are not editable/deletable through ordinary clinical-event workflows.

Backfill legacy references only for unambiguous snapshot-to-catalogue matches.
Because historical renames can invalidate a name-only guess, preflight must use
retained catalogue history as well; conflicting or insufficient evidence remains
unresolved. Unresolved legacy events remain intact and are redacted for non-admin
viewers; admin diagnostics expose aggregate unresolved counts, not patient data.
Do not guess identity or rewrite old descriptions. All admin assignment entry
points must call the same audited workflow; prevent direct bypassing inline/bulk
writes. Do not retrofit general patient audit or unrelated event permissions.

### D6. Explicit filter state and preference precedence

Store a separate preference keyed by the retained user-specialty membership with
selected catalogue IDs and `any`/`all` mode. The record's absence means "not yet
configured"; an existing empty selection means "intentionally no tag filter".
Persisted preferences are shared by patient list and map. Before the first save,
use the valid current specialty's principal tag and ANY mode. The user may omit
the principal from any saved selection.

Request precedence:

1. Explicit manual filter state, including an explicitly empty tag selection.
2. Saved preference for the valid active specialty, if present.
3. Valid active specialty's principal tag as initial fallback.
4. No tag filter; warn when a configured default is unavailable.

Use repeated `tags=<id>` parameters, `tag_mode=any|all`, and an explicit
`tag_filter=manual` marker to distinguish manual-empty from initial entry. Continue
to accept legacy `tag=<id>` URLs as explicit ANY single-tag filters; a present
empty `tag=` is explicit manual-empty state. Clearing emits manual-empty state;
reapply preferences removes manual state. Preserve repeated
parameters through pagination, refresh, badge removal and links. Never store a
preference on GET; explicit CSRF-protected save applies to the active membership
only and persists tags plus mode together.

Revalidate every request and save. Automatic defaults omit inactive, archived or
inaccessible IDs and show a generic warning; no IDs or names of inaccessible tags
are disclosed. If none remain, omit the tag predicate (no empty ALL/ANY trap).
Historical manual selection can include visible inactive/archived IDs, with status
labels; an inaccessible/invalid explicit ID yields a generic validation error,
not a silent wider search. Both modes run against distinct patients: ANY is union,
ALL requires every selected identity. Status/name/ward filters remain conjunctive.

A searchable, paginated selector shows active visible tags first and offers
"Incluir tags antigas" for inactive/archived entries. It cannot create tags.
Historical choices are for filtering, not new assignments or automatic defaults.

### D7. Shared cache cannot be an authorization decision

Keep a global base map only as a structural cache. Apply current catalogue,
assignment and requester visibility before rendering; do not reuse cached names,
notes or visibility decisions. Rehydrate tag metadata and patient associations for
the map's bounded patient ID set in batched queries. This makes revocation,
reclassification and assignment changes effective without waiting for cache expiry.
Apply filters afterwards and recalculate patient/ward totals from results.

The map refresh remains a GET/reload, not an admin cache rebuild operation.
The existing stale-base-cache handling stays explicit; it must not silently show
unfiltered results. Keep the INPATIENT-with-ward population unchanged and explain
why an outpatient tag can produce zero map results. Test warm-cache cross-user
requests and every current tag-rendering surface, not only the main map HTML.

### D8. Incremental delivery and compatibility

Nine slices build a single release candidate; do not deploy intermediate slices.
S1 delivers memberships; S2 catalogue identity/namespaces/principal configuration;
S3 administrative lifecycle/responsibility; S4 audited assignment writes and stable
event references; S5 request-time read privacy and current timeline context;
S6 leader self-service; S7 list filters; S8 durable defaults; S9 map parity and
final integration. See `slices/README.md` for dependencies and requirement coverage.

This replaces the original oversized catalogue and combined write/read slices,
without changing product contracts or architecture. S2-S4 are not safe restricted
metadata release checkpoints: S5 must close every reader, including existing
single-tag filter inputs and cached metadata. S5 privacy acceptance does not
certify current map-assignment freshness or multi-tag/default parity; S9 owns
those checks. No new feature flag or intermediate deployment mechanism is added.

Do not import Taggit test rows into `AllowedTag`. Package/table removal is deferred.
During implementation, update current operational docs and correct
`openspec/config.yaml`'s "Taggit - Patient tagging system" claim; preserve historical
plans as history. No edits outside this change are part of the planning delivery.

## Migration Plan

1. In development, generate additive migrations; use historical migration models
   rather than runtime services. Split cross-app references into ordered migrations
   so accounts and patients do not acquire a circular dependency.
2. Provide read-only preflight for normalized-name collisions, invalid associations
   and legacy event resolution. Block ambiguous transformations; operator decisions
   and production migration execution need separate approval.
3. Backfill catalogue rows as public/custom in the global namespace, retaining IDs,
   flags, authors, assignments and history. Map archived rows to archived/inactive;
   do not invent responsible leaders, principal tags or team membership.
4. Existing membership rows become active/non-leader. Create no preferences during
   backfill; use the absence-vs-empty contract. Add event references conservatively.
5. Verify migration tests on PostgreSQL, permission/redaction matrix, warm-cache
   cases, browser/mobile behavior, full suite, lint/types and frontend build.
6. Obtain deployment approval, backup and migration plan before production changes.
   Configure leaders/principal mappings explicitly through admin after release.

## Risks / Trade-offs

- Restricted metadata can leak through snapshots/DOM/cache: central projections
  and negative tests on every inventoried path are a release gate.
- Missing authorization in a legacy helper: migrate callers or deny unsupported
  paths; hiding buttons alone is never sufficient.
- Existing giant modules: extract focused feature modules while preserving import
  compatibility, with no unrelated model/view reorganization.
- Name normalization can reveal legacy collisions: fail preflight without merging.
- Retained inactive memberships/preferences add rows: necessary for reversible team
  participation; do not hard-delete them to simplify admin UI.
- A global map cache needs a live batched overlay: accept the bounded database cost
  for immediate privacy correctness rather than TTL-based authorization.

## Rollback

Do not downgrade to the legacy unrestricted readers after restricted tags exist.
A safe operational rollback disables the new tag surfaces while preserving the
new schema, events and associations, or restores an approved consistent backup.
Any schema reversal, data restoration or service intervention requires human
approval. Never solve rollback by dropping tags, references or audit tables.
