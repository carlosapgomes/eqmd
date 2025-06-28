# Outpatient Prescription System Implementation Requirements

## Overview
Implement two interconnected features for the EquipeMed platform:
1. A **Drug Templates** system to manage medication information
2. An **Outpatient Prescription** feature that uses these drug templates to create printable prescriptions

## Drug Templates Feature

### Core Functionality
- Create a `DrugTemplate` model to store medication information including:
  - Drug name (required)
  - Presentation (form, strength, etc.)
  - Usage instructions (dosage, frequency, duration)
  - Creator (ForeignKey to User model)
  - Visibility status (public/private boolean field)
  - Created/updated timestamps for audit trail

### Visibility Control
- Each drug template must have a public/private status:
  - **Private**: Only visible to and usable by the creating user
  - **Public**: Available to all system users regardless of creator

### User Experience
- Allow users to create personalized drug templates with their preferred:
  - Dosage instructions (text field with markdown support)
  - Administration routes (selectable from predefined options)
  - Standard warnings/instructions (text field)
- Provide a management interface for users to:
  - Create new drug templates
  - Edit existing templates (only those they created)
  - Toggle public/private status (only for templates they created)
  - View usage statistics (how many times template was used in prescriptions)

## Outpatient Prescription Feature

### Core Functionality
- Extend the existing Event system with a new `OutpatientPrescription` model (event_type=11)
- Create a `PrescriptionItem` model to store individual drugs within a prescription
- Allow users to:
  - Create new prescriptions for patients
  - Add multiple drugs from templates to a prescription
  - Add drugs not from templates (free-text entry)
  - Add the amount to be prescribed (i.e. number of pills, mL, etc.)
  - Customize drug instructions for specific patients
  - Save prescriptions as reusable templates
  - Generate printable documents using the HTML+browser print strategy (not server-side PDF)

### Prescription Templates
- Create a `PrescriptionTemplate` model to store reusable prescription configurations:
  - **Private templates**: Only available to the creating user
  - **Public templates**: Available to all system users
- Templates should store:
  - A predefined list of drugs (from drug templates)
  - Standard header/footer information
  - Creator information (ForeignKey to User model)
  - Visibility status (public/private boolean field)
  - Created/updated timestamps

### Print-Ready Document Generation
- Follow the established HTML+browser print strategy documented in styling.md
- Generate professional medical prescription documents following medical document standards
- Include all necessary prescription elements:
  - Hospital/clinic information (from current hospital context)
  - Patient details (name, ID, age)
  - Medication list with instructions
  - Physician information and signature area
  - Date and validity information
- Use the print.css stylesheet for proper document formatting

## Integration Requirements
- Follow the existing EquipeMed permission system:
  - Use `@patient_access_required` for patient-specific operations
  - Use `@can_edit_event_required` for edit operations
  - Use `@can_delete_event_required` for delete operations
  - Use `@hospital_context_required` where appropriate
- Integrate with the hospital context middleware for proper hospital-based access control
- Maintain audit trail of prescription creation and modifications using the Event model's audit fields
- Follow established medical styling guidelines from docs/styling.md

## Data Independence Requirements
- When creating an outpatient prescription for a patient or a prescription template, copy the content from drug templates rather than linking directly:
  - This ensures that if a drug template is later modified, those changes will not affect existing prescriptions
  - Store complete drug information in the PrescriptionItem model
- Permission rules:
  - Drug templates: Always editable by their creator regardless of age
  - Prescription templates: Always editable by their creator regardless of age
  - Saved outpatient prescription events: Follow the standard 24-hour edit/delete window as defined by the permissions:
    - `edit_own_event_24h`: Can edit own events within 24 hours
    - `delete_own_event_24h`: Can delete own events within 24 hours

## Technical Implementation Details
- Follow the vertical slicing approach used in other event implementations
- Create appropriate templates extending the base event templates
- Implement proper form validation for all user inputs
- Use Bootstrap 5.3.6 with the medical theme for consistent styling

## Success Criteria
- Doctors and residents can successfully create, edit, and manage drug templates
- Users can create outpatient prescriptions using both templates and manual drug entries
- Prescriptions generate properly formatted, professional-looking printable documents
- The system maintains data independence between templates and actual prescriptions
- All functionality works correctly within the hospital context system
- The interface is intuitive and follows established EquipeMed design patterns

## Acceptance Tests

### Drug Templates Feature
1. **Template Creation**
   - [ ] Doctors can create new drug templates with all required fields
   - [ ] Markdown support works correctly for dosage instructions
   - [ ] Templates can be saved as public or private

2. **Template Management**
   - [ ] Users can view a list of their own templates and public templates
   - [ ] Users can edit only templates they created
   - [ ] Users can toggle visibility status of their templates
   - [ ] Usage statistics are correctly tracked and displayed

### Outpatient Prescription Feature
1. **Core Workflow**
   - [ ] Users can create a new outpatient prescription for a patient
   - [ ] Users can select from existing prescription templates
   - [ ] Users can add additional drugs from drug templates
   - [ ] Users can add free-text drug entries not from templates
   - [ ] Users can specify amounts to be prescribed
   - [ ] Users can customize instructions for specific patients
   - [ ] Users can save and submit the prescription

2. **Template Usage**
   - [ ] Selecting a prescription template correctly populates the form
   - [ ] Users can save new prescription configurations as templates
   - [ ] Public/private visibility controls work correctly

3. **Print Functionality**
   - [ ] Generated prescriptions include all required elements
   - [ ] Print layout is professional and follows medical standards
   - [ ] Browser print functionality works correctly
   - [ ] Print CSS is properly applied

4. **Permissions and Security**
   - [ ] Only doctors and residents can create drug templates
   - [ ] Only doctors and residents can create prescription templates
   - [ ] Only doctors and residents can create outpatient prescriptions
   - [ ] Edit/delete permissions follow the 24-hour window rule
   - [ ] Hospital context is correctly applied to all operations

5. **Data Independence**
   - [ ] Changes to drug templates do not affect existing prescriptions
   - [ ] All prescription data is properly copied rather than linked

