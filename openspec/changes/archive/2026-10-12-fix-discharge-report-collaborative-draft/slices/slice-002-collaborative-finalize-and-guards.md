# Slice 002: collaborative finalize and guards

## Identity

- Slice: S2 (`slice-002-collaborative-finalize-and-guards.md`).
- Change: `fix-discharge-report-collaborative-draft`.
- Task: `tasks.md` section 2.
- Depends on: S1 (shared draft predicate fixed).

## Objective

Another doctor can finalize a draft, while non-doctors
stay blocked and finalized/delete rules stay unchanged.

## Read first

- `AGENTS.md`
- `PROJECT_CONTEXT.md`
- `openspec/changes/fix-discharge-report-collaborative-draft/proposal.md`
- `openspec/changes/fix-discharge-report-collaborative-draft/design.md`
  (decisions D3, D4, D5 are binding for this slice)
- `openspec/changes/fix-discharge-report-collaborative-draft/specs/dischargereports/spec.md`
  (finalize and guard requirements)
- `slices/slice-001-collaborative-draft-edit.md` (predicate
  contract; do not re-implement it)
- `apps/dischargereports/views.py`
  (`DischargeReportUpdateView.form_valid`)
- `apps/dischargereports/models.py`
  (`can_be_edited_by_user`, `can_be_deleted_by_user`)
- `apps/dischargereports/tests/test_models.py`
  (final-window and delete tests)
- `apps/dischargereports/tests/test_views.py`
  (update finalize and delete-window tests)
- `apps/dischargereports/tests/test_integration.py`
  (`test_unauthorized_user_cannot_edit` and draft flow)

Follow the repository engineering policy in `AGENTS.md`
and preserve existing conventions. Prefer the smallest
correct change; avoid speculative abstraction and
unrelated refactoring.

## Requirements

- R1: Doctor B can submit `save_final` on doctor A's draft;
  the report becomes `is_draft=False`. Evidence: view
  test with finalize `POST` by a second doctor.
- R2: A non-doctor (for example nurse `profession_type=2`
  or plain user) gets 403/false on draft update `GET` and
  `POST`, and no edit action is shown. Evidence: view +
  predicate test.
- R3: After finalization the 24h creator-only rule holds:
  creator edits within 24h, creator blocked after 25h,
  second doctor blocked on the final even within 24h
  unless holding `change_event`. Evidence: model/view
  regression tests.
- R4: Delete behavior unchanged: draft deletable by
  creator or `delete_event` holders; final deletable only
  in-window or with `delete_event`. Evidence: existing
  delete tests stay green.
- R5: The integration blocking assertion
  (`test_unauthorized_user_cannot_edit`) is reworked with
  explicit `profession_type` fixtures (collaborator doctor
  allowed, non-doctor denied). Evidence: updated
  integration test passes and documents the rule.

## Expected blast radius

- Likely: discharge report view/model tests only (no
  production-code change expected unless S1 left a gap;
  any production change needs explicit justification).
- Sensitive, do not change without escalation: edit
  predicate semantics from S1, creation gate, schema,
  other apps, bot drafts, copy/duplicate behavior.
- Previous behavior that must hold: S1 collaborative
  draft edit keeps working; finals stay immutable
  after 24h.

## Failing-before plan

Failing-before evidence (run before implementing):

- targeted test: second doctor finalize `POST`
  (`save_final`) on another doctor's draft → before S1
  403 with no state change; after S1+S2 302 and
  `is_draft=False`.
- targeted test: non-doctor draft update `GET` → 403
  both before and after (guard proof).
- targeted test: second doctor edit of a fresh final →
  403 (final rule proof).

If S1 is already applied, state which expectations were
fixed by S1 and which still fail without this slice.

## Implementation constraints

- Do not weaken the finalized-report rule or the delete
  rule to make R1 pass; finalize rides on the S1 draft
  predicate only.
- Keep `profession_type` fixtures explicit in every new
  or reworked test (`0` doctor, `1` resident, `2` nurse
  or equivalent); do not rely on default null profession.
- No schema/migration changes; no new permissions; no
  creation-gate change; no copy/duplicate feature.
- Do not re-implement S1; fix only genuine gaps found
  while proving R1..R5.

## Validation

Focused validation (worker runs during the slice):

- `./scripts/test.sh apps.dischargereports.tests.test_models`
- `./scripts/test.sh apps.dischargereports.tests.test_views`
- `./scripts/test.sh apps.dischargereports.tests.test_integration`
- `./scripts/test.sh apps.dischargereports` (slice scope)

Project-required gates: see `AGENTS.md` (full suite via
`./scripts/test.sh` before handoff; markdown lint for
touched docs). Do not replicate global gates here beyond
referencing them.

Runtime/verification evidence: second-doctor finalize
flow (`POST save_final` → 302, `is_draft=False`) plus a
negative non-doctor attempt (403) and a final-window
spot check.

TDD is required: RED → GREEN → REFACTOR for R1..R3.

## Acceptance criteria

- [ ] Second doctor finalize succeeds and flips the
      report to finalized.
- [ ] Non-doctor draft edit denied and edit action
      hidden.
- [ ] Finalized report still creator-only within 24h and
      locked after 25h; deletes unchanged.
- [ ] Integration blocking assertion
      (`test_unauthorized_user_cannot_edit`) reworked with
      explicit profession fixtures and passing.
- [ ] Focused suites pass; full suite green; no new
      ruff/mypy findings vs baseline.
- [ ] Evidence report written with failing-before and
      passing-after proof.

## Escalation conditions

Stop with `BLOCKED_NEEDS_DECISION` and evidence if any
of these appear: S1 predicate missing or contradictory,
need for schema/permission/creation-gate change, need
to alter final/delete semantics, new security or
clinical implication, or inability to satisfy R1..R5
without scope expansion.

## Evidence report

Path: `/tmp/sirhosp-slice-S2-report.md`.

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
