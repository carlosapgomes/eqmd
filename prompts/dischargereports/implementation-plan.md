# Discharge Reports - Implementation Plan

## Overview
This plan outlines a phased approach to implementing the discharge reports feature as a Django app that extends the Event model, following established patterns in the codebase.

## Phase 1: Core Model and Basic Structure

### 1.1 Create Django App Structure
```bash
# Create app structure similar to dailynotes/outpatientprescriptions
apps/dischargereports/
├── __init__.py
├── admin.py
├── apps.py  
├── forms.py
├── models.py
├── urls.py
├── views.py
├── templatetags/
│   └── dischargereport_tags.py
├── templates/dischargereports/
│   ├── dischargereport_create.html
│   ├── dischargereport_detail.html
│   ├── dischargereport_update.html
│   ├── dischargereport_list.html
│   ├── dischargereport_confirm_delete.html
│   ├── dischargereport_print.html
│   └── partials/
└── migrations/
```

### 1.2 Create DischargeReport Model
- Extend Event model (similar to DailyNote)
- Add all required fields as specified:
  - admission_date (DateField)
  - discharge_date (DateField) 
  - admission_history (TextField)
  - problems_and_diagnosis (TextField) 
  - exams_list (TextField)
  - procedures_list (TextField)
  - inpatient_medical_history (TextField)
  - discharge_status (TextField)
  - discharge_recommendations (TextField) 
  - medical_specialty (CharField)
  - is_draft (BooleanField, default=True)
  - specialty (CharField) - for backward compatibility with Firebase data
- Override save() method to set event_type = Event.DISCHARGE_REPORT_EVENT
- Implement get_absolute_url() and get_edit_url()
- Add Portuguese verbose names and Meta class

### 1.3 Create Initial Migration
- Generate migration for the new model
- Run migration to create database table

### 1.4 Add App to Settings
- Add 'apps.dischargereports' to INSTALLED_APPS
- Register URLs in main urls.py

## Phase 2: Basic CRUD Views and Templates

### 2.1 Create Form Classes
- DischargeReportForm for create/update operations
- Include all model fields with appropriate widgets
- Add draft/save toggle functionality
- Implement field validation

### 2.2 Create Views
- CreateView with separate create template (not reused for edit)
- UpdateView with separate update template  
- DetailView for viewing reports
- ListView for browsing reports
- DeleteView for draft reports only
- Follow permission patterns from dailynotes

### 2.3 Create Templates
- Use Bootstrap 5.3 styling consistent with other apps
- Create responsive forms with proper field layouts
- Implement save as draft vs save definitively buttons
- Add proper form validation feedback

### 2.4 URL Configuration
- Create URLs following app naming conventions:
  - dischargereport_create
  - dischargereport_detail  
  - dischargereport_update
  - dischargereport_list
  - dischargereport_delete

## Phase 3: Event Integration and Timeline

### 3.1 Create Event Card Template
- Create event_card_dischargereport.html
- Extend event_card_base.html
- Show key information: specialty, admission/discharge dates, draft status
- Add appropriate action buttons (view, edit, print)

### 3.2 Update Event System
- Verify DISCHARGE_REPORT_EVENT (6) is properly defined in Event model
- Update event type icon and badge mappings for discharge reports
- Test event card display in patient timeline

### 3.3 Timeline Filtering
- Add discharge report filtering option to timeline
- Update timeline template to include discharge report filter
- Implement filter JavaScript functionality

## Phase 4: Print/PDF Functionality

### 4.1 Create Print Template
- Model after outpatientprescription_print.html
- Include all specified sections in Portuguese:
  - Header with hospital branding and "Relatório de Alta"
  - Patient identification section
  - All content sections in specified order
  - Footer with generation info and pagination
- Implement proper CSS for print layout

### 4.2 Add Print View
- Create print view that renders the print template
- Include PDF generation option using existing patterns
- Add print button to detail and event card templates

### 4.3 CSS Styling
- Create print-specific CSS
- Ensure proper pagination for multi-page reports
- Style Brazilian Portuguese section headers

## Phase 5: Firebase Import Management Command

### 5.1 Create Import Command
- Create apps/dischargereports/management/commands/import_firebase_discharge_reports.py
- Model after sync_firebase_data.py structure
- Handle Firebase "patientDischargeReports" reference

### 5.2 Implement Data Mapping
```python
# Firebase field -> Django model field mapping:
{
    'admissionDate': 'admission_date',
    'dischargeDate': 'discharge_date', 
    'admissionHistory': 'admission_history',
    'problemsAndDiagnostics': 'problems_and_diagnosis',
    'examsList': 'exams_list',
    'proceduresList': 'procedures_list',
    'inpatientMedicalHistory': 'inpatient_medical_history',
    'patientDischargeStatus': 'discharge_status',
    'dischargeRecommendations': 'discharge_recommendations',
    'specialty': 'medical_specialty'
}
```

### 5.3 PatientAdmission Creation
- Create AdmissionRecord for each imported report
- Set appropriate fields:
  - admission_type = 'scheduled'
  - discharge_type = 'medical'
  - is_active = False
  - Calculate stay_duration_days
  - Empty beds/wards/diagnoses

### 5.4 Documentation and Testing
- Create comprehensive feature documentation in docs/apps/dischargereports.md
- Document Firebase import command usage and Docker examples
- Test import process with sample Firebase data

## Phase 6: Permissions and Security

### 6.1 Implement Draft Logic
- Only allow edit/delete of draft reports
- Once not draft, follow standard 24h event edit window
- Update templates to show/hide actions based on draft status

### 6.2 Permission Integration
- Follow existing event permission patterns
- Ensure proper user access control
- Test with different user roles (doctors, residents, nurses)

### 6.3 Admin Interface
- Create admin.py with proper ModelAdmin
- Enable history tracking display
- Configure list display and filters

## Phase 7: Testing and Documentation

### 7.1 Create Tests
- Model tests for validation and methods
- View tests for CRUD operations
- Permission tests for draft vs final reports
- Integration tests for timeline display
- Firebase import tests

### 7.2 Template Testing
- Test responsive design on different screen sizes
- Verify print layout and PDF generation
- Test form validation and user feedback

### 7.3 Documentation Updates
- Update CLAUDE.md with testing commands
- Document Firebase import process
- Add app-specific documentation following project patterns

## Implementation Notes

### Key Design Decisions
1. **Separate Create/Update Templates**: Following the requirement to not reuse create template for editing
2. **Draft System**: Implementing is_draft with default True and save options
3. **Single Specialty Field**: Using medical_specialty field, mapping from Firebase specialty during import
4. **Event Integration**: Full integration with timeline and event system
5. **Print Focus**: Proper Brazilian Portuguese PDF generation with pagination

### Technical Considerations
1. **Date Handling**: Proper timezone handling for admission/discharge dates
2. **Text Fields**: Large text capacity for medical content
3. **Firebase Migration**: Robust error handling and data validation
4. **Performance**: Proper indexing for queries and timeline display
5. **Security**: Draft-only editing with standard event permissions thereafter

### Dependencies
- Existing Event model and system
- Patient and PatientAdmission models
- Hospital template tags for print headers
- Firebase admin SDK for import command
- Bootstrap 5.3 for styling

This implementation plan provides a comprehensive roadmap for developing the discharge reports feature while maintaining consistency with existing codebase patterns and ensuring all requirements are met.