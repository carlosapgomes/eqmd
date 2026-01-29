## Why
Consent forms are currently handled outside the system. We need a consistent, auditable workflow that generates printable documents, stores an immutable markdown snapshot, and integrates with the patient timeline.

## What Changes
- Add admin-only consent template management in Django admin with activation/retirement and audit history
- Add consent form events that render templates into immutable markdown snapshots stored on the event
- Add consent form creation from the patient timeline with required inputs and defaulted patient fields
- Integrate on-demand PDF generation using the existing pdfgenerator services
- Allow optional scanned uploads (1-3 images or a single PDF) within the existing 24-hour edit window
- For uploads, follow the file upload and storage strategy used in apps/mediafiles

## Impact
- Affected specs: consent-forms
- Affected code: apps/events, apps/pdfgenerator, apps/outpatientprescriptions (pattern reuse), new consentforms app and templates
