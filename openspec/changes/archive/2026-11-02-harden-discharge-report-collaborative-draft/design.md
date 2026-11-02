# Design: harden discharge report collaborative draft

## Context

The 2026-10-12 change fixed two of three
authorization doors for discharge-report drafts:
`DischargeReport.can_be_edited_by_user()` (model,
used by `UpdateView.get_object`) and
`can_edit_discharge_report()` (view helper, used by
the detail context). Both implement creator OR
`events.change_event` OR `profession_type in
(0, 1)` for drafts with no time limit. The third
door, the patient timeline, was missed:
`apps/events/views.py::_bulk_permission_check`
computes `event_data.can_edit` with the generic
`can_edit_event` (creator-only, 24h) for every event
type, and `event_card_dischargereport.html` renders
the pencil from that flag. The timeline queryset
itself correctly includes discharge drafts
(`with_drafts()` plus the `DISCHARGE_REPORT_EVENT`
filter).

`EqmdCustomUser.profession_type` is a
`PositiveSmallIntegerField(null=True, blank=True)`
with no default, so real users default to `None`
and fail the collaborative predicate. The admin
exposes the field but does not require it; the
`assign_user_to_profession_group` signal strips
`None` users from all profession groups;
`setup_groups` reconciles permissions on existing
groups (unconditional `permissions.set`) but runs
only manually, so drift is silent.

Finalized reports anchor the 24h window at
`created_at` (`Event.can_be_edited`); finalizing
preserves `created_at`, so a draft older than 24h
finalizes into an immediately immutable report, and
a non-creator finalizer loses edit access at once.

Repo policy (`docs/workflows/coding-standards.md`)
prefers the View -> Service -> Model flow with
business rules in `services/`; both `views.py`
files near the 300-line soft limit favor
extraction.

## Goals / Non-Goals

**Goals:**

- One collaborative predicate, three doors
  consistent by construction.
- Timeline edit/delete actions correct for
  discharge drafts.
- Identity integrity guardrails without touching
  the user schema.
- 24h correction window anchored at finalization.
- Audited gaps covered by regression tests.

**Non-Goals:**

- Partial-draft validation relaxation.
- Concurrency/cache redesign.
- Broad schema changes beyond the two
  finalization fields.

## Decisions

### D1. Predicate lives in a dischargereports service

New `apps/dischargereports/services/permissions.py`
owns `can_edit_discharge_report(user, report)` and
`can_delete_discharge_report(user, report)` (moved
from `views.py`, same semantics). The model methods
delegate to the service; `views.py` keeps thin
re-exports for existing importers (detail view,
template tags); the timeline bulk check calls the
service for discharge-report events. Rationale:
matches the mandated View -> Service -> Model flow,
shrinks files near the size limit, and turns future
divergence into a structural rather than silent
behavioral drift. Rejected: model-as-authority (the
model cannot own the patient-access check cleanly)
and helper-as-authority (the events timeline
importing from discharge views inverts layering).

### D2. Timeline dispatches by event type

`_bulk_permission_check` keeps the generic path as
default and branches for `event_type ==
DISCHARGE_REPORT_EVENT` (events are
`select_subclasses()`, so the service receives a
real `DischargeReport`). Both `can_edit` and
`can_delete` dispatch; the card template is
unchanged (it already reads the flags). Same
per-event call complexity as today, no N+1 change.

### D3. Admin requires profession_type, narrowly

Django admin user forms require `profession_type`
unless the user `is_superuser` (bypasses draft
checks via `has_perm` anyway) or belongs to
`User Managers` (administrative staff with no
clinical access and no profession choice). The model
field stays nullable: no migration, no backfill
risk for legitimate `None` holders. If the
exemption check proves brittle under test, fall
back to warning-only and escalate (S2).

### D4. Audit is read-only and separate from repair

A new `audit_clinical_identity` management command
reports, without writing: active users with `NULL`
`profession_type` (excluding superusers and `User
Managers` members), profession groups missing
expected permissions, and non-exempt users in no
profession group. Repair stays a human/admin
action. Rationale: no silent permission mutation
in a clinical system.

### D5. setup_groups reconciliation becomes contractual

Current `setup_groups` already reconciles existing
groups (`get_or_create` plus unconditional
`permissions.set`). This change adds a spec
requirement and regression tests locking that
behavior (a signal-created empty group gains its
correct permissions after the command runs). No
command logic change expected.

### D6. Window anchored at finalization (operator-approved)

New `DischargeReport.finalized_at` (nullable
datetime) and `finalized_by` (nullable FK to the
user model, `SET_NULL`, related name
`finalized_discharge_reports`). The draft-to-final
flip sets both (`now` + request user); reverting a
final back to draft via `save_draft` (existing
reopen path) clears both, so the next finalize
re-anchors. Finals are editable within 24h of the
anchor by the creator OR the finalizer (plus
`events.change_event` holders, still window-bound).
Null-anchor fallback: a final with `finalized_at`
null behaves exactly as today (`created_at`
anchor). Migration backfills legacy finals with
`finalized_at = created_at` and `finalized_by =
created_by`, preserving today's verdicts row for
row; drafts stay null.

Rationale for the union (creator OR finalizer): it
preserves every right creators hold today (no one
loses anything) while granting the finalizer the
correction window the operator requested; the wider
surface is bounded by the 24h window and the
`updated_by` + history audit trail. Considered and
rejected: finalizer-only (strips the creator's
rights in collaborative flows) and creator-only
re-anchored (keeps the reported frustration: the
finalizer still could not fix a typo). Flipping to
finalizer-only later is a one-predicate-line change
if the clinic prefers it.

Delete semantics are deliberately unchanged: finals
keep the creation-anchored standard deletion window
(conservative for a destructive action), locked by
a regression test.

## Risks / Trade-offs

- Moving helpers to services touches importers;
  mitigate with re-exports and a focused test run.
- Admin validation could surprise admins creating
  service accounts; the superuser/User-Manager
  exemptions plus the audit command cover the known
  cases; unknown cases escalate per S2.
- Migration backfill runs over existing finals;
  mitigate with a row-count-capped data step and
  a staging run before production. Rollback is a
  plain backward migration: the fields hold
  derived data and pre-change code ignores them.
- Two editors (creator + finalizer) widen the
  final-edit surface; bounded by 24h and audit
  trail, and flippable to finalizer-only in one
  line if the clinic prefers.
- Partial drafts stay impossible (parked): re-save
  still needs a complete form. Documented as a
  known limitation with a follow-up pointer.

## Slices

1. `slice-001-single-predicate-timeline-dispatch.md`
   — service predicate, three-door consistency,
   timeline fix, explicit actions.
2. `slice-002-clinical-identity-guardrails.md` —
   admin requirement, audit command,
   reconciliation lock-in.
3. `slice-003-finalization-window-anchoring.md` —
   migration, anchor switch, display, tests.
   Depends on S1 (predicate lives in the service).
