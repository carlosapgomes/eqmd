# Slice 001 — Discharge report duplication flow

## Identity

- Slice: `slice-001-discharge-report-duplication`
- Change: `duplicate-discharge-report`
- Tasks: `tasks.md` items 1.1–1.4 (Contract: this file)

## Objective

Deliver the full discharge-report duplication flow end to end:
route, view, form, template, timeline-card action and regression
tests, mirroring the shipped reports pattern against the
post-hardening collaborative draft semantics.

## Read first

- `AGENTS.md`
- `openspec/changes/duplicate-discharge-report/proposal.md`
- `openspec/changes/duplicate-discharge-report/design.md` (D1–D5)
- `openspec/changes/duplicate-discharge-report/specs/discharge-report-actions/spec.md`
  (scenarios are the behavioral contract)
- `apps/dischargereports/services/permissions.py`
- `apps/dischargereports/views.py` (create view)
- `apps/dischargereports/forms.py` (create form)
- Mirrors: `apps/reports/views/report_views.py` (`ReportDuplicateView`),
  `apps/reports/forms.py` (`ReportDuplicateForm`), `apps/reports/urls.py`,
  `apps/reports/templates/reports/report_duplicate_form.html`,
  `apps/events/templates/events/partials/event_card_report.html`
- Test patterns: `apps/reports/tests/test_report_duplicate_view.py`,
  `apps/dischargereports/tests/test_views.py`,
  `apps/dischargereports/tests/test_permissions.py`

## Requirements

- **R1 — Route**: add to `apps/dischargereports/urls.py`
  `path('<uuid:pk>/duplicate/', views.DischargeReportDuplicateView.as_view(), name='dischargereport_duplicate')`.
  Namespace `app_name = 'apps.dischargereports'` stays untouched.
  Evidence: reverse resolves; focused tests green.
- **R2 — Form**: `DischargeReportDuplicateForm` in
  `apps/dischargereports/forms.py`, subclass of
  `DischargeReportCreateForm`, popping a `source` kwarg; after
  `super().__init__()` it re-applies at FIELD level
  (`self.fields[...].initial`) the source's: `medical_specialty`,
  `admission_date`, `discharge_date`, `admission_history`,
  `problems_and_diagnosis`, `exams_list`, `procedures_list`,
  `inpatient_medical_history`, `discharge_status`,
  `discharge_recommendations`. It must NOT touch
  `event_datetime` (create-form now-default stays) and must not
  copy `is_draft` or finalization metadata. Rationale (D3/D4):
  re-applying field initials after `super()` overrides the
  create-form field defaults (active-admission dates); the view
  must not pass form-level `initial` for these fields (form-level
  takes precedence over both). Evidence: GET prefill tests.
- **R3 — View**: `DischargeReportDuplicateView(LoginRequiredMixin,
  CreateView)` in `apps/dischargereports/views.py`: `dispatch`
  resolves the source via `get_object_or_404` and raises
  `PermissionDenied` unless `can_access_patient(request.user,
  source.patient)`; `get_form_kwargs` passes `patient` and
  `source`; context exposes `patient` and `source`; `form_valid`
  stamps `created_by`/`updated_by` to the request user and
  delegates draft/final to the create-form semantics (`save_final`
  POST key stamps `finalized_at`/`finalized_by` on the COPY only);
  success redirects to the patient timeline with a pt-BR message.
  Evidence: POST tests (draft and final paths).
- **R4 — Template**:
  `apps/dischargereports/templates/dischargereports/dischargereport_duplicate.html`
  reusing the create form layout, title "Duplicar Relatório de
  Alta", patient context, same draft/final submit buttons as
  create. Evidence: GET renders (assert template used + key
  content).
- **R5 — Card**: in `event_card_dischargereport.html`, between the
  PDF and Edit buttons: link to the `dischargereport_duplicate`
  route for `event.pk`, `bi-files` icon, `btn-outline-info btn-sm`,
  tooltip/aria "Duplicar relatório de alta", gated by
  `{% if perms.events.add_event %}`. No other card changes.
  Evidence: card render tests for both permission states.
