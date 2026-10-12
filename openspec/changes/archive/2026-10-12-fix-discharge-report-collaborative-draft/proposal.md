# Proposal: fix discharge report collaborative draft

## Why

The discharge report draft workflow was designed for collaboration:
one doctor creates a draft, any doctor/resident edits and re-saves
it as draft, until another doctor/resident finalizes and issues
the document.

That contract is documented in
`can_edit_discharge_report()` (`Drafts: Any doctor/resident can
edit anytime`) but it does not work. A draft created by user A
cannot be edited by user B today: the detail button stays hidden
and `UpdateView` returns 403. Collaborative finalization by a
second doctor is therefore impossible without the Django
`events.change_event` permission.

Root causes confirmed in code:

- The view helper checks `getattr(user, "profession")` against
  string constants (`medical_doctor`/`resident`), but
  `EqmdCustomUser` only has `profession_type: int (0/1)`.
  The check is always false.
- The real enforcement, `can_be_edited_by_user()`, requires
  `created_by == user OR has_perm('events.change_event')`
  for drafts, blocking plain doctors/residents.
- Existing tests lock the broken behavior
  (`test_can_be_edited_by_user_different_user`,
  `test_unauthorized_user_cannot_edit`).

## What Changes

1. Draft edit rule: any authenticated doctor/resident
   (`profession_type in [0, 1]`) with patient access can edit
   a discharge report draft at any time, re-save as draft,
   with no 24h window.
2. Collaborative finalize: any doctor/resident who can edit
   the draft can finalize it (`save_final` flips
   `is_draft` to false).
3. Single rule in both doors: fix `can_be_edited_by_user()`
   and `can_edit_discharge_report()` to use the same
   `profession_type` check; detail, timeline card, and
   `UpdateView` stay consistent.
4. Guards stay strict: finalized reports keep the 24h
   creator-only rule; delete rules unchanged; non-doctors
   still cannot edit drafts; creation gate unchanged.
5. Tests: replace blocking assertions with collaborative
   coverage (edit by other doctor, old draft still editable,
   finalize by other doctor, non-doctor blocked, final
   window preserved).

## Out of Scope

- Database schema changes: zero migrations by design.
- Creation permission gate (stays as today).
- Copy/duplicate of reports or drafts.
- Bot drafts expiry (36h) and cleanup command.
- Other event types (daily notes, H&P, notes).
- New Django permission objects.

## Success Criteria

- Doctor B can open, edit, re-save as draft, and finalize
  a draft created by doctor A, including drafts older
  than 24h.
- Non-doctor (nurse/physio/student) cannot edit drafts.
- Finalized reports remain editable only by the creator
  within 24h (or `change_event` holders).
- Delete behavior unchanged for drafts and finals.
- Full suite green with no new lint/type findings.
