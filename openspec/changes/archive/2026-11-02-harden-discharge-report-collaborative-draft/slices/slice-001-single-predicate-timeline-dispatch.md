# Slice 001: single predicate and timeline dispatch

## Identity

- Slice: S1
  (`slice-001-single-predicate-timeline-dispatch.md`).
- Change: `harden-discharge-report-collaborative-draft`.
- Task: `tasks.md` section 1.

## Objective

One collaborative predicate serves the model, the
view helper, and the timeline, so a collaborating
doctor sees the timeline edit action on another
author's draft.

## Read first

- `AGENTS.md`
- `PROJECT_CONTEXT.md`
- `openspec/changes/harden-discharge-report-collaborative-draft/proposal.md`
- `openspec/changes/harden-discharge-report-collaborative-draft/design.md`
  (decisions D1, D2 are binding for this slice)
- `openspec/changes/harden-discharge-report-collaborative-draft/specs/discharge-report-actions/spec.md`
  (edit availability requirement, unknown-action
  scenario)
- `apps/dischargereports/models.py`
  (`can_be_edited_by_user`, `can_be_deleted_by_user`)
- `apps/dischargereports/views.py`
  (`can_edit_discharge_report`,
  `can_delete_discharge_report`,
  `DischargeReportUpdateView`)
- `apps/dischargereports/templatetags/dischargereport_tags.py`
- `apps/events/views.py`
  (`_bulk_permission_check`)
- `apps/events/templates/events/partials/event_card_dischargereport.html`
- `apps/core/permissions/utils.py`
  (`can_edit_event`, `can_delete_event`)

Follow the repository engineering policy in `AGENTS.md`
and preserve existing conventions. Prefer the smallest
correct change; avoid speculative abstraction and
unrelated refactoring.

## Requirements

- R1: The edit/delete predicates live in
  `apps/dischargereports/services/permissions.py`;
  the model methods delegate to the service and
  `views.py` re-exports keep existing importers
  working. Evidence: equivalence test plus
  unchanged detail behavior.
- R2: The timeline bulk check dispatches
  discharge-report events to the service predicate
  for `can_edit` and `can_delete`; other event
  types keep the generic path. Evidence: timeline
  test as collaborator (edit visible) and as
  non-doctor (edit hidden).
- R3: A collaborator sees no timeline edit action
  on a finalized report whose window expired
  (created more than 24h ago; S3 re-anchors the
  window without changing this verdict for legacy
  finals). Evidence: timeline test with an old
  final.
- R4: Model method, view helper, and timeline
  check return the same edit verdict for a matrix
  of user/report pairs (creator, collaborator
  doctor/resident, non-doctor, fresh/old
  draft/final). Evidence: equivalence test.
- R5: An update POST with neither `save_draft` nor
  `save_final` leaves state unchanged and returns
  an explicit error naming the valid actions.
  Evidence: view test asserting state plus error.

## Expected blast radius

- Likely: new
  `apps/dischargereports/services/permissions.py`,
  `apps/dischargereports/models.py` (delegation),
  `apps/dischargereports/views.py` (re-exports,
  explicit actions), `apps/events/views.py`
  (dispatch), discharge/event tests.
- Sensitive, do not change without escalation:
  predicate semantics (creator OR `change_event`
  OR `profession_type in (0, 1)` for drafts),
  creation gate, finalized/delete rules beyond
  dispatch, migrations/schema, card template
  markup, other event types.
- Previous behavior that must hold: detail edit
  visibility, update GET/POST flows, timeline
  draft inclusion, full existing suites.

## Failing-before plan

Failing-before evidence (run before implementing):

- targeted test: collaborator timeline GET shows
  the discharge update URL → today absent, after
  fix present.
- targeted test: equivalence matrix across the
  three doors → today timeline diverges, after
  fix all equal.
- targeted test: update POST without action →
  document today's silent behavior, then the
  explicit error.

Record commands, exit codes, and failure output in
the evidence report.

## Implementation constraints

- Keep predicate semantics byte-identical; move
  code, do not reinterpret it.
- Keep `can_access_patient()` as a precondition
  in the service edit/delete functions.
- Do not change the card template markup; fix the
  flags feeding it.
- Do not implement S2 (identity) or S3
  (finalization anchoring) in this slice.
- No schema/migration changes.

## Validation

Focused validation (worker runs during the slice):

- `./scripts/test.sh apps.dischargereports`
- `./scripts/test.sh apps.events.tests`

Project-required gates: see `AGENTS.md` (full suite
via `./scripts/test.sh` before handoff; markdown
lint for touched docs). Do not replicate global
gates here beyond referencing them.

Runtime/verification evidence: collaborator
timeline HTML containing the update URL plus a
non-doctor timeline without it.

TDD is required: RED → GREEN → REFACTOR for R1..R5.

## Acceptance criteria

- [ ] Service owns the predicates; model and view
      delegate; existing importers unbroken.
- [ ] Collaborator timeline shows the draft edit
      action; non-doctor timeline hides it.
- [ ] Old-final timeline hides edit from the
      collaborator.
- [ ] Equivalence matrix passes for all three
      doors.
- [ ] Unknown update action preserves state with
      an explicit error.
- [ ] Focused suites pass; full suite green; no
      new ruff/mypy findings vs baseline.
- [ ] Evidence report written with failing-before
      and passing-after proof.

## Escalation conditions

Stop with `BLOCKED_NEEDS_DECISION` and evidence if
any of these appear: contradiction in
proposal/design/spec, need for a schema change,
need to change predicate semantics to satisfy the
slice, `select_subclasses()` not yielding a real
`DischargeReport` in the bulk check, new
security/privacy/clinical implication, or
inability to satisfy R1..R5 without scope
expansion.

## Evidence report

Path: `/tmp/eqmd-slice-S1-report.md`.

Include: status (`READY_FOR_REVIEW` or
`BLOCKED_NEEDS_DECISION`), requirements →
evidence, changed files, failing-before evidence,
passing-after evidence, commands with exit status,
runtime evidence, blast-radius expansion with
justification, risks, and open decisions for
humans.

## Worker handoff

Implement only this approved slice. Treat the slice
and referenced OpenSpec artifacts as the
implementation contract. Reconstruct context from
the listed files; do not rely on prior
conversation. Follow the repository engineering
policy. Produce failing-before evidence, implement
the smallest correct change, run focused
validation, and produce the required evidence
report. Do not update `tasks.md`, commit, push,
merge, archive, or start another slice. If a new
decision is required, stop with
`BLOCKED_NEEDS_DECISION` and evidence. Otherwise
finish with `READY_FOR_REVIEW` and
`REPORT_PATH=<path>`.
