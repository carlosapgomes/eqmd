# Slice 003 — duplication POST regression coverage (text apps)

## Identity

- Slice: S3 of change `extend-document-duplication`.
- Task: `tasks.md` section 3.

## Objective

The POST half of the three text-document duplication flows is locked in
by regression tests proving that submitting the duplicate form creates
an independent copy.

## Read first

- `AGENTS.md`
- `openspec/changes/extend-document-duplication/proposal.md`
- The three duplicate views (behavior under test, do NOT modify):
  `apps/dailynotes/views.py` (`DailyNoteDuplicateView`),
  `apps/simplenotes/views.py` (`SimpleNoteDuplicateView`),
  `apps/historyandphysicals/views.py` (`HistoryAndPhysicalDuplicateView`)
- Existing coverage: daily notes — GET/permission tests only
  (`apps/dailynotes/tests/test_integration.py:196`,
  `test_permissions.py:231,352`); history and physical — ONE basic POST
  test (`test_integration.py:152-183`: asserts 302 + row count, NO
  independence guarantees); simple notes — none (`apps/simplenotes/tests/`).
- Forms defining valid POST payloads (field names, formats, validation):
  `apps/dailynotes/forms.py`, `apps/simplenotes/forms.py`,
  `apps/historyandphysicals/forms.py` (a working POST payload example:
  `apps/historyandphysicals/tests/test_integration.py:164-169`).
- Existing POST-style duplication tests as a style reference:
  `apps/pdf_forms/tests/test_duplication.py` and
  `apps/outpatientprescriptions/tests/test_views.py`

## Requirements

For EACH of the three apps (daily note, simple note, history and
physical). For history and physical, add the missing independence
assertions (new module or extend the existing test) — do NOT duplicate
the basic POST test that already exists:

- R1: A test that POSTs valid data (source content pre-filled or
  equivalent) to the duplicate URL and asserts: a NEW document exists
  for the same patient, `created_by` = the posting user,
  `event_datetime` is fresh (not the source's), and the response
  redirects to the patient timeline.
- R2: A test asserting the source document is unchanged after the POST
  (content, author, event_datetime).
- R3: Permission regression: an authenticated user without
  `events.add_event` cannot POST and receives 403 (the duplicate views
  check `can_access_patient` in `dispatch` before the login mixin, so
  anonymous requests also get 403 — see
  `apps/dailynotes/tests/test_permissions.py:352`).

SimpleNotes additionally gets GET coverage (pre-filled form) since the
app has none (superset of R1–R3 is acceptable in one module).

## Expected blast radius

- New module `apps/<app>/tests/test_duplication.py` for each of the
  three apps (fresh modules keep this coverage slice reviewable;
  extending an existing module is acceptable with justification in the
  report).
- NO production code changes are expected in this slice. If a test
  reveals a production defect, stop and escalate (see below).

## Failing-before evidence

This is a coverage slice over existing behavior: the new tests are
expected to PASS immediately. Evidence is the coverage gap itself —
record PER APP what is missing today (grep/read output; for history and
physical, note the existing basic POST test and which independence
assertions it lacks). If any new test FAILS, that is a bug finding:
capture the failure output and escalate; do not fix production code
silently.

## Implementation constraints

- Tests only; no production edits without escalation.
- Reuse existing test fixtures/factories. In new tests, reference URL
  namespaces in the SHORT form (`dailynotes:`, `simplenotes:`,
  `historyandphysicals:`) — resolves today via the instance namespace
  and is immune to slice-004's `app_name` rewrite (which runs later).
- Do not weaken existing tests.

## Validation

- Focused: `./scripts/test.sh apps.dailynotes`,
  `./scripts/test.sh apps.simplenotes`,
  `./scripts/test.sh apps.historyandphysicals`.
- Project gates: `AGENTS.md` (full `./scripts/test.sh`).

## Acceptance criteria

- [ ] R1–R3 present and green for the three apps.
- [ ] Coverage-gap evidence recorded.
- [ ] No production file touched (or escalation documented).

## Escalation conditions

Stop with `BLOCKED_NEEDS_DECISION` if any new test fails against
current production code (indicates a real defect in a duplication
flow), or if the existing behavior contradicts the specs/design of this
change.

## Evidence report

Write `/tmp/eqmd-slice-S3-report.md` (same structure as S1; the
"failing-before" section records the coverage gap instead).

## Worker handoff

Implement only this approved slice. Treat the slice and referenced
OpenSpec artifacts as the implementation contract. Reconstruct context
from the listed files; do not rely on prior conversation. Follow the
repository engineering policy in `AGENTS.md` and preserve existing
conventions. Record the coverage gap, add the tests, run focused
validation, and produce the required evidence report. Do not update
`tasks.md`, commit, push, merge, archive, or start another slice. If a
new decision is required, stop with `BLOCKED_NEEDS_DECISION` and
evidence. Otherwise finish with `READY_FOR_REVIEW` and
`REPORT_PATH=/tmp/eqmd-slice-S3-report.md`.
