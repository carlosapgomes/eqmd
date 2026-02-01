## Why

Discharge reports currently rely on browser printing, which produces inconsistent output and lacks standardized hospital branding and pagination. We need a consistent, branded PDF output with proper signatures and to align discharge report actions with the rest of the system.

## What Changes

- Replace discharge report HTML print output with PDF generation using the shared PDF infrastructure.
- Add PDF download buttons in the discharge report detail page and the patient timeline card.
- Remove the legacy HTML print view/route for discharge reports.
- Fix delete permission behavior so finalized discharge reports can be deleted within the allowed time window.
- Add a delete button in the discharge report timeline card, respecting permissions.

## Capabilities

### New Capabilities
- `discharge-report-pdf`: Generate branded discharge report PDFs with pagination, page numbering, dates, and doctor signature, mirroring the current print layout content.
- `discharge-report-actions`: Provide consistent discharge report actions (PDF download and deletion) across detail view and timeline with correct permission enforcement.

### Modified Capabilities
- (none)

## Impact

- Affected apps: `apps/dischargereports`, `apps/events` (timeline card), `apps/pdfgenerator` (integration usage).
- URLs: remove discharge report `/print/` route; add `/pdf/` route.
- Templates: update detail page and event card actions to use PDF download button and delete button.
- Permissions: adjust delete logic for finalized discharge reports within the system’s edit/delete window.
- Tests: add/update discharge report view tests for PDF and deletion permissions.
