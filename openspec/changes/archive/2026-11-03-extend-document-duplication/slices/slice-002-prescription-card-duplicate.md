# Slice 002 — prescription duplicate action on the timeline card

## Identity

- Slice: S2 of change `extend-document-duplication`.
- Task: `tasks.md` section 2.

## Objective

Users with `events.add_event` see a duplicate action on the patient
timeline prescription card that clones the prescription into a draft and
lands on the copy's edit view.

## Read first

- `AGENTS.md`
- `openspec/changes/extend-document-duplication/proposal.md`
- `openspec/changes/extend-document-duplication/design.md` — Decision D
- `openspec/changes/extend-document-duplication/specs/outpatientprescriptions/spec.md`
- Existing endpoint (do NOT modify):
  `apps/outpatientprescriptions/views.py` (`OutpatientPrescriptionDuplicateView`,
  POST-only) and `apps/outpatientprescriptions/urls.py`
  (`outpatientprescriptions:outpatientprescription_duplicate`)
- Card to modify:
  `apps/events/templates/events/partials/event_card_prescription.html`
- Button markup reference (detail page):
  `apps/outpatientprescriptions/templates/outpatientprescriptions/outpatientprescription_detail.html`
  (inline duplicate `<form method="post">`)
- Existing endpoint tests:
  `apps/outpatientprescriptions/tests/test_views.py` — classes
  `OutpatientPrescriptionDuplicateViewTest` (~line 1129: POST, GET 405,
  login) and `OutpatientPrescriptionDuplicateButtonVisibilityTest`
  (~line 1354: `action="..."` assertion pattern to reuse for the card
  tests).

## Requirements

- R1: The prescription card renders an inline POST form (with
  `{% csrf_token %}` and `class="d-inline"`, mirroring
  `outpatientprescription_detail.html:36-42`) targeting the duplicate
  endpoint, with a `btn btn-outline-info btn-sm` button labeled
  "Duplicar" (tooltip + `aria-label`) and icon `bi-files` (matching the
  other timeline duplicate buttons; the detail page keeps `bi-copy`),
  when the viewer holds `events.add_event`.
- R2: The form is absent for users without `events.add_event`; a direct
  POST to the endpoint by such users is still denied by the view
  (existing behavior — assert once for defense in depth).
- R3: Submitting the card form creates a new draft copy and redirects
  to the copy's edit view (existing endpoint behavior, unchanged —
  verified through the card's form action URL, not by re-testing clone
  semantics already covered in
  `apps/outpatientprescriptions/tests/test_views.py`).
- R4: No JavaScript, no confirmation dialog; card markup stays inside
  the existing `event_actions` block and Bootstrap 5 patterns. The form
  uses `d-inline` so it does not break the `.btn-group` layout.

## Expected blast radius

- Modified: `apps/events/templates/events/partials/event_card_prescription.html`
  only, plus a NEW focused card test module under
  `apps/outpatientprescriptions/tests/`. Slice-001 owns
  `apps/patients/tests/test_patient_timeline_links.py` — do not extend
  that module here, to avoid inter-slice merge conflicts.
- Must not change: the duplicate view, its URL, clone semantics,
  `apps/events/views.py`, other cards, the prescription detail page.

## Failing-before evidence

- RED test: authenticated user WITH `events.add_event` loads the
  patient timeline containing a prescription event; assertion that the
  response contains `outpatientprescription_duplicate` form action for
  that event fails before the change.

## Implementation constraints

- Template-only change plus tests; no view/URL/model edits.
- Follow the repository engineering policy in `AGENTS.md`; no
  speculative refactoring of the card.
- Do not implement other slices.

## Validation

- Focused: `./scripts/test.sh apps.patients.tests.test_patient_timeline_links`
  and `./scripts/test.sh apps.outpatientprescriptions`.
- Project gates: `AGENTS.md` (full `./scripts/test.sh`).
- Runtime evidence: timeline HTML excerpt showing the form/button for
  an authorized user and its absence for an unauthorized one.

## Acceptance criteria

- [ ] R1–R4 verified by passing tests + runtime evidence.
- [ ] Failing-before evidence captured.
- [ ] No file outside blast radius without justification.

## Escalation conditions

Stop with `BLOCKED_NEEDS_DECISION` if: the card context cannot resolve
the endpoint namespace; CSRF rendering inside the card breaks the
timeline layout; any behavior change in the endpoint appears to be
required.

## Evidence report

Write `/tmp/eqmd-slice-S2-report.md` (same structure as S1).

## Worker handoff

Implement only this approved slice. Treat the slice and referenced
OpenSpec artifacts as the implementation contract. Reconstruct context
from the listed files; do not rely on prior conversation. Follow the
repository engineering policy in `AGENTS.md` and preserve existing
conventions. Produce failing-before evidence, implement the smallest
correct change, run focused validation, and produce the required
evidence report. Do not update `tasks.md`, commit, push, merge,
archive, or start another slice. If a new decision is required, stop
with `BLOCKED_NEEDS_DECISION` and evidence. Otherwise finish with
`READY_FOR_REVIEW` and `REPORT_PATH=/tmp/eqmd-slice-S2-report.md`.
