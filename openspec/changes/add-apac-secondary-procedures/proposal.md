## Why
APAC submissions currently capture only a single procedure, but the national form requires one main procedure plus five secondary procedures. We need structured capture of all procedure slots with codes, descriptions, and UUIDs so overlays and audits are accurate.

## What Changes
- Add five optional secondary procedures to the APAC form (main remains required).
- Require selection from search suggestions and prevent duplicate procedures across slots.
- Persist UUID, code, and description for main and secondary procedures in submission data.
- Update the APAC form UI to render six searchable procedure inputs.
- Document the procedure key naming used for PDF overlay mapping.

## Impact
- Affected specs: pdf-forms (new)
- Affected code: apps/pdf_forms/views/national_forms.py, apps/pdf_forms/templates/pdf_forms/apac_form.html, tests, docs
