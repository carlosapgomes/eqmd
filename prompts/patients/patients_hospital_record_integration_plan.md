# Hospital Record Integration Plan

## Overview

This plan outlines the steps to integrate hospital record management into the patient edit form, providing an additional entry point for creating and updating hospital records while maintaining the existing functionality.

## Implementation Steps

### 1. Update Patient Form Template

- [ ] Modify `apps/patients/templates/patients/patient_form.html` to include a hospital record section
- [ ] Add conditional logic to show/hide based on patient status
- [ ] Create collapsible section for hospital records (to keep form clean)
- [ ] Add UI elements for adding/editing hospital record

### 2. Update Patient Form

- [ ] Modify `apps/patients/forms.py` to include hospital record fields
- [ ] Create a nested form or formset for hospital record data
- [ ] Add validation for hospital record fields
- [ ] Handle conditional field requirements based on patient status

### 3. Update Patient Views

- [ ] Modify `PatientCreateView` and `PatientUpdateView` in `apps/patients/views.py`
- [ ] Add logic to process hospital record data from form submission
- [ ] Implement save method to handle both patient and hospital record data
- [ ] Add success messages for hospital record creation/updates

### 4. Add JavaScript Enhancements

- [ ] Add JS to show/hide hospital record section based on patient status selection
- [ ] Implement dynamic field validation
- [ ] Add AJAX functionality for hospital selection (optional)
- [ ] Ensure mobile responsiveness for the expanded form

### 5. Update Models (if needed)

- [ ] Review `Patient` and `PatientHospitalRecord` models for any needed adjustments
- [ ] Add helper methods to simplify view logic

### 6. Update Tests

- [ ] Add tests for the new form functionality
- [ ] Test hospital record creation during patient creation/update
- [ ] Test validation rules and error handling
- [ ] Test UI behavior with different patient statuses

### 7. Update Documentation

- [ ] Update `docs/patients/hospital_records.md` to include the new entry point
- [ ] Add screenshots or diagrams showing the new workflow
- [ ] Update user guides to reflect the new functionality

### 8. Final Review and Testing

- [ ] Conduct usability testing with sample users
- [ ] Review mobile responsiveness
- [ ] Check accessibility compliance
- [ ] Verify all existing functionality still works correctly
