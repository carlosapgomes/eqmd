# Discharge Reports (apps/dischargereports)

**Medical discharge report management system with draft/final workflow.**

## Overview

The discharge reports app provides comprehensive medical discharge report creation, editing, and management. It extends the Event model to integrate seamlessly with the patient timeline system, supporting autonomous agent workflows where reports can be prepared in advance and reviewed by medical staff.

## Features

### Core Functionality
- **Draft System**: Reports start as drafts and can be finalized by doctors/residents
- **Event Integration**: Full integration with patient timeline as Event type 6
- **Autonomous Agent Support**: Drafts can be created automatically and reviewed later
- **Role-Based Permissions**: Doctors/residents have special editing privileges
- **Portuguese Localization**: All labels, messages, and help text in Portuguese

### Draft Logic
- New reports default to `is_draft = True`
- **Draft reports**: Unlimited editing/deletion by doctors and residents
- **Final reports**: Follow 24-hour system standards (creator-only)
- Two save options: "Salvar Rascunho" and "Salvar Definitivo"

## Model Structure

### DischargeReport Fields

The `DischargeReport` model extends the base `Event` model with these medical-specific fields:

#### Date Fields
- `admission_date`: Date of hospital admission (DateField, required)
- `discharge_date`: Date of hospital discharge (DateField, required)

#### Medical Content Fields
- `medical_specialty`: Medical specialty responsible for discharge (CharField, max 100)
- `admission_history`: Clinical admission history (TextField)
- `problems_and_diagnosis`: Main problems and diagnoses (TextField) 
- `exams_list`: Exams performed during hospitalization (TextField)
- `procedures_list`: Procedures performed during stay (TextField)
- `inpatient_medical_history`: Medical evolution during hospitalization (TextField)
- `discharge_status`: Patient condition at discharge (TextField)
- `discharge_recommendations`: Post-discharge care recommendations (TextField)

#### System Fields
- `is_draft`: Boolean indicating draft status (default: True)
- Inherits from Event: `patient`, `event_datetime`, `description`, `created_by`, etc.

### Model Methods
- `save()`: Automatically sets `event_type = Event.DISCHARGE_REPORT_EVENT` (6)
- `get_absolute_url()`: Returns detail view URL
- `get_edit_url()`: Returns update view URL
- `__str__()`: Returns formatted string with patient name, date, and draft status

### Database Indexes
- `admission_date`: For filtering by admission date
- `discharge_date`: For filtering by discharge date  
- `is_draft`: For separating drafts from finals
- `medical_specialty`: For filtering by specialty

## Permissions System

### Business Logic

The discharge reports use a custom permission system that differs from standard events:

#### Draft Reports
- **Editing**: ✅ **Unlimited time** - Any doctor/resident can edit
- **Deletion**: ✅ **Unlimited time** - Any doctor/resident can delete
- **Who**: Medical doctors (`MEDICAL_DOCTOR`) and residents (`RESIDENT`) only

#### Final Reports  
- **Editing**: ⏰ **24 hours** from creation + creator-only (system standards)
- **Deletion**: ⏰ **24 hours** from creation + creator-only (system standards)
- **Who**: Only the person who finalized the report

### Permission Functions
- `can_edit_discharge_report(user, report)`: Custom edit permission logic
- `can_delete_discharge_report(user, report)`: Custom delete permission logic
- Uses `apps.core.permissions.can_edit_event()` and `can_delete_event()` for final reports

### Template Tags
- `can_edit_discharge_report_tag`: Template tag for edit button visibility
- `can_delete_discharge_report_tag`: Template tag for delete button visibility

## URLs and Views

### URL Patterns
- `/dischargereports/` - List view with pagination
- `/dischargereports/create/` - Create new discharge report
- `/dischargereports/<uuid:pk>/` - Detail view (read-only)
- `/dischargereports/<uuid:pk>/update/` - Edit existing report
- `/dischargereports/<uuid:pk>/delete/` - Delete confirmation

### View Classes

#### DischargeReportListView
- **Purpose**: Browse all discharge reports with search and filtering
- **Features**: Pagination (20 per page), status badges, action buttons
- **Template**: `dischargereport_list.html`
- **Permissions**: Login required

#### DischargeReportCreateView
- **Purpose**: Create new discharge reports
- **Features**: Draft/final save options, form validation, auto-set creator
- **Template**: `dischargereport_create.html`
- **Save Options**:
  - "Salvar Rascunho": Saves as draft (`is_draft=True`)
  - "Salvar Definitivo": Saves as final (`is_draft=False`)

#### DischargeReportDetailView
- **Purpose**: View discharge report details in read-only format
- **Features**: Organized sections, metadata display, conditional edit button
- **Template**: `dischargereport_detail.html`
- **Sections**: Basic info, dates, medical content, metadata

#### DischargeReportUpdateView
- **Purpose**: Edit existing discharge reports
- **Features**: Separate template from create, conditional save buttons, permission checking
- **Template**: `dischargereport_update.html`
- **Logic**: Shows different buttons based on draft status

#### DischargeReportDeleteView
- **Purpose**: Delete discharge reports with confirmation
- **Features**: Confirmation dialog, permission validation, success messages
- **Template**: `dischargereport_confirm_delete.html`
- **Restrictions**: Custom permission logic for drafts vs finals

## Form System

### DischargeReportForm

