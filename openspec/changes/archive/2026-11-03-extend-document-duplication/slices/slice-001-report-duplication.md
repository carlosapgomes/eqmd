# Slice 001 — report duplication

## Identity

- Slice: S1 of change `extend-document-duplication`.
- Task: `tasks.md` section 1.

## Objective

Authorized users can duplicate an existing report into a new report via
a pre-filled creation form, reachable from the patient timeline card.

## Read first

- `AGENTS.md`
- `openspec/changes/extend-document-duplication/proposal.md`
- `openspec/changes/extend-document-duplication/design.md` — Decisions
  A, B, C
- `openspec/changes/extend-document-duplication/specs/reports/spec.md`
- Reference implementation of the pattern:
  `apps/dailynotes/views.py` (`DailyNoteDuplicateView`), its
  `dailynote_duplicate_form.html`, and
  `apps/events/templates/events/partials/event_card_dailynote.html`
- Target app: `apps/reports/` (`models.py`, `forms.py`,
  `views/report_views.py`, `urls.py`, `templates/reports/`,
  `tests/`)
- Card: `apps/events/templates/events/partials/event_card_report.html`
- Existing card-link tests:
  `apps/patients/tests/test_patient_timeline_links.py`

## Requirements

- R1: `GET reports/<uuid:pk>/duplicate/` (URL name `report_duplicate`)
  renders `reports/report_duplicate_form.html` with the source's title
  and content pre-filled and today's document date; requires
  `events.add_event` and `can_access_patient` (403 otherwise; 404 for
  unknown pk).
- R2: The form excludes template selection (subclass of
  `ReportCreateForm` with `template` removed); no template re-render can
  occur. The view's `get_form_kwargs` passes BOTH `user` and
  `patient=source.patient` — `ReportCreateForm.__init__` pops both
  kwargs (the daily-note pattern passes only `user`; copying it blindly
  breaks this form). The subclass must guard the parent's template
  queryset block (`if 'template' in self.fields:`) —
  `apps/reports/forms.py:140-141` indexes `self.fields['template']`
  unconditionally when `user` is set and would raise `KeyError` with
  the field removed.
- R3: Valid POST creates a new `Report` for the source patient,
  `created_by`/`updated_by` = submitting user, fresh `event_datetime`
  (new 24h window), `template` not set; redirects to the patient
  timeline with a success message.
- R4: The source report is not modified by GET or POST.
- R5: `event_card_report.html` shows a duplicate action (GET link
  mirroring the daily-note card duplicate action: icon `bi-files`,
  `btn-outline-info`, tooltip, `aria-label`) gated by
  `{% if perms.events.add_event %}`. Mirror the daily-note texts:
  `aria-label="Duplicar relatório"`, tooltip "Criar novo relatório
  baseado neste".
- R6: Tests cover R1–R5 (view GET/POST, permissions, card
  presence/absence).

## Expected blast radius

- New: `apps/reports/views/report_views.py` (`ReportDuplicateView`),
  route in `apps/reports/urls.py`,
  `apps/reports/templates/reports/report_duplicate_form.html`, test
  module(s) under `apps/reports/tests/`.
- Modified: `apps/events/templates/events/partials/event_card_report.html`
  (duplicate button only), `apps/patients/tests/test_patient_timeline_links.py`
  (card-link assertions) or a focused card test module.
- Must not change: `ReportCreateView`/`ReportUpdateView` behavior,
  `Report.save()`, PDF generation, `apps/events/views.py`, the
  `discharge-report-actions` capability.

## Failing-before evidence

- RED test: `reverse("reports:report_duplicate")` raises
  `NoReverseMatch` (route absent) and GET on the intended path returns
  404; timeline card test asserting the duplicate link fails (link
  absent). Capture output before implementing.

## Implementation constraints

- Follow the text-app duplicate pattern exactly (permission_required,
  dispatch guard, get_form_kwargs initial, form_valid patient binding),
  EXCEPT the form kwargs difference in R2 (`user` + `patient`).
- No opt-in flags, no model/schema changes, no
  `apps/events/views.py` changes.
- Do not inherit or copy `ReportCreateView.get_initial` (its
  `?template=` GET-param re-render): the duplicate view ignores
  `?template=`; initial comes only from the source report's stored
  fields.
- Do not implement other slices.

## Validation

- Focused: `./scripts/test.sh apps.reports` and
  `./scripts/test.sh apps.patients.tests.test_patient_timeline_links`.
- Project gates: `AGENTS.md` (full `./scripts/test.sh`).
- Runtime evidence: manual GET of the duplicate URL renders the
  pre-filled form (screenshot or response HTML excerpt in the report).

## Acceptance criteria

- [ ] R1–R6 verified by passing tests + runtime evidence.
- [ ] Failing-before evidence captured.
- [ ] No file outside blast radius without justification.

## Escalation conditions

Stop with `BLOCKED_NEEDS_DECISION` if: the report form cannot exclude
`template` without breaking `ReportCreateForm`; card context lacks
`perms` for gating; any conflict with the specs listed in Read first;
anything requiring schema or permission-model changes.

## Evidence report

Write `/tmp/eqmd-slice-S1-report.md` with status, requirements →
evidence, changed files, failing-before output, passing-after output,
commands + exit codes, runtime evidence, blast-radius deviations.

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
`READY_FOR_REVIEW` and `REPORT_PATH=/tmp/eqmd-slice-S1-report.md`.
