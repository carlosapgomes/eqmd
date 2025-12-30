# Patient Gender Field Implementation Plan

## Overview

Add a gender/sex field to the Patient model and integrate it throughout the application's templates, forms, and display components.

## Step 1: Model Changes

### 1.1 Update Patient Model (`apps/patients/models.py`)

- Add gender field with appropriate choices:

  ```python
  class GenderChoices(models.TextChoices):
      MALE = 'M', 'Masculino'
      FEMALE = 'F', 'Feminino'
      OTHER = 'O', 'Outro'
      NOT_INFORMED = 'N', 'Não Informado'

  gender = models.CharField(
      max_length=1,
      choices=GenderChoices.choices,
      default=GenderChoices.NOT_INFORMED,
      verbose_name="Sexo"
  )
  ```

- Position the field logically after `birthday` field for consistency with personal information grouping

## Step 2: Form Updates

### 2.1 Update Patient Forms (`apps/patients/forms.py`)

- Add gender field to `PatientForm`
- Add gender field to `PatientCreateForm`
- Add gender field to `PatientUpdateForm`
- Ensure proper field ordering in Meta.fields
- Add appropriate widget styling if needed

## Step 3: Template Updates

### 3.1 Patient Detail Template (`apps/patients/templates/patients/patient_detail.html`)

- Add gender display in patient information section
- Position after birthday field for logical flow
- Use proper Portuguese labeling ("Sexo:")

### 3.2 Patient List Template (`apps/patients/templates/patients/patient_list.html`)

- Consider adding gender as optional column (may make table too wide)
- Evaluate if gender should be shown in list view or kept for detail view only

### 3.3 Patient Form Templates

- Update `patient_form.html` to include gender field
- Update `patient_create.html` to include gender field
- Update `patient_update.html` to include gender field
- Ensure proper Bootstrap styling and form layout

### 3.4 Patient Widgets

- Update `patient_stats.html` widget to potentially include gender statistics
- Update `recent_patients.html` widget if gender should be displayed

## Step 4: Admin Interface Updates

### 4.1 Update Admin Configuration (`apps/patients/admin.py`)

- Add gender to list_display if appropriate
- Add gender to list_filter for filtering patients by gender
- Add gender to search_fields if needed
- Update fieldsets to include gender in personal information section

## Step 5: API Updates (if applicable)

### 5.1 Update API Serializers

- Check if there are any API serializers that need to include gender field
- Update any ViewSets or API views that handle patient data

## Step 6: Template Tags and Filters

### 6.1 Patient Template Tags (`apps/patients/templatetags/patient_tags.py`)

- Add any gender-related template tags if needed
- Consider adding gender display formatting tags

## Step 7: Test Updates

### 7.1 Model Tests (`apps/patients/tests/test_models.py`)

- Add tests for gender field validation
- Test gender choices
- Test default value

### 7.2 Form Tests (`apps/patients/tests/test_forms.py`)

- Add tests for gender field in forms
- Test form validation with gender field

### 7.3 View Tests (`apps/patients/tests/test_views.py`)

- Update existing tests to include gender field
- Test patient creation/update with gender

### 7.4 Template Tests (`apps/patients/tests/test_templates.py`)

- Test gender display in templates
- Test form rendering with gender field

## Step 8: Factory Updates

### 8.1 Update Test Factories

- Update patient factories to include gender field
- Ensure realistic test data generation

## Step 9: Sample Data Updates

### 9.1 Management Commands

- Update any sample data creation commands to include gender
- Ensure sample patients have realistic gender distribution

## Step 10: Documentation Updates

### 10.1 Update Model Documentation

- Update any model documentation to reflect new gender field
- Update API documentation if applicable

## Implementation Order Priority

1. Model changes (Step 1)
2. Form updates (Step 2)
3. Core template updates (Step 3.1, 3.3)
4. Admin interface (Step 4)
5. Test updates (Step 7)
6. Optional template updates (Step 3.2, 3.4)
7. Factory and sample data updates (Step 8, 9)
8. Documentation (Step 10)

## Considerations

### UI/UX Considerations

- Gender field should be prominently placed in forms but not overwhelming
- Consider using radio buttons instead of dropdown for better UX
- Ensure proper spacing and alignment in form layouts

### Data Considerations

- Default to "Não Informado" to handle legacy data gracefully
- Consider if gender statistics should be added to dashboard widgets
- Evaluate if gender filtering is needed in patient search/list views

### Accessibility

- Ensure proper labels and ARIA attributes for screen readers
- Test keyboard navigation for gender field
- Ensure proper color contrast for any gender-specific styling

### Localization

- All labels and choices should be in Portuguese
- Ensure proper gender terminology for medical context
- Consider cultural sensitivity in gender options

## Files to be Modified

- `apps/patients/models.py`
- `apps/patients/forms.py`
- `apps/patients/admin.py`
- `apps/patients/templates/patients/patient_detail.html`
- `apps/patients/templates/patients/patient_form.html`
- `apps/patients/templates/patients/patient_create.html`
- `apps/patients/templates/patients/patient_update.html`
- `apps/patients/tests/test_models.py`
- `apps/patients/tests/test_forms.py`
- `apps/patients/tests/test_views.py`
- Test factories and sample data commands