The main form class extends `ModelForm` with:

#### Form Fields
All model fields except system-generated ones:
- Basic: `patient`, `event_datetime`, `description`
- Dates: `admission_date`, `discharge_date` 
- Medical: All content fields listed above

#### Widget Configuration
- Bootstrap 5.3 CSS classes on all inputs
- Date widgets: `type="date"` HTML5 inputs
- DateTime widget: `type="datetime-local"` for event time
- Textarea widgets: Configurable rows (3-6) based on content type
- Placeholders: Helpful examples (e.g., "Ex: Cardiologia")

#### Form Validation
- **Date Logic**: Admission date must be before discharge date
- **Custom Clean**: Validates date relationship with Portuguese error message
- **Required Fields**: All medical content fields are required

## Templates

### Template Structure

All templates extend `base.html` and use Bootstrap 5.3 styling:

#### dischargereport_create.html
- **Purpose**: New report creation form
- **Features**: Manual field rendering, icons, error display, dual save buttons
- **Layout**: Two-column responsive grid for dates, full-width textareas

#### dischargereport_update.html  
- **Purpose**: Edit existing reports (separate from create)
- **Features**: Same layout as create, conditional buttons based on draft status
- **Logic**: Shows different save options for drafts vs final reports

#### dischargereport_list.html
- **Purpose**: Browse all reports with table view
- **Features**: 
  - Sortable columns: Patient, specialty, dates, status, created time
  - Status badges: Draft (warning) vs Final (success)
  - Action buttons: View, Edit (conditional), Delete (conditional)
  - Pagination with Bootstrap pagination component
  - Empty state with helpful message

#### dischargereport_detail.html
- **Purpose**: Read-only report view
- **Features**:
  - Card-based layout with sections
  - Status badge in header
  - Conditional edit button
  - Organized medical content in smaller cards
  - Metadata section with timestamps and users
  - Duration calculation between admission/discharge dates

#### dischargereport_confirm_delete.html
- **Purpose**: Delete confirmation dialog
- **Features**: Report summary, clear warning message, cancel option
- **Message**: Explains different rules for drafts vs finals

### Template Features
- **Icons**: Bootstrap Icons throughout for visual consistency
- **Error Handling**: Form errors displayed with proper Bootstrap styling
- **Responsive**: Mobile-friendly layouts with Bootstrap grid system
- **Accessibility**: Proper labels, ARIA attributes, semantic HTML

## Form Validation

### Client-Side Validation
- HTML5 validation for date fields and required inputs
- Bootstrap validation classes for visual feedback

### Server-Side Validation
- Date relationship validation (admission before discharge)
- All required field validation through Django forms
- Portuguese error messages for user feedback

## Admin Interface

### DischargeReportAdmin
- **List Display**: Patient, specialty, dates, draft status, creation time
- **Filters**: Draft status, specialty, admission/discharge dates  
- **Search**: Patient name, specialty, diagnosis content
- **Fieldsets**: Organized sections (Basic, Dates, Specialty, Medical Content, Metadata)
- **Readonly Fields**: Timestamps and user tracking fields

## Database Integration

### Event Integration
- Inherits from `Event` model (multi-table inheritance)
- Automatically sets `event_type = 6` (DISCHARGE_REPORT_EVENT)
- Participates in event timeline and history tracking
- UUID primary keys for security

### Migration
- **0001_initial.py**: Creates DischargeReport table with proper indexes
- **Indexes**: Optimized for common queries (dates, draft status, specialty)

## Testing

### Model Testing
```bash
# Test model functionality
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/dischargereports/tests/test_models.py
```

### View Testing  
```bash
# Test CRUD operations and permissions
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/dischargereports/tests/test_views.py
```

### Form Testing
```bash
# Test form validation
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/dischargereports/tests/test_forms.py
```

## Troubleshooting

### Common Issues

**Permission Errors**
- Verify user has correct profession (doctor/resident for drafts)
- Check 24-hour window for final report editing
- Ensure user is authenticated and can access patient

**Form Validation Errors**
- Check admission date is before discharge date
- Verify all required fields are filled
- Test date format compatibility

**Template Errors**
- Ensure `dischargereports` app is in INSTALLED_APPS
- Check template tag loading: `{% load dischargereport_tags %}`
- Verify Bootstrap CSS/JS is loaded in base template

**Admin Interface Issues**
- Confirm admin registration is working
- Check fieldset configuration for field visibility
- Verify readonly fields are properly set

## Development Notes

### Adding New Fields
1. Add field to `DischargeReport` model
2. Create and run migration: `uv run python manage.py makemigrations dischargereports`
3. Update `DischargeReportForm.Meta.fields` list
4. Add widget configuration in `DischargeReportForm.Meta.widgets`
5. Update templates (create, update, detail) to display new field
6. Add to admin fieldsets if needed
7. Update tests and documentation

### Customizing Permissions
1. Modify `can_edit_discharge_report()` or `can_delete_discharge_report()` functions
2. Update template tags if logic changes
3. Test permission scenarios thoroughly
4. Update error messages in views if needed

### Template Customization
1. Override templates in your hospital's template directory
2. Maintain Bootstrap structure for consistency
3. Test responsive behavior on mobile devices
4. Ensure accessibility standards are maintained

This documentation covers the core functionality implemented in Phases 1 and 2 of the discharge reports system.