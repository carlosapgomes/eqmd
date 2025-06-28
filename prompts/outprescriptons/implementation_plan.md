<>context>
# Outpatient Prescription System Implementation Plan

## Overview

This implementation plan outlines the development of two interconnected features for the EquipeMed platform:
1. A **Drug Templates** system to manage medication information
2. An **Outpatient Prescription** feature that uses these drug templates to create printable prescriptions

The plan follows a vertical slicing approach, breaking down the implementation into discrete, testable components that build upon each other.
</context>
<PRD>
## App Structure

### Drug Templates App
- Independent app in the `apps/` directory following Django conventions
- Implements the `DrugTemplate` model with all required fields and functionality
- Provides management interface for creating, editing, and toggling visibility of templates

### Outpatient Prescriptions App
- Independent app in the `apps/` directory following Django conventions
- Imports and uses the Drug Templates app where necessary
- Extends the existing Event system with a new `OutpatientPrescription` model (event_type=11)
- Implements the `PrescriptionItem` model for individual drugs within a prescription
- Implements the `PrescriptionTemplate` model for reusable prescription configurations

## Implementation Requirements

### Technical Requirements
- Follow the vertical slicing approach used in other event implementations
- Create appropriate templates extending the base event templates
- Implement proper form validation for all user inputs
- Use Bootstrap 5.3.6 with the medical theme for consistent styling

### UI/UX Requirements
- All UI components must follow the established EquipeMed design patterns
- Reference existing apps like `apps/dailynotes`, `apps/simplenotes`, and `apps/mediafiles` for UI patterns
- Follow the styling guidelines in the `docs/` folder
- Implement the HTML+browser print strategy for prescription documents

### Integration Requirements
- Follow the existing permission system with appropriate decorators:
  - Use `@patient_access_required` for patient-specific operations
  - Use `@can_edit_event_required` for edit operations
  - Use `@can_delete_event_required` for delete operations
  - Use `@hospital_context_required` where appropriate
- Integrate with the hospital context middleware for proper hospital-based access control
- Maintain audit trail of prescription creation and modifications using the Event model's audit fields
- Ensure data independence between templates and actual prescriptions

## Detailed Implementation Plan

### Vertical Slice 1: Drug Templates App - Core Setup

#### Task 1: Initial App Setup
1. Create the drug templates app structure
   ```bash
   python manage.py startapp drugtemplates apps/drugtemplates
   ```
2. Add the app to INSTALLED_APPS in config/settings.py
3. Create initial app directory structure (models, views, forms, templates, etc.)
4. Verify app configuration with Django shell

#### Task 2: Drug Template Model Implementation
1. Create the `DrugTemplate` model with required fields:
   - Drug name (CharField, required)
   - Presentation (CharField for form, strength, etc.)
   - Usage instructions (TextField with markdown support)
   - Creator (ForeignKey to User model)
   - Visibility status (BooleanField for public/private)
   - Created/updated timestamps (auto_now_add/auto_now)
2. Implement model methods (`__str__`, `get_absolute_url`, etc.)
3. Add model validation for required fields
4. Create initial migration for the model

#### Task 3: Admin Interface Setup
1. Register the `DrugTemplate` model with the admin site
2. Customize the admin interface with list_display, search_fields, and filters
3. Add inline editing capabilities for related models (if any)
4. Implement custom admin actions for bulk operations

#### Task 4: Basic Model Testing
1. Create test cases for model creation and validation
2. Test model methods and properties
3. Verify field constraints and validation rules
4. Test model permissions and access control

### Vertical Slice 2: Drug Templates App - Forms and Views

#### Task 5: Drug Template Forms
1. Create `DrugTemplateForm` using crispy forms
2. Implement form validation for all fields
3. Add markdown editor support for usage instructions
4. Style form using Bootstrap 5.3.6 and medical theme

