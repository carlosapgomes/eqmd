# Patients Listing Bug Fix Plan

## Bug Description

The patients list view has a filtering issue. When a user first accesses the list, it correctly defaults to showing only patients from the user's current hospital. However, when the user tries to filter by another hospital, the list incorrectly shows all patients from all hospitals instead of just the selected hospital.

## Root Cause Analysis

Based on the available information, this appears to be a filtering logic issue in the patients list view. The initial filter works correctly, but the subsequent filter selection isn't being properly applied.

## Step-by-Step Fix Plan

### 1. Examine the Current View Implementation

- Locate the patient list view in `apps/patients/views.py`
- Identify how the initial hospital filter is being applied
- Check how the filter form is being processed

### 2. Inspect the Filter Form

- Examine the form used for filtering patients
- Check how the hospital selection is being processed
- Verify that the form is correctly passing the hospital parameter

### 3. Debug the Query Construction

- Add debug logging to see what query parameters are being applied
- Check if the hospital filter is being overridden somewhere
- Verify that the hospital parameter from the form is being correctly added to the queryset

### 4. Fix the View Logic

- Modify the view to properly handle the hospital filter parameter
- Ensure that when a hospital is selected in the filter form, it correctly filters the queryset
- Make sure the filter doesn't reset to showing all patients

### 5. Update the Template

- Verify that the filter form in the template is correctly submitting the hospital parameter
- Check if there are any JavaScript interactions that might be interfering with the filter

### 6. Test the Fix

- Test with a user who has access to multiple hospitals
- Verify that the initial filter shows only the current hospital's patients
- Test selecting different hospitals from the filter and verify only patients from the selected hospital are shown
- Test other filter combinations to ensure they work correctly with the hospital filter

### 7. Add Regression Tests

- Add a test case that verifies the hospital filter works correctly
- Include tests for both the initial filter and subsequent filter selections
- Test combinations of filters to ensure they all work together

### 8. Documentation

- Update any relevant documentation about the patients list filtering
- Document the fix in the commit message with clear explanation of what was changed and why

## Potential Issues to Check

1. The view might be resetting the queryset instead of filtering the existing one
2. The form might not be correctly passing the hospital parameter
3. There might be a condition that's bypassing the hospital filter when other filters are applied
4. The URL parameters might not be correctly preserved when the form is submitted

This plan should help identify and fix the bug in the patients list view filtering functionality.
