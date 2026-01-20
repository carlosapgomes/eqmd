## Why

The APAC form currently uses plain text inputs for ICD-10 (CID) diagnosis codes (main_icd, secondary_icd, other_icd). This lacks validation against the Icd10Code model, allows invalid codes to be submitted, and provides no autocomplete. The procedures search pattern already exists and provides a validated, user-friendly selection experience that should be replicated for ICD-10 codes.

## What Changes

- Replace plain text inputs with searchable autocomplete inputs for main_icd, secondary_icd, and other_icd fields in the APAC form.
- Add hidden UUID fields to store selected ICD-10 code IDs.
- Add JavaScript to handle ICD-10 search using the existing icd10_search_api endpoint.
- Display search results with code and description, but populate the input field only with the code after selection.
- Update form validation to require selection from search suggestions for required ICD-10 fields.
- Persist UUID, code, and description for selected ICD-10 codes in APAC submission data.
- Update the APAC template HTML to render three searchable ICD-10 inputs matching the procedure search UI pattern, including consistent spinner styling and behavior.

## Impact

- Affected specs: pdf-forms
- Affected code: apps/pdf_forms/views/national_forms.py (APACForm, APACFormView), apps/pdf_forms/templates/pdf_forms/apac_form.html, tests
- Uses existing: apps/core/api/icd10_codes.py (icd10_search endpoint), apps/core/models/icd10_code.py (Icd10Code model)
