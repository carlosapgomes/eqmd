# Ward Model Implementation

## Your Mission

Rewrite the file @prompts/wards_implementantion_plan.md adding the missing steps to verify the app configuration and basic functionality before writing complex tests. Follow this project styling conventions, and add the additional recommendation described bellow.

## Important additional CONTEXT

- the initial hospital app plan @prompts/hospitalsapp.md
- the initial wards implementation sliced plan @prompts/wards_implementantion_plan.md
- Please read the file @prompts/testing_issues_analysis.md to learn about the some testing issues we encountered in the first implementation of the hospital plan slices, see the improved Slice 2 of @prompts/hospital_implementation_plan.md as an example.
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
