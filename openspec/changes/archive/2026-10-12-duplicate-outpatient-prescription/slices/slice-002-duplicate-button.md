# Slice 002 — Duplicate button

- Slice ID: slice-002-duplicate-button
- Change: `duplicate-outpatient-prescription`
- Tasks: 2.1, 2.2

## Objective

The prescription detail page exposes the duplicate action to
authorized users through a visible control.

## Read first

- `AGENTS.md`
- `openspec/changes/duplicate-outpatient-prescription/proposal.md`
- `openspec/changes/duplicate-outpatient-prescription/design.md` (D5)
- `openspec/changes/duplicate-outpatient-prescription/specs/outpatientprescriptions/spec.md`
- `apps/outpatientprescriptions/templates/outpatientprescriptions/outpatientprescription_detail.html`
  (existing delete POST form as the technique reference)

## Requirements

- R1: Detail page shows a "Duplicar" control submitting POST to the
  S1 duplicate URL with CSRF when the user holds
  `events.add_event`.
- R2: The control is absent without `events.add_event`.
- R3: No GET link to the duplicate URL is rendered (POST-only
  action).

Follow the repository engineering policy in `AGENTS.md` and preserve
existing conventions. Prefer the smallest correct change; avoid
speculative abstraction and unrelated refactoring.

## Expected blast radius

- Likely: the detail template above,
  `apps/outpatientprescriptions/tests/test_views.py` (visibility
  tests).
- Sensitive, do not change without escalation: S1 view/route
  contract, detail-view access predicate, any other template.
- Prior behavior that must remain: edit/delete/PDF controls
  unchanged.

## Failing-before plan

Failing-before evidence:

- verification scenario: GET the detail page as an authorized user
  and assert a duplicate control exists.
- expected observable failure: control absent before the change.

## Implementation constraints

- Reuse the existing delete-form technique (inline POST + CSRF);
  do not add JavaScript.
- Do not re-implement or alter S1 behavior.

## Validation

Focused validation:

- `./scripts/test.sh apps.outpatientprescriptions` — all green.

Project-required gates: per `AGENTS.md`; ruff on touched files if
Python changed (template-only change expected).

Runtime/verification evidence: rendered detail page asserted in
tests (control present/absent); no manual browser proof required.

## Acceptance criteria

- [ ] R1 control present and POSTs with CSRF for authorized users.
- [ ] R2 control absent without `add_event`.
- [ ] R3 no GET duplicate link rendered.
- [ ] Focused suite green.

## Escalation conditions

Stop with `BLOCKED_NEEDS_DECISION` if: spec/design contradiction;
new product or architecture decision needed; material scope
expansion; or the slice cannot be met without violating the
approved contract.

## Evidence report

Path: `/tmp/<APP_VIZINHA>-slice-dup-02-report.md` with status
(`READY_FOR_REVIEW` or `BLOCKED_NEEDS_DECISION`), requirements →
evidence, files changed, failing-before and passing-after evidence,
commands with exit status, unexpected blast-radius expansion with
justification, risks/limitations, and decisions needing a human.

## Worker handoff

Implement only this approved slice.
Treat the slice and referenced OpenSpec artifacts as the
implementation contract.
Reconstruct context from the listed files; do not rely on prior
conversation.
Follow the repository engineering policy.
Produce failing-before evidence, implement the smallest correct
change, run focused validation, and produce the required evidence
report.
Do not update `tasks.md`, commit, push, merge, archive, or start
another slice.
If a new decision is required, stop with `BLOCKED_NEEDS_DECISION`
and evidence.
Otherwise finish with `READY_FOR_REVIEW` and
`REPORT_PATH=/tmp/<APP_VIZINHA>-slice-dup-02-report.md`.
