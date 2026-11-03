# Design: duplicate-discharge-report

## Context

Post-hardening state (base `39e2043`): drafts are editable by the
creator, `events.change_event` holders, or any doctor/resident with
patient access; finals open a 24h window anchored at `finalized_at`
(legacy fallback: `created_at`). The single predicate lives in
`apps/dischargereports/services/permissions.py`. The create flow
(`DischargeReportCreateView` + `DischargeReportCreateForm`) decides
draft-vs-final via the `save_final` POST key and stamps
`finalized_at`/`finalized_by` when saving final.

## Decision D1 — Permission model: create, not edit

Duplication creates a new document, so access follows the create
flow already shipped for five document types: the view's `dispatch`
checks `can_access_patient(request.user, source.patient)` and raises
`PermissionDenied` otherwise; the card action is gated by
`perms.events.add_event`. No opt-in flag, no reuse of
`can_edit_discharge_report` — duplicating an expired final is
allowed because the source is never mutated.

## Decision D2 — The copy is always born a draft

Regardless of the source state, the pre-filled form saves through
the standard create semantics: without `save_final` the copy is a
draft; with `save_final` the user may finalize it immediately, which
stamps the copy's own `finalized_at`/`finalized_by`. The source's
finalization metadata is never copied, so a duplicated final never
leaks edit-window state into the copy.

## Decision D3 — Field copy matrix

Copied verbatim from the source: `medical_specialty`,
`admission_date`, `discharge_date`, `admission_history`,
`problems_and_diagnosis`, `exams_list`, `procedures_list`,
`inpatient_medical_history`, `discharge_status`,
`discharge_recommendations`.

Not copied: `event_datetime` (fresh `now`, matching the create-form
default for a new document), `is_draft` (always draft, D2),
`finalized_at`/`finalized_by`, `created_by`/`updated_by` (stamped to
the submitting user), `created_at`/`updated_at` (auto).

Rationale: a duplicate reuses the same hospitalization context
(admission/discharge dates travel with the content) while the
document timestamp marks the new document's creation.

## Decision D4 — Implementation mirrors the reports pattern (S1)

`DischargeReportCreateForm.__init__` sets field-level initials
(`event_datetime` = now; `admission_date`/`discharge_date` from
the patient's active admission). Django's
`Form.get_initial_for_field()` prefers form-level
`form.initial[field]` over `field.initial`, so the cleanest
override of the create-form defaults is the same mechanism the
create form itself uses: like `ReportDuplicateForm` in
`extend-document-duplication` S1, the duplicate view uses a form
subclass — `DischargeReportDuplicateForm(DischargeReportCreateForm)`
— that pops a `source` kwarg and, after `super().__init__`,
re-applies the source initials at field level so the source wins
over the automatic admission defaults (D3). The duplicate view
must NOT pass form-level `initial` values for these fields
(form-level initial would take precedence over both); the view is
a `CreateView` bound to `patient` taken from the source, rendering
`dischargereports/dischargereport_duplicate.html`; success
redirects to the patient timeline with a pt-BR success message,
matching the create view.

## Decision D5 — Card action parity

Timeline card button between PDF and Edit: icon `bi-files`, class
`btn-outline-info`, `aria-label`/tooltip "Duplicar relatório de
alta", gated by `{% if perms.events.add_event %}` — identical visual
and permission contract to the report (S1) and prescription (S2)
cards delivered by `extend-document-duplication`.

## Risks / Trade-offs

- Field-level initial clobbering (D4) is verified by an explicit GET
  prefill test with a source whose dates differ from the patient's
  active admission defaults.
- The form subclass inherits create-form validation (date input
  formats, patient admission lookup); the slice must not modify
  `DischargeReportCreateForm` itself.
