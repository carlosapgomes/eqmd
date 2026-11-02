# Proposal: harden discharge report collaborative draft

## Why

The collaborative draft workflow shipped in
`2026-10-12-fix-discharge-report-collaborative-draft`
works on the happy path: the clinical team confirms
routine use (create a draft, a colleague edits it, a
third doctor finalizes it). A read-only audit with
four scouts then mapped why earlier "it does not
work" reports were plausible and where the
implementation stays fragile at the edges:

- The timeline card computes `can_edit` with the
  generic creator-only predicate, so a collaborating
  doctor never sees the edit action there, even
  though the detail page and the update view allow
  editing.
- Draft authorization depends on the nullable
  `profession_type` field (default `None`) with no
  admin guardrail, audit, or backfill; any real
  doctor stored as `None` gets 403 on both doors.
- The collaborative predicate is duplicated in the
  model method and the view helper; the enforcement
  door skips the patient-access check the display
  door performs. Convergent today only because
  patient access is permissive.
- Finalizing a draft older than 24h locks it
  immediately (window anchored at creation) with no
  warning, and the finalizer loses edit access at
  once (creator-only rule).
- Profession groups created by the post-save signal
  start empty; `setup_groups` reconciles them, but
  only when someone runs it, and drift is invisible.

Each fragility re-triggers on new users, old drafts,
or future permission tightening. This change hardens
the shipped workflow without changing its clinical
semantics.

## What Changes

1. Single collaborative predicate: one service-level
   rule used by the model method, the view helper,
   and the timeline bulk check; the timeline
   dispatches by event type for discharge-report
   edit and delete actions.
2. Explicit update-action handling: `save_draft`,
   `save_final`, and unknown/missing actions are
   handled and tested explicitly instead of falling
   through silently.
3. Clinical identity guardrails: Django admin
   requires `profession_type` for clinical users
   (superusers and User Managers exempt); a
   read-only audit command reports `NULL`
   professions and group-permission drift;
   `setup_groups` reconciliation of existing
   groups is locked with regression tests.
4. Finalization-anchored window: new `finalized_at` /
   `finalized_by` fields plus a migration with a
   behavior-preserving backfill; the 24h edit window
   counts from finalization and covers the creator
   and the finalizer (plus `change_event` holders).
5. Regression coverage for the audited gaps:
   timeline-as-collaborator, old-draft finalize,
   three-door equivalence, identity audit.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `discharge-report-actions`: single predicate,
  timeline dispatch, explicit update actions,
  finalization-anchored window.
- `accounts`: `profession_type` integrity for
  clinical users, identity auditability, group
  reconciliation contract.

## Impact

- `apps/dischargereports`: new permissions
  service, model/view delegation, finalization
  fields plus migration, display, tests.
- `apps/events`: type-dispatched bulk permission
  check, timeline tests.
- `apps/accounts`: admin validation, audit
  command, `setup_groups`/signal tests.
- One migration (S3 only): `finalized_at` /
  `finalized_by` plus backfill. S1/S2 add no
  migrations.
- Full suite green via `./scripts/test.sh`;
  markdown lint for touched docs.

## Out of Scope

- Partial/incomplete drafts: draft-tolerant
  validation changes clinical record-completeness
  behavior and needs a clinical/compliance decision
  first. Follow-up change candidate.
- Concurrency control: accepted residual risk per
  operator (sequential team flow; incident-level
  impact, audit trail preserved).
- Timeline cache redesign, patient-access
  tightening.

## Success Criteria

- A collaborating doctor sees and uses the timeline
  edit action on another author's draft; a
  non-doctor does not.
- Model, helper, and timeline predicates stay
  equivalent by construction and by test.
- No new clinical user can be created via admin
  without `profession_type`; the audit reports
  existing gaps read-only.
- Finalizing any draft (fresh or old) opens a 24h
  correction window anchored at finalization for
  creator and finalizer; `finalized_by`/`at` are
  recorded and visible; legacy finals keep
  today's verdicts.
- Full suite green; no new lint/type findings.
