# Slice 003: finalization window anchoring

## Identity

- Slice: S3
  (`slice-003-finalization-window-anchoring.md`).
- Change: `harden-discharge-report-collaborative-draft`.
- Task: `tasks.md` section 3.
- Depends on: S1 (predicate lives in
  `apps/dischargereports/services/permissions.py`
  after S1; this slice changes its final branch).

## Objective

Finalizing any draft opens a 24h correction window
anchored at finalization for creator and finalizer,
with legacy finals keeping today's verdicts.

## Read first

- `AGENTS.md`
- `PROJECT_CONTEXT.md`
- `openspec/changes/harden-discharge-report-collaborative-draft/proposal.md`
- `openspec/changes/harden-discharge-report-collaborative-draft/design.md`
  (decision D6 is binding for this slice)
- `openspec/changes/harden-discharge-report-collaborative-draft/specs/discharge-report-actions/spec.md`
  (finalization requirement)
- `slices/slice-001-single-predicate-timeline-dispatch.md`
  (predicate location contract)
- `apps/dischargereports/models.py`
  (`DischargeReport` fields)
- `apps/dischargereports/migrations/`
  (numbering and convention for the new migration)
- `apps/dischargereports/services/permissions.py`
  (S1 service; final branch is edited here)
- `apps/dischargereports/views.py`
  (`DischargeReportUpdateView.form_valid`)
- `apps/dischargereports/admin.py`
  (`readonly_fields`, `Metadados` fieldset)
- `apps/dischargereports/templates/dischargereports/dischargereport_detail.html`
  (line ~190 "Criado por" block)
- `apps/events/models.py` (`can_be_edited`)

Follow the repository engineering policy in `AGENTS.md`
and preserve existing conventions. Prefer the smallest
correct change; avoid speculative abstraction and
unrelated refactoring.

## Requirements

- R1: A migration adds nullable `finalized_at`
  (datetime) and `finalized_by` (FK to the user
  model, `SET_NULL`, related name
  `finalized_discharge_reports`) and backfills
  legacy finals with `finalized_at = created_at`
  and `finalized_by = created_by`; drafts stay
  null. Evidence: migration file plus a backfill
  test on seeded rows.
- R2: The draft-to-final flip sets `finalized_at`
  to now and `finalized_by` to the acting user;
  the final is then editable within 24h of the
  anchor by creator OR finalizer, including an
  old draft finalized by a collaborator.
  Evidence: view tests for fresh and backdated
  drafts finalized by a second doctor, plus a
  timeline assertion that the card shows edit
  to the finalizer.
- R3: Re-saving a final as draft within its
  window clears both fields and restores draft
  rules; the next finalize re-anchors. Evidence:
  view test asserting null fields plus draft
  predicate afterwards.
- R4: More than 24h after `finalized_at`, the
  update view denies everyone (including
  `change_event` holders, still window-bound).
  Evidence: view/model tests with a backdated
  anchor.
- R5: A final with null `finalized_at` falls back
  to the `created_at` anchor. Evidence: model
  test with null anchor, old and fresh
  `created_at`.
- R6: Delete behavior for finals is unchanged
  (creation-anchored standard window). Evidence:
  existing delete tests stay green plus a new
  test: old draft freshly finalized is editable
  but not deletable by the creator.
- R7: Admin shows both fields read-only and the
  detail page shows "Finalizado por X em Y" for
  finals only. Evidence: admin config test plus
  detail response assertions.

## Expected blast radius

- Likely: `apps/dischargereports/models.py`
  (fields), one new migration,
  `apps/dischargereports/services/permissions.py`
  (final branch),
  `apps/dischargereports/views.py` (flip/clear
  bookkeeping), `apps/dischargereports/admin.py`,
  detail template, discharge tests.
- Sensitive, do not change without escalation:
  draft predicate semantics, delete rule
  semantics, creation gate, other models/apps,
  `Event.can_be_edited` itself.
- Previous behavior that must hold: draft
  collaboration from S1, non-doctor denial,
  fresh-finalize UX unchanged (fields are set
  silently), S1 assertions green via the
  null-anchor fallback.

## Failing-before plan

Failing-before evidence (run before implementing):

- targeted test: finalize a backdated draft as a
  collaborator, then GET update as finalizer →
  today 403 (immediately locked), after fix 200.
- targeted test: `finalized_at`/`finalized_by`
  after finalize → today attributes missing,
  after fix set.
- targeted test: old final (created more than
  24h ago) → 403 before via the creation anchor
  and 403 after via the null-anchor fallback
  (preservation proof).

Record commands, exit codes, and failure output in
the evidence report.

## Implementation constraints

- This slice is the change's only migration;
  keep it to the two fields plus the backfill
  (reversible data step).
- Backfill rule is fixed: finals get
  `created_at`/`created_by`; never `updated_at`,
  never guess another finalizer.
- Enforce the anchor with the same clock source
  as `can_be_edited` (`timezone.now`).
- Do not implement S1 (predicate location) or S2
  (identity) in this slice; if S1 is missing,
  stop per escalation instead of rebuilding it.
- S1's assertions stay green unchanged via the
  null-anchor fallback; extend coverage with
  finalizer/anchor cases instead of rewriting
  S1's final-branch tests.
- Do not touch files outside the slice blast
  radius without justification.

## Validation

Focused validation (worker runs during the slice):

- `./scripts/test.sh apps.dischargereports`
- `./scripts/test.sh apps.events.tests`
  (timeline equivalence still holds)

Project-required gates: see `AGENTS.md` (full suite
via `./scripts/test.sh` before handoff; markdown
lint for touched docs). Migration approval for
production deploy is separate from this slice.
Do not replicate global gates here beyond
referencing them.

Runtime/verification evidence: old-draft finalize
transcript by a collaborator (302, fields set,
update GET 200 within window) plus detail HTML
with the finalized line.

TDD is required: RED → GREEN → REFACTOR for R1..R7
(R1's migration may be written first with the
backfill test asserting seeded-row outcomes).

## Acceptance criteria

- [ ] Migration adds and backfills exactly per
      R1; drafts untouched.
- [ ] Old-draft finalize opens a 24h window for
      creator and finalizer.
- [ ] Revert to draft clears the anchor; next
      finalize re-anchors.
- [ ] Post-window update denied for everyone
      window-bound.
- [ ] Null-anchor fallback and delete lock-in
      proven by tests.
- [ ] Admin and detail display the finalization
      data.
- [ ] Focused suites pass; full suite green; no
      new ruff/mypy findings vs baseline.
- [ ] Evidence report written with failing-before
      and passing-after proof.

## Escalation conditions

Stop with `BLOCKED_NEEDS_DECISION` and evidence if
any of these appear: S1 service missing (do not
rebuild it here), contradiction in
proposal/design/spec, need for a second migration
or a non-nullable field, need to change delete
semantics or draft rules to satisfy the slice,
backfill touching an unexpectedly large row count
or failing on staging data, new
security/privacy/clinical implication, or
inability to satisfy R1..R7 without scope
expansion.

## Evidence report

Path: `/tmp/eqmd-slice-S3-report.md`.

Include: status (`READY_FOR_REVIEW` or
`BLOCKED_NEEDS_DECISION`), requirements →
evidence, changed files, failing-before evidence,
passing-after evidence, commands with exit status
(including migration apply), runtime evidence,
blast-radius expansion with justification, risks,
and open decisions for humans.

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
