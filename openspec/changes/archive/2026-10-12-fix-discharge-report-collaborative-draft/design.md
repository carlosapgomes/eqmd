# Design: fix discharge report collaborative draft

## Context

Current discharge report edit path has two doors that disagree:

- Display door: `views.can_edit_discharge_report()` plus
  template tag `can_edit_discharge_report_tag` gate the
  detail button and the timeline card. The draft branch
  reads `getattr(user, "profession", None)` and compares
  against string constants from
  `apps/core/permissions/constants.py`
  (`medical_doctor`/`resident`). `EqmdCustomUser` has no
  `profession` attribute (only `UserProfile` does) and
  stores `profession_type: int (0 = doctor, 1 = resident)`.
  Result: always false for real users.
- Enforcement door: `UpdateView.get_object()` calls
  `DischargeReport.can_be_edited_by_user()`, which allows
  drafts only for `created_by == user OR
has_perm('events.change_event')`. No profession check,
  no time window, but no collaboration either.
- Canonical profession check in this repo is
  `getattr(user, 'profession_type', None) in [0, 1]`
  (see `apps/core/permissions/utils.py`). The fix aligns
  both doors to that check.

Finalized-report and delete behavior are intentionally kept:
`Event.can_be_edited` (24h) + creator-only for finals,
`can_delete_discharge_report` / `can_be_deleted_by_user`
unchanged.

## Decisions

### D1. Draft edit check uses `profession_type in [0, 1]`

Both `can_be_edited_by_user()` (draft branch) and
`can_edit_discharge_report()` (draft branch) SHALL use
`getattr(user, "profession_type", None) in
[MEDICAL_DOCTOR, RESIDENT]` with the int constants from
`EqmdCustomUser` (`0`, `1`), combined with
`can_access_patient()`. Rejected: string constants from
`core.permissions.constants` (wrong type for this model).

### D2. Single rule, two doors kept consistent

The model method remains the enforcement authority used
by `UpdateView`; the view helper remains the display
authority used by detail/timeline. Both SHALL implement
the same draft predicate. No new service layer: the
predicate is model-local and view-local authorization,
consistent with current architecture.

### D3. Finalize is a consequence of edit, not a new permission

`UpdateView.form_valid()` already flips `is_draft` on
`save_final`. Any doctor/resident who passes D1 can
therefore finalize. No separate finalize permission,
no `draft_promoted_*` bookkeeping for UI drafts
(`draft_expires_at` stays null for manual drafts).

### D4. Finals and deletes unchanged

Finalized reports: `can_be_edited` (24h) plus creator or
`change_event` holders. Deletes: creator or
`delete_event` holders for drafts; standard window plus
override for finals. Creation gate (`can_access_patient`
in `CreateView.dispatch`) unchanged.

### D5. Tests are updated, not just added

`test_can_be_edited_by_user_different_user` and
`test_unauthorized_user_cannot_edit` currently assert the
broken behavior (plain second user blocked on a draft).
They SHALL be reworked: plain second doctor allowed,
non-doctor still blocked. New tests use
`profession_type=0/1` users and an old-draft fixture
(`created_at -25h`) to prove no time limit.

## Risks and mitigations

- Wider edit surface for drafts: intended by the clinical
  workflow; audit trail (`updated_by`, simple history)
  already records who touched the draft. No change to
  final-document immutability.
- String/int constant confusion recurs: mitigate by
  referencing `EqmdCustomUser` ints directly and adding
  a comment pointing at `core.permissions.utils` usage.

## Slices

1. `slice-001-collaborative-draft-edit.md` — shared draft
   predicate, model + helper fix, edit/re-save coverage.
2. `slice-002-collaborative-finalize-and-guards.md` —
   finalize by another doctor, non-doctor block, final
   window and delete regression, old-test rework.