#### Task 6: Drug Template List View
1. Implement view to display all accessible drug templates (public + user's private)
2. Add filtering options (by name, creator, visibility)
3. Implement pagination for large result sets
4. Add sorting capabilities (by name, creation date, etc.)

#### Task 7: Drug Template Detail View
1. Create detail view to display complete drug template information
2. Add usage statistics display (how many times used in prescriptions)
3. Implement permission checks for private templates
4. Add links to edit/delete for templates created by the user

#### Task 8: Drug Template Create/Edit Views
1. Implement create view with form handling
2. Create edit view with permission checks
3. Add success messages and redirects
4. Implement CSRF protection and form validation

#### Task 9: Drug Template Delete View
1. Create delete confirmation view
2. Implement permission checks (only creator can delete)
3. Add success messages and redirects
4. Handle dependencies and prevent deletion if template is in use

### Vertical Slice 3: Drug Templates App - Templates and URLs

#### Task 10: Template Implementation
1. Create base template for drug templates app
2. Implement list template with filtering and pagination controls
3. Create detail template with complete information display
4. Implement create/edit form templates with proper styling

#### Task 11: URL Configuration
1. Create URL patterns for all views
2. Implement named URL patterns for reverse lookups
3. Add URL namespacing for the app
4. Test all URL patterns for correct routing

#### Task 12: Integration Testing
1. Create test cases for all views and forms
2. Test permission-based access control
3. Verify template rendering and form submission
4. Test URL routing and redirects

### Vertical Slice 4: Outpatient Prescriptions App - Core Setup

#### Task 13: Initial App Setup
1. Create the outpatient prescriptions app structure
   ```bash
   python manage.py startapp outpatientprescriptions apps/outpatientprescriptions
   ```
2. Add the app to INSTALLED_APPS in config/settings.py
3. Create initial app directory structure
4. Verify app configuration with Django shell

#### Task 14: Outpatient Prescription Model Implementation
1. Create the `OutpatientPrescription` model extending the Event model (event_type=11)
2. Add required fields and relationships
3. Implement model methods and properties
4. Create initial migration for the model

#### Task 15: Prescription Item Model Implementation
1. Create the `PrescriptionItem` model with fields:
   - Prescription (ForeignKey to OutpatientPrescription)
   - Drug name (copied from template or manually entered)
   - Presentation (copied from template or manually entered)
   - Usage instructions (copied from template or manually entered)
   - Amount to be prescribed (quantity field)
   - Order (IntegerField for sorting items)
2. Implement model methods and validation
3. Create migration for the model
4. Test model creation and relationships

#### Task 16: Prescription Template Model Implementation
1. Create the `PrescriptionTemplate` model with fields:
   - Name (CharField)
   - Creator (ForeignKey to User model)
   - Visibility status (BooleanField for public/private)
   - Created/updated timestamps
2. Create `PrescriptionTemplateItem` model for template items
3. Implement model methods and validation
4. Create migrations for both models

### Vertical Slice 5: Outpatient Prescriptions App - Forms and Views

#### Task 17: Prescription Forms
1. Create `OutpatientPrescriptionForm` extending from appropriate Event form
2. Implement `PrescriptionItemForm` for individual items
3. Create `PrescriptionItemFormSet` for handling multiple items
4. Implement form validation and error handling

#### Task 18: Prescription Template Forms
1. Create `PrescriptionTemplateForm` for template management
2. Implement `PrescriptionTemplateItemForm` for template items
3. Create `PrescriptionTemplateItemFormSet` for handling multiple items
4. Add validation and error handling

#### Task 19: Prescription List View
1. Implement view to display patient prescriptions
2. Add filtering and sorting options
3. Implement pagination for large result sets
4. Add links to create, view, edit, and delete prescriptions

#### Task 20: Prescription Create View
1. Implement create view with multi-step form process
2. Add drug template selection interface
3. Implement prescription template selection
4. Add free-text drug entry capability

#### Task 21: Prescription Detail and Print Views
1. Create detail view showing complete prescription information
2. Implement print view following HTML+browser print strategy
3. Style print view according to medical document standards
4. Add print button and functionality

#### Task 22: Prescription Template Management Views
1. Implement template list view with filtering options
2. Create template detail view
3. Add template create/edit views
4. Implement template delete view with confirmation

### Vertical Slice 6: Outpatient Prescriptions App - Templates and URLs

#### Task 23: Prescription Templates Implementation
1. Create base template for prescriptions app
2. Implement list template with filtering controls
3. Create detail template with complete information display
4. Implement create/edit form templates with proper styling

#### Task 24: Print Template Implementation
1. Create print-ready template following medical standards
2. Implement hospital/clinic information section
3. Add patient details section
4. Create medication list section with instructions

#### Task 25: URL Configuration
1. Create URL patterns for all prescription views
2. Implement URL patterns for prescription template views
3. Add URL namespacing for the app
4. Test all URL patterns for correct routing

### Vertical Slice 7: Integration and Testing

#### Task 26: Permission Integration
1. Apply appropriate permission decorators to all views
2. Implement hospital context integration
3. Add audit trail functionality
4. Test permission-based access control

#### Task 27: Data Independence Implementation
1. Implement copying mechanism from drug templates to prescription items
2. Ensure prescription items store complete information rather than references
3. Test data independence by modifying templates after prescription creation
4. Verify that existing prescriptions remain unchanged

#### Task 28: Comprehensive Testing
1. Create test cases for all models, views, and forms
2. Test the complete prescription workflow
3. Verify print functionality across browsers
4. Test permission rules and data independence

#### Task 29: Documentation
1. Create user documentation for both features
2. Add developer documentation with code examples
3. Document API endpoints and usage
4. Create deployment instructions

#### Task 30: Final Integration and Deployment
1. Perform final integration testing
2. Fix any remaining issues
3. Prepare deployment package
4. Create deployment checklist

## Success Criteria

### Drug Templates Feature
1. **Template Creation**
   - Doctors can create new drug templates with all required fields
   - Markdown support works correctly for dosage instructions
   - Templates can be saved as public or private

2. **Template Management**
   - Users can view a list of their own templates and public templates
   - Users can edit only templates they created
   - Users can toggle visibility status of their templates
   - Usage statistics are correctly tracked and displayed

### Outpatient Prescription Feature
1. **Core Workflow**
   - Users can create a new outpatient prescription for a patient
   - Users can select from existing prescription templates
   - Users can add additional drugs from drug templates
   - Users can add free-text drug entries not from templates
   - Users can specify amounts to be prescribed
   - Users can customize instructions for specific patients
   - Users can save and submit the prescription

2. **Template Usage**
   - Selecting a prescription template correctly populates the form
   - Users can save new prescription configurations as templates
   - Public/private visibility controls work correctly

3. **Print Functionality**
   - Generated prescriptions include all required elements
   - Print layout is professional and follows medical standards
   - Browser print functionality works correctly
   - Print CSS is properly applied

4. **Permissions and Security**
   - Only doctors and residents can create drug templates
   - Only doctors and residents can create prescription templates
   - Only doctors and residents can create outpatient prescriptions
   - Edit/delete permissions follow the 24-hour window rule
   - Hospital context is correctly applied to all operations

5. **Data Independence**
   - Changes to drug templates do not affect existing prescriptions
   - All prescription data is properly copied rather than linked

## Risk Mitigation

1. **Technical Risks**
   - Complex form handling: Use formsets and thorough testing
   - Print layout issues: Test across browsers and devices
   - Performance with large datasets: Implement pagination and optimization

2. **User Experience Risks**
   - Complex workflow: Create intuitive UI with clear guidance
   - Learning curve: Provide comprehensive documentation and tooltips
   - Printing inconsistencies: Standardize print CSS and test thoroughly

3. **Data Integrity Risks**
   - Template modifications affecting prescriptions: Implement proper copying
   - Data loss during form submission: Add form validation and auto-save
   - Concurrent edits: Implement proper locking or versioning

## Conclusion

This implementation plan provides a comprehensive roadmap for developing the Outpatient Prescription System. By following the vertical slicing approach, each component can be developed, tested, and deployed incrementally, ensuring a robust and reliable system that meets all requirements.
</PRD>