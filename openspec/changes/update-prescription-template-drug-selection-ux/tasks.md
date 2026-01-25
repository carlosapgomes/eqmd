## 1. Implementation

- [x] 1.1 Update `PrescriptionTemplateItemForm` in `apps/drugtemplates/forms.py` to use `AutoCompleteWidget` and `DrugTemplateField`
- [x] 1.2 Add `drug_templates` to context in `PrescriptionTemplateCreateView.get_context_data()`
- [x] 1.3 Add `drug_templates` to context in `PrescriptionTemplateUpdateView.get_context_data()`
- [x] 1.4 Update `prescriptiontemplate_create_form.html` template structure with autocomplete
- [x] 1.5 Update `prescriptiontemplate_update_form.html` template structure with autocomplete
- [x] 1.6 Update drug name input field HTML to include autocomplete wrapper and search spinner
- [x] 1.7 Remove custom formset JavaScript from templates (addFormsetItem, deleteFormsetItem functions)
- [x] 1.8 Update empty form template in JavaScript to match new structure
- [x] 1.9 Update container ID from `#formset-container` to `#prescription-items-container` in both template files
- [x] 1.10 Run tests to validate changes (Note: pre-existing test failures are unrelated to this change - see summary)

## 2. Testing

- [ ] 2.1 Test creating a new prescription template with autocomplete search
- [ ] 2.2 Test selecting a drug from autocomplete dropdown
- [ ] 2.3 Verify all fields populate correctly (drug_name, presentation, usage_instructions, quantity)
- [ ] 2.4 Test adding multiple medication items
- [ ] 2.5 Test removing medication items
- [ ] 2.6 Test reordering items (up/down buttons)
- [ ] 2.7 Test updating an existing prescription template
- [ ] 2.8 Test validation (empty fields, required fields)
- [ ] 2.9 Test that data is copied (not referenced) from templates
- [ ] 2.10 Verify existing outpatientprescription template selector still works
