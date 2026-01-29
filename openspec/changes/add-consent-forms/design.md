## Context
Consent forms must be generated, printed, and archived as part of the patient timeline. Templates are authored by admins in Django admin. Clinicians use templates to create consent form events that store immutable markdown snapshots. PDF generation must reuse the existing pdfgenerator services.

## Goals / Non-Goals
- Goals:
  - Provide admin-only template management with activation/retirement and audit history
  - Create consent form events from templates with immutable markdown snapshots
  - Reuse pdfgenerator for deterministic, on-demand PDFs
  - Allow optional scanned uploads within the existing 24-hour edit window
- Non-Goals:
  - No new authorization model beyond the existing event edit window
  - No general-purpose template engine or scripting
  - No requirement to keep template versions available for new events

## Decisions
- Decision: Implement consent forms in a dedicated `consentforms` app with `ConsentTemplate`, `ConsentForm` (Event subclass), and `ConsentAttachment`.
- Decision: Use django-simple-history on `ConsentTemplate` to display who changed it and when in Django admin.
- Decision: Validate templates on save to ensure only allowlisted placeholders are used and required placeholders are present.
- Decision: Render templates with a small allowlist-based renderer that produces a stored markdown snapshot. The snapshot is immutable after creation and is the canonical content.
- Decision: Integrate PDF generation by using `HospitalLetterheadGenerator` and `MarkdownToPDFParser` (patterned after `apps/pdfgenerator` and `apps/outpatientprescriptions`).
- Decision: Edit flow after creation only allows attachment changes; it does not re-render or mutate the markdown snapshot.

## Risks / Trade-offs
- Template validation errors must be clearly surfaced in Django admin to avoid unusable templates.
- If future needs require template versioning, a follow-up change will be needed since snapshots are stored per event.

## Migration Plan
- Add new models and migrations for consent forms.
- Register Django admin for templates.
- Add views/urls and update patient timeline create event dropdown.
- Add PDF endpoint and optional attachment support.
- Add tests.

## Open Questions
- None.
