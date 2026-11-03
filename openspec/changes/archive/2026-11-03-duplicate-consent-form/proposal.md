# Proposal: duplicate-consent-form

## Why

Consent forms (Termo de Consentimento) are signed paper documents:
once created, their rendered markdown is frozen (`rendered_markdown`
is immutable after creation; the update view only manages scanned
attachments). When a term needs a small correction — without
changing the template for everyone — there is no flow today: the
user must rebuild the document from scratch, and the corrected term
must be reprinted with the current date for the new signature cycle.

## What Changes

- Add a `ConsentFormDuplicateView` (pattern:
  `apps/reports/views.py::ReportDuplicateView`, adapted) with route
  `consentforms/<uuid:pk>/duplicate/` (name `consentform_duplicate`)
  on the existing `consentforms` urlconf.
- Add `ConsentFormDuplicateForm`: document date defaulting to today,
  procedure description copied from the source, the source's
  template as a fixed provenance reference (allowed even if now
  inactive), and an **editable markdown field pre-filled with the
  source's rendered markdown** so the correction happens in the
  duplicate form itself.
- Add a `consentform_duplicate_form.html` template reusing the
  create layout (template info shown read-only, markdown editor,
  preview parity with the create flow).
- Add a duplicate button (`bi-files`, `btn-outline-info`, gated by
  `perms.events.add_event`) to the timeline card
  (`event_card_consentform.html`), between the PDF and
  attachment-edit actions.
- Regression tests for the view (GET prefill, POST copy semantics
  including edited markdown, permissions, source integrity, no
  attachment copying) and the card action gating.

## Non-goals

- Making the rendered markdown of an EXISTING document editable
  (the per-document immutability invariant stays; the duplicate is a
  new document whose snapshot is set at its own creation).
- Copying attachments (signatures/scans) or any cross-reference
  between duplicate and source — the original stays untouched and
  fully valid as printed/paper-tracked in the physical record.
- Editing `ConsentTemplate` content or its administration flow.
- Shortening any URL namespace (`consentforms` is already short).
