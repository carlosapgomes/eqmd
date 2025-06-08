# Patients App Implementation Plan

## Your Mission

Read the file @prompts/patientsapp.md and make a detailed step-by-step plan to implement its features using a vertical slicing approach. Think hard to be as detailed as possible and follow the testing, styling, and all the additional recommendations bellow.

## Important additional CONTEXT

- the Wards model is not implemented yet, so you don't need to worry about it, just leave comments in the code to implement any functionality related to it later.
- for an example of a detailed vertical sliced plan, see the wards implementation sliced plan at @prompts/wards_implementantion_plan.md
- Please read the file @prompts/testing_issues_analysis.md and follow its recommendations for writing tests.
- Read the file @docs/styling.md and follow its recommendations for any UI or templating related task. Remember to use django crispy forms and crispy bootstrap 5 whenever possible.

## Additional Recommendations

1. **For All Slices**:

   - Always verify app configuration before running complex tests
   - Use Django shell for quick verification of model changes
   - Test both positive and negative cases (e.g., permissions denied)

2. **For Views**:

   - Test with authenticated and unauthenticated users
   - Verify proper redirect behavior for unauthorized access
   - Test with various user roles/permissions

3. **For Forms**:

   - Test validation with both valid and invalid data
   - Verify error messages are displayed correctly
   - Test form submission with missing required fields

4. **For Templates**:

   - Verify responsive design on different screen sizes
   - Test accessibility features
   - Ensure consistent styling with the rest of the application

5. **For Related Data**:
   - Test performance with large datasets
   - Implement pagination for related data lists
   - Consider using select_related/prefetch_related for optimization
