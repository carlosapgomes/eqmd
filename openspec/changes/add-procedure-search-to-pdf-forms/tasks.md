## 1. Discovery
- [ ] 1.1 Review APAC procedure search UX and map which behaviors must be mirrored (debounce, spinner, dropdown, selection enforcement).
- [ ] 1.2 Confirm how sectioned vs legacy form rendering should place the combined search input and hide raw fields.

## 2. Tests
- [ ] 2.1 Add tests for procedure search detection when both `procedure_code` and `procedure_description` are present.
- [ ] 2.2 Add validation tests rejecting submissions with free-text procedure values not found in MedicalProcedure.
- [ ] 2.3 Add integration test that form_fill renders a combined search input and does not render editable code/description fields.
- [ ] 2.4 Add submission test to confirm stored form_data includes only `procedure_code` and `procedure_description` (no UUID).

## 3. Implementation
- [ ] 3.1 Add a helper to detect the procedure field pair and expose metadata (display field name, target fields, required state).
- [ ] 3.2 Update DynamicFormGenerator to add a synthetic display field and mark `procedure_code` / `procedure_description` widgets as hidden or readonly.
- [ ] 3.3 Extend generated form validation to require a valid MedicalProcedure selection (e.g., code exists; optional description match).
- [ ] 3.4 Update form_fill rendering to insert the combined search UI (spinner + results dropdown) and to skip raw fields.
- [ ] 3.5 Add a procedure search JS module (assets/js) based on APAC behavior: debounce, spinner, dropdown, selection enforcement, and clearing.
- [ ] 3.6 Wire the JS into the build and include it only when procedure search metadata is present.

## 4. Documentation
- [ ] 4.1 Document the naming convention and expected field types in the PDF form configuration guide.
