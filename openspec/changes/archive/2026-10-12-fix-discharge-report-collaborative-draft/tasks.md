# Tasks: fix discharge report collaborative draft

## 1. Slice 001 — collaborative draft edit

- [x] 1.1 Fix the shared draft predicate in
      `apps/dischargereports/models.py`
      (`can_be_edited_by_user` draft branch) and
      `apps/dischargereports/views.py`
      (`can_edit_discharge_report` draft branch) to allow any
      doctor/resident (`profession_type in [0, 1]`) with patient
      access, with no time limit, per
      `slices/slice-001-collaborative-draft-edit.md`.
- [x] 1.2 TDD: other-doctor draft `GET`/`POST`, backdated
      draft still editable, detail edit-action visible.
      RED → GREEN → REFACTOR; focused suites green.
- [x] 1.3 Rework the model blocking assertion
      (`test_can_be_edited_by_user_different_user` in
      `test_models.py`) to the new rule; full suite green;
      no new findings.

Contract: `slices/slice-001-collaborative-draft-edit.md`

## 2. Slice 002 — collaborative finalize and guards

- [x] 2.1 Prove and lock finalize-by-other-doctor
      (`save_final` flips `is_draft`) on top of the S1
      predicate, per
      `slices/slice-002-collaborative-finalize-and-guards.md`.
- [x] 2.2 TDD: non-doctor draft edit denied and hidden;
      finalized report stays creator-only within 24h and
      locked after 25h; delete behavior unchanged.
      RED → GREEN → REFACTOR.
- [x] 2.3 Rework the integration blocking assertion
      (`test_unauthorized_user_cannot_edit` in
      `test_integration.py`) with explicit `profession_type`
      fixtures (allowed collaborator doctor, denied
      non-doctor); full suite green; no new findings.

Contract:
`slices/slice-002-collaborative-finalize-and-guards.md`
