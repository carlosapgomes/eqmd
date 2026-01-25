## Why

Prescription template create/update forms currently use manual text input fields for drug selection, providing a different and inferior user experience compared to outpatient prescriptions. The outpatient prescription form has autocomplete search and template integration that users expect. Inconsistency in UX across similar forms creates confusion and reduces efficiency.

## What Changes

- Update `PrescriptionTemplateItemForm` to use `AutoCompleteWidget` for drug name field (same as outpatient prescriptions)
- Add `DrugTemplateField` to prescription template item form for dropdown selection (optional)
- Add `drug_templates` to context in `PrescriptionTemplateCreateView` and `PrescriptionTemplateUpdateView`
- Update prescription template create/update templates to:
  - Include `prescription_forms.css` for consistent styling
  - Include `prescription_forms.js` for formset management
  - Include `drug_template_integration.js` for autocomplete functionality
  - Replace manual drug name input structure with autocomplete-enabled version
  - Update container ID from `#formset-container` to `#prescription-items-container` to match shared JS expectations
  - Remove custom formset JavaScript (use shared JS files instead)
- Reuse existing AJAX endpoints from outpatientprescriptions app for drug template search and data retrieval
- Update drug name input fields to show search spinner and autocomplete dropdown

## Impact

- Affected specs: prescription-templates (drug selection UX)
- Affected code:
  - `apps/drugtemplates/forms.py` (PrescriptionTemplateItemForm updates)
  - `apps/drugtemplates/views.py` (context updates)
  - `apps/drugtemplates/templates/drugtemplates/prescriptiontemplate_create_form.html` (template restructuring)
  - `apps/drugtemplates/templates/drugtemplates/prescriptiontemplate_update_form.html` (template restructuring)
- Reused assets (no changes):
  - `apps/outpatientprescriptions/static/outpatientprescriptions/css/prescription_forms.css`
  - `apps/outpatientprescriptions/static/outpatientprescriptions/js/prescription_forms.js`
  - `apps/outpatientprescriptions/static/outpatientprescriptions/js/drug_template_integration.js`
  - `apps/outpatientprescriptions/widgets.py` (AutoCompleteWidget, DrugTemplateField)
