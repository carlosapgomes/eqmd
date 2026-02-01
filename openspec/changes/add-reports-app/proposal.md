## Why


The system lacks a generic report document for low-volume use cases (referrals, reimbursement letters, internal communication). A templated report app fills this gap without creating a new app per document type.

## What Changes

- Add a new `reports` app with report templates and report events.
- Provide strict placeholder validation and deterministic server-side rendering.
- Add a report creation flow with EasyMDE editing and 24h edit/delete rules.
- Add PDF generation with letterhead, page breaks, and signature section.
- No attachments for reports.

## Capabilities

### New Capabilities
- `reports`: Create and manage generic report templates and patient reports with PDF output.

### Modified Capabilities
- None.

## Impact

- New Django app, models, migrations, views, and templates.
- New PDF generator and download endpoint for reports.
- Uses existing Event type `REPORT_EVENT` and existing PDF generator stack.
