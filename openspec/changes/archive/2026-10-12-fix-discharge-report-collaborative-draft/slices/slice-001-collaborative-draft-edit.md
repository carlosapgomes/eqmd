# Slice 001: collaborative draft edit

## Identity

- Slice: S1 (`slice-001-collaborative-draft-edit.md`).
- Change: `fix-discharge-report-collaborative-draft`.
- Task: `tasks.md` section 1.

## Objective

Any doctor/resident can open, edit, and re-save another
doctor's discharge report draft, with no time limit.

## Read first

- `AGENTS.md`
- `PROJECT_CONTEXT.md`
- `openspec/changes/fix-discharge-report-collaborative-draft/proposal.md`
- `openspec/changes/fix-discharge-report-collaborative-draft/design.md`
  (decisions D1, D2, D5 are binding for this slice)
- `openspec/changes/fix-discharge-report-collaborative-draft/specs/dischargereports/spec.md`
  (draft-editing requirement and visibility requirement)
- `apps/dischargereports/models.py`
  (`can_be_edited_by_user`)
- `apps/dischargereports/views.py`
  (`can_edit_discharge_report`, `DischargeReportUpdateView`,
  `DischargeReportDetailView`)
- `apps/dischargereports/templatetags/dischargereport_tags.py`
- `apps/accounts/models.py`
  (`EqmdCustomUser.profession_type`, `MEDICAL_DOCTOR = 0`,
  `RESIDENT = 1`)
- `apps/core/permissions/utils.py`
  (`can_access_patient`, `profession_type in [0, 1]` pattern)
- `apps/dischargereports/tests/test_models.py`
- `apps/dischargereports/tests/test_views.py`

Follow the repository engineering policy in `AGENTS.md`
and preserve existing conventions. Prefer the smallest
correct change; avoid speculative abstraction and
unrelated refactoring.

## Requirements

- R1: A doctor/resident who did not create the draft can
  `GET` the update view (200) and `POST` a re-save as
  draft; the report stays `is_draft=True`. Evidence:
  view test with two `profession_type=0/1` users.
- R2: A draft older than 24h (`created_at -25h`) remains
  editable by the creator and by another doctor/resident.
  Evidence: model + view test with backdated `created_at`.
- R3: The detail/timeline edit predicate returns true for
  a collaborating doctor and the edit button is visible.
  Evidence: helper assertion and/or detail response
  containing the update URL.
- R4: The model blocking assertion
  (`test_can_be_edited_by_user_different_user`) is reworked
  to the new rule (collaborator doctor allowed). The
  integration blocking assertion stays for S2. Evidence:
  updated model test passes.

## Expected blast radius

- Likely: `apps/dischargereports/models.py` (draft branch
  of `can_be_edited_by_user`), `apps/dischargereports/views.py`
  (draft branch of `can_edit_discharge_report`),
  discharge report model/view tests.
- Sensitive, do not change without escalation: finalized
  report rule, delete predicates, creation gate,
  migrations/schema, other event types, bot expiry.
- Previous behavior that must hold: creator can always
  edit own draft; finals still locked per 24h rule.

## Failing-before plan

Failing-before evidence (run before implementing):

- targeted test: other doctor `GET` update view of a
  draft → today 403, after fix 200.
- targeted test: `can_be_edited_by_user(other_doctor)`
  on a draft → today false, after fix true.
- targeted test: backdated draft edit by creator →
  confirm current vs fixed behavior in the report.

Record commands, exit codes, and failure output in the
evidence report.

## Implementation constraints

- Use `getattr(user, "profession_type", None) in (0, 1)`
  (or `EqmdCustomUser` constants); do not use the string
  constants from `core.permissions.constants`.
- Keep `can_access_patient()` as a precondition in the
  view helper; keep enforcement in the model method for
  `UpdateView` and display in the helper for detail/card.
- No schema/migration changes; `draft_expires_at` stays
  null for UI drafts.
- Do not implement finalize-by-other beyond keeping the
  existing `save_final` path reachable (S2 covers it).
- Do not touch files outside the slice blast radius
  without justification.

## Validation

Focused validation (worker runs during the slice):

- `./scripts/test.sh apps.dischargereports.tests.test_models`
- `./scripts/test.sh apps.dischargereports.tests.test_views`
- `./scripts/test.sh apps.dischargereports` (slice scope)

Project-required gates: see `AGENTS.md` (full suite via
`./scripts/test.sh` before handoff; markdown lint for
touched docs). Do not replicate global gates here beyond
referencing them.

Runtime/verification evidence: `GET`/`POST` update-view
flow for the collaborating doctor, with status codes and
`is_draft` state before/after.

TDD is required: RED → GREEN → REFACTOR for R1..R3.

## Acceptance criteria

- [ ] Other doctor gets 200 on draft update `GET` and
      302 on draft re-save `POST`; report stays draft.
- [ ] Backdated draft (>24h) editable by creator and by
      other doctor.
- [ ] Edit predicate/button visible to collaborating
      doctor on detail view.
- [ ] Focused suites pass; full suite green; no new
      ruff/mypy findings vs baseline.
- [ ] Evidence report written with failing-before and
      passing-after proof.

## Escalation conditions

Stop with `BLOCKED_NEEDS_DECISION` and evidence if any
of these appear: contradiction in proposal/design/spec,
need for a new permission object or schema change, need
to change creation/final/delete rules to satisfy the
slice, new security/privacy/clinical implication, or
inability to satisfy R1..R3 without scope expansion.

## Evidence report

Path: `/tmp/<APP_VIZINHA>-slice-S1-report.md`.

Include: status (`READY_FOR_REVIEW` or
`BLOCKED_NEEDS_DECISION`), requirements → evidence,
changed files, failing-before evidence, passing-after
evidence, commands with exit status, runtime evidence,
blast-radius expansion with justification, risks,
and open decisions for humans.

## Worker handoff

Implement only this approved slice. Treat the slice and
referenced OpenSpec artifacts as the implementation
contract. Reconstruct context from the listed files; do
not rely on prior conversation. Follow the repository
engineering policy. Produce failing-before evidence,
implement the smallest correct change, run focused
validation, and produce the required evidence report.
Do not update `tasks.md`, commit, push, merge, archive,
or start another slice. If a new decision is required,
stop with `BLOCKED_NEEDS_DECISION` and evidence.
Otherwise finish with `READY_FOR_REVIEW` and
`REPORT_PATH=<path>`.
