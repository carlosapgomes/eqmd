# Proposal: duplicate-discharge-report

## Why

Discharge reports (Relatório de Alta) are the only remaining text
document type on the patient timeline without a duplication action.
All five other text/PDF document types (daily notes, simple notes,
history & physical, prescriptions, reports) allow creating a new
editable document pre-filled from an existing one; the discharge
report card only offers view, PDF, edit and delete.

After `harden-discharge-report-collaborative-draft` shipped the
single collaborative predicate and the finalization window anchored
at `finalized_at`, the duplication semantics can now be defined
against a stable workflow: duplicating a report must never mutate the
source or its finalization metadata, and the copy starts as an
editable draft regardless of the source state.

## What Changes

- Add a `DischargeReportDuplicateView` (pattern:
  `apps/reports/views.py::ReportDuplicateView`) with route
  `dischargereports/<uuid:pk>/duplicate/` (name
  `dischargereport_duplicate`) on the existing
  `apps.dischargereports` urlconf.
- Add `DischargeReportDuplicateForm` (subclass of
  `DischargeReportCreateForm`) that pre-fills the clinical content
  fields and admission/discharge dates from the source report.
- Add a `dischargereport_duplicate.html` template reusing the create
  form layout.
- Add a duplicate button (`bi-files`, `btn-outline-info`, gated by
  `perms.events.add_event`) to the timeline card
  (`event_card_dischargereport.html`), placed between the PDF and
  Edit actions.
- Regression tests for the view (GET prefill, POST copy semantics,
  permissions, source integrity) and the card action gating.

## Non-goals

- Shortening the `apps.dischargereports` URL namespace (explicitly
  excluded by `extend-document-duplication` Decision E).
- Changing the collaborative draft workflow, the edit/delete
  predicates in `apps/dischargereports/services/permissions.py`, the
  finalization window, or the create/update flows.
- Copying finalization metadata (`finalized_at`/`finalized_by`) or
  duplicating directly into a final state.
- A duplicate entry on the report detail page (timeline-first, same
  as every other duplication flow).
- Copy-to-clipboard features; PDFForm `allow_duplication` semantics.
