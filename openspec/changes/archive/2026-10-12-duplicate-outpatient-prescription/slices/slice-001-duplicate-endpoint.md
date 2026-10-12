# Slice 001 — Duplicate endpoint

- Slice ID: slice-001-duplicate-endpoint
- Change: `duplicate-outpatient-prescription`
- Tasks: 1.1, 1.2

## Objective

POST to the duplicate action clones a prescription into an
independent draft and redirects to the copy's edit view.

## Read first

- `AGENTS.md`
- `openspec/changes/duplicate-outpatient-prescription/proposal.md`
- `openspec/changes/duplicate-outpatient-prescription/design.md`
  (D1–D4, D6)
- `openspec/changes/duplicate-outpatient-prescription/specs/outpatientprescriptions/spec.md`
- `apps/outpatientprescriptions/models.py`
  (`OutpatientPrescription`, `PrescriptionItem`)
- `apps/outpatientprescriptions/views.py`
  (`OutpatientPrescriptionCreateView.form_valid` authorship pattern)
- `apps/outpatientprescriptions/urls.py`
- `apps/dailynotes/views.py` (`DailyNoteDuplicateView` permission
  pattern only — do not copy its form-rendering approach)

## Requirements

- R1: POST `<uuid:pk>/duplicate/` creates a new draft for the same
  patient with copied `instructions`, `prescription_date` = the
  configured-local date (`timezone.localdate()`, `America/Bahia` —
  include a near-midnight boundary case),
  `event_datetime` now, actor as creator, and one new item row per
  source item preserving order and content.
- R2: The copy is independent: new PKs, source rows unchanged,
  cloned items carry `source_template = None`.
- R3: Deny without creating when the user lacks patient access or
  `events.add_event`; reject GET (405).
- R4: Success responds 302 to the copy's `outpatientprescription_update`
  URL with a success message.
- R5: Duplication leaves every `DrugTemplate.usage_count` unchanged.

Follow the repository engineering policy in `AGENTS.md` and preserve
existing conventions. Prefer the smallest correct change; avoid
speculative abstraction and unrelated refactoring.

## Expected blast radius

- Likely: `apps/outpatientprescriptions/views.py` (new view),
  `apps/outpatientprescriptions/urls.py` (new route),
  `apps/outpatientprescriptions/tests/test_views.py` (new tests).
- Sensitive, do not change without escalation: models/schema (zero
  migrations), create/update/delete/print/PDF behavior, `Event` base,
  `PrescriptionItem.save()` usage-count logic.
- Prior behavior that must remain: all existing prescription tests
  green.

## Failing-before plan

Failing-before evidence:

- targeted test: POST to the duplicate URL of an existing
  prescription (reverser name to be defined by the worker).
- expected failure: 404 (no route) before the change; assertion of
  the clone contract after.

## Implementation constraints

- POST-only view; no duplicate form template (D1).
- Same patient only; status of the copy always `draft` even when the
  source is finalized.
- Do not implement the detail-page button (S2).

## Validation

Focused validation:

- `./scripts/test.sh apps.outpatientprescriptions` — all green.

Project-required gates: per `AGENTS.md` (smoke is covered by CI;
ruff on touched files; markdownlint untouched here).

Runtime/verification evidence: not required beyond tests; the 302
target is asserted in tests.

## Acceptance criteria

- [ ] R1 clone contract holds (header, date, items, authorship).
- [ ] R2 independence holds (source untouched, no source_template).
- [ ] R3 guards deny without side effects; GET rejected.
- [ ] R4 redirect lands on the copy's edit URL.
- [ ] R5 usage counts unchanged.
- [ ] Focused suite green; no new ruff findings on touched files.

## Escalation conditions

Stop with `BLOCKED_NEEDS_DECISION` if: spec/design contradiction;
new product or architecture decision needed; material scope
expansion; persistence/migration change required; new security,
privacy, or clinical-behavior implication; or the slice cannot be
met without violating the approved contract.

## Evidence report

Path: `/tmp/sirhosp-slice-dup-01-report.md` with status
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
`REPORT_PATH=/tmp/sirhosp-slice-dup-01-report.md`.
