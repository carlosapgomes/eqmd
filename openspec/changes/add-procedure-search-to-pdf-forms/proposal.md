## Why

Hospital-specific PDF forms currently rely on manual text entry for procedure code and description fields. This leads to inconsistent data and user confusion, especially when procedures must match the national procedures table. The APAC form already provides a validated, user-friendly procedure search experience. We need the same capability in configurable hospital PDF forms without introducing new field types, using a simple naming convention that administrators can follow.

## What Changes

- Detect the naming convention `procedure_code` + `procedure_description` in PDF form field configurations.
- Render a combined procedure search input (code + description) in the hospital PDF form UI, matching the APAC search UX (spinner, dropdown results, debounce).
- Populate `procedure_code` and `procedure_description` fields from the selected procedure and prevent direct editing of those fields.
- Enforce selection from search suggestions (server-side validation against MedicalProcedure).
- Persist only `procedure_code` and `procedure_description` in submission data (no procedure UUID).

## Impact

- Affected specs: pdf-forms
- Affected code: apps/pdf_forms/services/form_generator.py, apps/pdf_forms/templates/pdf_forms/form_fill.html, apps/pdf_forms/templates/pdf_forms/partials/form_field.html, assets/js (new procedure search script), tests in apps/pdf_forms/tests
- Uses existing: apps/core/api/procedures.py (procedures_search_api), apps/core/models/medical_procedure.py