- **R6 — Tests**: new
  `apps/dischargereports/tests/test_duplicate_view.py` covering at
  least: GET prefills content + source dates (source dates differ
  from any admission default); GET `event_datetime` default is now;
  POST saves an independent draft (`is_draft=True`, `created_by` =
  submitter, `finalized_at` null); POST with `save_final`
  finalizes the COPY (stamps copy only); duplicating an expired
  final is allowed, the source stays final, AND the copy is
  asserted to be a draft with both `finalized_at` and
  `finalized_by` null; source integrity
  after duplication; 403 without patient access; 404 unknown pk;
  card gating (show/hide).
- **R7 — No regressions**: create/update/delete views,
  `permissions.py`, `DischargeReportCreateForm` and the model are
  byte-identical except for the additions above. Evidence:
  `git diff --stat` limited to the expected surfaces.
- **R8 — Post-conditions**: `rg -n "dischargereport_duplicate" apps`
  shows route + view + template + card + tests.

## Expected blast radius

Expected surfaces: `apps/dischargereports/{forms.py,views.py,urls.py}`,
the new template, `event_card_dischargereport.html`, the new test
module. Sensitive surfaces that must not change (escalate first):
`apps/dischargereports/services/permissions.py`, the model,
`patient_timeline.html`, `config/urls.py`, any other app. Extra
files need justification in the report.

## Failing-before plan

Reproduce BEFORE implementing (record outputs):
- from a Django shell, reverse the
  `apps.dischargereports:dischargereport_duplicate` route with a
  uuid kwarg → expected `NoReverseMatch`;
- `manage.py test apps.dischargereports.tests.test_duplicate_view` →
  expected `ImportError`/module not found (tests are the RED step;
  write them first against the contract, then implement to GREEN).

## Implementation constraints

- Copy is ALWAYS born draft unless `save_final` is posted (D2);
  never copy `finalized_at`/`finalized_by`.
- Do NOT modify `DischargeReportCreateForm`,
  `DischargeReportCreateView/UpdateView/DeleteView`,
  `permissions.py`, the model, `patient_timeline.html`, or the
  namespace.
- No commits/pushes; no dependency installs; no new deps; do not
  update `tasks.md`.

## Validation

- Focused (worker): `apps.dischargereports apps.events` via the
  established container runner (controller-provided; test DB
  `test_eqmd_dev_dupdisch1`).
- Project gates: full suite error set must equal the recorded
  74-error fully-qualified pre-existing baseline
  (`/tmp/eqmd-slice-loop/eqmd/extend-document-duplication/exec-4-prep/post-merge-err-ids.txt`);
  extract with `grep -E "^ERROR:" <log>` piped to
  `sed -E 's/^ERROR: (\w+) \(([^)]+)\).*/\2.\1/' | sort`.
- `ruff check` on changed `.py` files — zero NEW findings vs
  `SLICE_BASE_REF`.

## Acceptance criteria

- [ ] AC1: duplicate route resolves (R1) — reverse works, focused
      tests green.
- [ ] AC2: GET form prefilled per R2 (test-asserted field values).
- [ ] AC3: POST draft copy semantics per R3/D2 (test-asserted).
- [ ] AC4: POST `save_final` stamps the copy only (test-asserted).
- [ ] AC5: expired-final source duplicable; copy asserted draft
      with `finalized_at`/`finalized_by` null; source integrity
      test-asserted (R6).
- [ ] AC6: 403/404 handling test-asserted (R6).
- [ ] AC7: card action present/absent per permission (R6).
- [ ] AC8: full suite = baseline identity; ruff zero new findings.
- [ ] AC9: diff limited to expected blast radius (extras justified).

## Escalation conditions

Stop and return `BLOCKED_NEEDS_DECISION` with evidence if: the
create-form initial precedence cannot deliver R2 by subclassing;
immutability or permission semantics block any R; a new product/
clinical decision emerges; blast radius must expand materially.

## Evidence report

Report to the controller-bound output path (slice-loop evidence
root): status, R1–R8 → evidence, failing-before + passing-after,
commands + exit codes, error-identity proof, `git diff --stat`,
deviations, risks. End with `READY_FOR_REVIEW` and
`REPORT_PATH=<path>`.
