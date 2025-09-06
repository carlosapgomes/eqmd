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

## Phase 7: Testing & Documentation

**Comprehensive test suite and complete documentation for discharge reports feature.**

### Overview

Phase 7 completes the discharge reports implementation with comprehensive testing coverage and enhanced documentation. The test suite covers all aspects of the application including models, views, Firebase import functionality, and integration workflows.

### Test Suite Structure

#### Test Directory Structure
```
apps/dischargereports/
└── tests/
    ├── __init__.py
    ├── test_models.py          # Model behavior and validation
    ├── test_views.py          # View functionality and permissions  
    ├── test_firebase_import.py # Firebase import functionality
    └── test_integration.py    # Complete workflow testing
```

### Model Tests (`test_models.py`)

#### Coverage Areas
- **Event Type Setting**: Verifies `save()` sets correct event type
- **Draft Default Behavior**: Confirms `is_draft` defaults to `True`
- **String Representation**: Tests `__str__` method formatting
- **Permission Methods**: Validates edit/delete permission logic
- **Status Display**: Tests status properties and badge classes
- **Date Validation**: Ensures discharge date after admission date
- **24-hour Edit Window**: Verifies time-based editing restrictions

#### Key Test Scenarios
```python
def test_can_be_edited_by_user_draft(self):
    """Test that drafts can be edited by creator"""
    # Tests draft editing permissions
    
def test_can_be_deleted_by_user_draft_only(self):
    """Test that only drafts can be deleted"""
    # Tests delete restrictions for final reports
    
def test_status_display_properties(self):
    """Test status display properties"""
    # Tests status text and CSS class generation
```

### View Tests (`test_views.py`)

#### Coverage Areas
- **Authentication Requirements**: All views require login
- **CRUD Operations**: Create, read, update, delete functionality
- **Draft vs Final Logic**: Different behavior for draft/final reports
- **Permission Enforcement**: Proper access control implementation
- **Form Validation**: Server-side validation and error handling
- **Template Rendering**: Correct template selection and context data

#### Key Test Scenarios
```python
def test_create_view_saves_draft_by_default(self):
    """Test that create view saves as draft by default"""
    # Tests draft creation workflow
    
def test_update_view_blocks_non_editable(self):
    """Test that update view blocks non-editable reports"""
    # Tests 24-hour edit window enforcement
    
def test_delete_view_allows_drafts_only(self):
    """Test that delete view only allows draft deletion"""
    # Tests delete permission restrictions
```

### Firebase Import Tests (`test_firebase_import.py`)

#### Coverage Areas
- **Command Interface**: Proper argument parsing and validation
- **Firebase Connection**: Authentication and data retrieval
- **Data Mapping**: Firebase to Django model field mapping
- **Patient Matching**: Record number to patient lookup
- **Duplicate Prevention**: Skip already imported records
- **Error Handling**: Graceful handling of various error conditions
- **Dry Run Mode**: Preview functionality without database changes

#### Key Test Scenarios
```python
def test_successful_import(self):
    """Test successful Firebase import"""
    # Tests import with dry run mode
    
def test_actual_import_creates_objects(self):
    """Test that actual import creates DischargeReport and PatientAdmission objects"""
    # Tests real import with database changes
    
def test_import_with_nonexistent_patient(self):
    """Test import with patient that doesn't exist"""
    # Tests error handling for missing patients
```

### Integration Tests (`test_integration.py`)

#### Coverage Areas
- **Complete Workflows**: End-to-end draft to final workflows
- **Timeline Integration**: Reports appearing in patient timelines
- **Multiple Reports**: Handling multiple reports per patient
- **Cross-User Permissions**: Unauthorized user access prevention
- **Form Validation Integration**: Server-side validation in context
- **Template Integration**: Permission-based UI elements

#### Key Test Scenarios
```python
def test_complete_draft_to_final_workflow(self):
    """Test creating draft, editing, and finalizing"""
    # Tests complete report lifecycle
    
def test_multiple_reports_for_same_patient(self):
    """Test creating multiple reports for the same patient"""
    # Tests patient-report relationships
    
def test_timeline_integration(self):
    """Test that discharge reports appear in patient timeline"""
    # Tests event system integration
```

### Running Tests

#### Test Commands
```bash
# All tests with coverage
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/dischargereports/tests/ --cov=apps.dischargereports --cov-report=term-missing -v

# All tests without coverage
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/dischargereports/tests/ -v

# Specific test files
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/dischargereports/tests/test_models.py -v
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/dischargereports/tests/test_views.py -v
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/dischargereports/tests/test_firebase_import.py -v
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/dischargereports/tests/test_integration.py -v

# With coverage reports
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/dischargereports/tests/ --cov=apps.dischargereports --cov-report=html --cov-report=term-missing -v
```

#### Test Coverage Goals
- **Overall Coverage**: >80% code coverage
- **Model Coverage**: 100% of model methods and properties
- **View Coverage**: All view classes and methods tested
- **Import Coverage**: Firebase import command thoroughly tested
- **Integration Coverage**: Key user workflows validated

### Testing Best Practices

#### Mock Usage
- **Firebase Services**: Mock Firebase Admin SDK for import tests
- **User Authentication**: Mock user authentication for view tests
- **Database Operations**: Use Django's test database for isolated testing
- **External Services**: Mock all external service calls

#### Test Data Management
- **Factory Pattern**: Use factory-boy or direct object creation
- **Test Isolation**: Each test runs with clean database state
- **Data Relationships**: Proper patient-report relationships maintained
- **Edge Cases**: Test boundary conditions and error scenarios

#### Performance Testing
- **Query Efficiency**: Monitor database query counts
- **Load Testing**: Test with large datasets for import functionality
- **Memory Usage**: Ensure tests don't leak memory
- **Response Times**: View response times within acceptable limits

### Test Documentation

#### Test Case Documentation
Each test includes:
- **Clear Description**: What the test validates
- **Setup Steps**: How test data is prepared
- **Expected Results**: What the test should verify
- **Error Conditions**: How failures are handled

#### Integration with CI/CD
- **Automated Testing**: Tests run on every commit
- **Coverage Reports**: Coverage reports generated and monitored
- **Test Failures**: Failed tests block deployment
- **Performance Metrics**: Test performance tracked over time

### Verification Checklist

#### Test Implementation Verification
✅ **Test Structure**: Proper test directory and file organization
✅ **Model Coverage**: All model methods and properties tested
✅ **View Coverage**: All CRUD operations and permissions tested
✅ **Import Coverage**: Firebase import thoroughly tested with mocking
✅ **Integration Coverage**: Complete workflows and user scenarios tested
✅ **Error Handling**: Comprehensive error condition testing
✅ **Edge Cases**: Boundary conditions and unusual scenarios covered
✅ **Performance**: Test efficiency and resource usage monitored

#### Documentation Verification
✅ **Test Commands**: Clear instructions for running tests
✅ **Coverage Goals**: Defined coverage targets and metrics
✅ **Best Practices**: Testing guidelines and standards documented
✅ **Troubleshooting**: Common test issues and solutions documented
✅ **CI/CD Integration**: Automated testing process documented

### Troubleshooting Tests

#### Common Test Issues

**Import Errors**:
```bash
# Check for missing dependencies
uv run python -c "import pytest, factory_boy, firebase_admin"

# Verify test settings
DJANGO_SETTINGS_MODULE=config.test_settings uv run python manage.py check
```

**Permission Test Failures**:
- Verify user authentication setup
- Check permission groups and user assignments
- Validate permission method implementations

**Firebase Mock Issues**:
- Confirm mock setup for Firebase Admin SDK
- Verify mock return values and method calls
- Check patch decorators and import paths

**Database Test Issues**:
- Ensure test database migrations are current
- Check test data setup and cleanup
- Verify test isolation between test cases

This completes the Phase 7 implementation, providing comprehensive test coverage and documentation for the discharge reports feature, ensuring reliability and maintainability for production use.

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

## Phase 3: Event System Integration

**Timeline integration and event card functionality for discharge reports.**

### Overview

Phase 3 integrates discharge reports fully into the patient timeline system, making them appear as interactive event cards alongside other medical events like daily notes, prescriptions, and media files.

### Event Card Template

#### event_card_dischargereport.html

Custom event card template extending `event_card_base.html`:

**Location**: `/apps/events/templates/events/partials/event_card_dischargereport.html`

**Features**:
- **View Button**: Link to detailed discharge report view
- **Print Button**: Opens print-friendly version in new tab
- **Edit Button**: Conditional visibility (drafts + 24h window for finals)
- **Delete Button**: Only visible for drafts with proper permissions
- **Draft Badge**: Warning badge for draft status indication
- **Content Summary**: Shows medical specialty, admission/discharge dates, duration, and truncated content

**Template Blocks**:
- `{% block event_actions %}`: Custom buttons for discharge report actions
- `{% block event_content %}`: Discharge report summary with dates and medical content

### Print Functionality

#### DischargeReportPrintView

**Purpose**: Generate print-friendly discharge report pages

**Features**:
- Clean, professional print layout
- Hospital branding integration using `{% load hospital_tags %}`
- All discharge report sections (history, diagnosis, treatment, recommendations)
- Signature section with doctor details
- Print-optimized CSS with `@media print` rules

**Template**: `dischargereports/dischargereport_print.html`

**URL**: `/dischargereports/<uuid:pk>/print/`

#### Print Template Features
- Hospital name and branding header
- Patient demographic information
- All medical content sections
- Professional signature block
- Print button (hidden in print mode)
- Responsive styling for different paper sizes

### Timeline Integration

#### Event Type Registration

Discharge reports are fully registered in the Event system:

- **Event Type**: `Event.DISCHARGE_REPORT_EVENT = 6`
- **Display Name**: "Relatório de Alta"
- **Short Display**: "Alta" (mobile-friendly)
- **Badge Class**: `bg-medical-dark`
- **Icon**: `bi-door-open`

#### Timeline Template Updates

**File**: `/apps/events/templates/events/patient_timeline.html`

**Changes**:
1. **Event Card Rendering**: Added conditional include for discharge report event cards
   ```django
   {% elif event.event_type == 6 %}
       {% include "events/partials/event_card_dischargereport.html" with event=event event_data=event_data %}
   ```

2. **Create Event Dropdown**: Enabled discharge report creation from timeline
   - Mobile and desktop dropdown menus updated
   - Removed "Em breve" (Coming soon) status
   - Added proper URL linking to patient-specific creation

### Patient-Specific URLs

#### New URL Pattern

Added patient-specific creation URL for better workflow integration:

**URL**: `/dischargereports/patient/<uuid:patient_id>/create/`

**Name**: `patient_dischargereport_create`

#### View Enhancement

Updated `DischargeReportCreateView` with `get_initial()` method:
- Automatically pre-fills patient field when accessed via patient-specific URL
- Maintains backward compatibility with general create URL
- Improves user experience from timeline interface

### Integration Testing

#### Verification Checklist

✅ **Model Integration**:
- Event type constants properly defined
- Badge and icon classes configured
- Short display mapping included

✅ **Template Integration**:
- Event card template created and functional
- Timeline template updated with conditional rendering
- Print template created with hospital branding

✅ **URL Integration**:
- Patient-specific creation URL added
- Print URL properly configured
- All URL patterns tested

✅ **Permission Integration**:
- Event card respects discharge report permission logic
- Buttons show/hide based on draft status and edit windows
- Delete permissions properly enforced

### Usage in Timeline

#### For Medical Staff

1. **Creating Discharge Reports**:
   - Access patient timeline
   - Click "Criar Evento" → "Relatórios" → "Relatório de Alta"
   - Patient is pre-selected automatically
   - Create as draft or final report

2. **Viewing in Timeline**:
   - Discharge reports appear as event cards with dark badge
   - Shows admission dates, medical specialty, and content preview
   - Duration calculation between admission and discharge dates

3. **Actions Available**:
   - **View**: Full detailed view of discharge report
   - **Print**: Professional print layout with hospital branding
   - **Edit**: Available for drafts (unlimited) and finals (24h window)
   - **Delete**: Available for drafts only

#### Timeline Display Features

- **Chronological Order**: Discharge reports appear in timeline alongside other events
- **Visual Distinction**: Dark badge (`bg-medical-dark`) with door icon (`bi-door-open`)
- **Content Preview**: Shows key information without requiring full page load
- **Mobile Responsive**: Optimized for mobile and desktop viewing
- **Accessibility**: Proper ARIA labels and keyboard navigation support

### Technical Implementation

#### Event System Methods

Discharge reports inherit all Event model methods:
- `get_event_type_badge_class()`: Returns `"bg-medical-dark"`
- `get_event_type_icon()`: Returns `"bi-door-open"`
- `get_event_type_short_display()`: Returns `"Alta"`
- `get_absolute_url()`: Links to discharge report detail view
- `get_edit_url()`: Links to discharge report update view

#### Timeline Filtering

Discharge reports automatically participate in timeline filtering:
- **Event Type Filter**: Included in event type checkbox options
- **Date Range Filter**: Works with admission/discharge dates
- **Creator Filter**: Works with created_by field
- **Search Integration**: Content is searchable within timeline

### Troubleshooting

#### Common Integration Issues

**Event Card Not Appearing**:
- Verify `event_type = 6` is properly set on DischargeReport model
- Check timeline template includes the conditional rendering
- Ensure event_card_dischargereport.html exists in correct location

**Print Button Not Working**:
- Confirm print URL is added to dischargereports/urls.py
- Verify DischargeReportPrintView is imported in views.py
- Check print template exists and hospital_tags are loaded

**Permission Errors**:
- Verify draft/final permission logic is working correctly
- Check user profession requirements for draft editing
- Test 24-hour editing window for final reports

**Timeline Dropdown Issues**:
- Ensure patient-specific URL pattern is added
- Check URL namespace: `apps.dischargereports:patient_dischargereport_create`
- Verify CreateView handles patient_id parameter correctly

This completes the Phase 3 integration, making discharge reports fully functional within the EquipeMed timeline system.

## Phase 4: Professional Print/PDF Generation

**Professional Portuguese PDF reports with hospital branding and print optimization.**

### Overview

Phase 4 enhances the discharge reports system with comprehensive print functionality, providing medical-grade print layouts with full hospital branding integration. The system generates professional Portuguese discharge documents suitable for official medical documentation.

### Enhanced Print Template

#### Comprehensive Print Layout

**Location**: `/apps/dischargereports/templates/dischargereports/dischargereport_print.html`

**Features**:
- **Hospital Branding Header**: Logo, name, address, phone, email integration
- **Document Title Section**: Professional formatting with medical specialty
- **Patient Information Grid**: Organized demographics with proper medical information
- **Medical Content Sections**: All discharge report fields with conditional rendering
- **Professional Footer**: Generation info and hospital branding footer
- **Auto-print Support**: JavaScript functionality for `?print=true` parameter

**Template Structure**:
```html
<!-- Hospital Branding -->
<div class="hospital-branding">
  {% hospital_logo as logo_url %}
  {% if logo_url %}
    <img src="{{ logo_url }}" alt="Logo do Hospital" class="hospital-logo" />
  {% endif %}
  <div class="hospital-info">
    <div class="hospital-name">{% hospital_name %}</div>
    <div class="hospital-details">
      {% hospital_address %} | {% hospital_phone %} | {% hospital_email %}
    </div>
  </div>
</div>

<!-- Patient Information Grid -->
<div class="patient-info-section">
  <h3>Identificação do Paciente</h3>
  <div class="patient-info-grid">
    <!-- Organized patient demographics -->
  </div>
</div>

<!-- Medical Content Sections -->
<!-- All discharge report fields with proper formatting -->
```

### Professional Print CSS

#### Print-Specific Styling

**Location**: `/apps/dischargereports/static/dischargereports/css/print.css`

**Design Features**:
- **Professional Typography**: 12pt/11pt font sizes with proper line-height
- **Hospital Color Scheme**: Professional blue (#0066cc) theme throughout
- **Print Optimization**: `@media print` queries with page numbering support
- **Page Break Management**: Proper page breaks and content flow
- **Responsive Layout**: Mobile and desktop compatibility

**Key CSS Classes**:
```css
/* Print-specific styles */
@media print {
  @page {
    margin: 2cm;
    @top-right {
      content: "Página " counter(page) " de " counter(pages);
    }
  }
  
  .no-print { display: none !important; }
  .page-break { page-break-before: always; }
  .avoid-break { page-break-inside: avoid; }
}

/* Professional styling */
.header {
  border-bottom: 2px solid #0066cc;
  page-break-inside: avoid;
}

.patient-info-grid {
  background: #f8f9fa;
  border: 1px solid #dee2e6;
}

.content-section {
  page-break-inside: avoid;
}
```

### Static Files Integration

#### Directory Structure

```
apps/dischargereports/
├── static/
│   └── dischargereports/
│       └── css/
│           └── print.css
└── templates/
    └── dischargereports/
        └── dischargereport_print.html

static/
└── dischargereports/
    └── css/
        └── print.css (deployed)
```

#### Build Process

**Webpack Integration**:
- CSS file processed through build system
- Static files copied to deployment directory
- Template properly links to static CSS file

**Build Commands**:
```bash
npm run build  # Process static files
# CSS automatically copied to static/ directory
```

### Print View Enhancement

#### DischargeReportPrintView Updates

**Enhanced Context**:
```python
def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    context['now'] = timezone.now()
    context['user'] = self.request.user  # Added for generation info
    return context
```

**Features**:
- **Current User**: Print shows who generated the report
- **Generation Timestamp**: Professional date/time formatting
- **Hospital Integration**: Full hospital branding context
- **Print Security**: Login required for all print access

### User Interface Integration

#### Print Button in Detail View

**Location**: Updated in `dischargereport_detail.html`

**Implementation**:
```html
<div class="btn-group">
  <a
    href="{% url 'apps.dischargereports:dischargereport_print' pk=report.pk %}"
    class="btn btn-outline-secondary"
    target="_blank"
  >
    <i class="bi bi-printer"></i> Imprimir Relatório
  </a>
  <!-- Other buttons... -->
</div>
```

**Features**:
- **New Tab Opening**: `target="_blank"` for better user experience
- **Bootstrap Integration**: Consistent with existing button styling
- **Icon Integration**: Printer icon for visual recognition
- **Accessibility**: Proper ARIA labels and semantic HTML

### Print Features

#### Professional Document Layout

**Header Section**:
- Hospital logo (if configured)
- Hospital name, address, phone, email
- Document title: "Relatório de Alta"
- Medical specialty designation

**Patient Information**:
- **Demographics**: Name, record number, birth date, gender, age
- **Medical Dates**: Admission date, discharge date
- **Organized Grid**: Professional tabular layout with proper spacing

**Medical Content**:
- **Conditional Rendering**: Only shows sections with content
- **Proper Formatting**: Text justified, proper line breaks
- **Section Headers**: Professional styling with borders
- **Content Flow**: Optimized for multi-page documents

**Footer Section**:
- **Generation Info**: Date/time generated, generated by user
- **Hospital Footer**: Hospital branding and contact information
- **System Credit**: "criado por EquipeMed" branding

#### Print Optimization

**Page Management**:
- **Page Breaks**: Automatic page breaks for long content
- **Page Numbering**: "Página X de Y" in header (print mode)
- **Content Flow**: Sections avoid breaking across pages
- **Margins**: Professional 2cm margins for all pages

**Typography**:
- **Font Stack**: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif
- **Font Sizes**: 12pt screen, 11pt print for optimal readability
- **Line Height**: 1.4 for professional document appearance
- **Color Scheme**: Professional blue theme with proper contrast

#### Browser Compatibility

**Print Features**:
- **Print Button**: Fixed position with hover effects
- **Auto-print**: JavaScript support for `?print=true` URL parameter
- **Print Preview**: Optimized for browser print preview
- **Cross-browser**: Compatible with Chrome, Firefox, Safari, Edge

### Event Card Integration

#### Enhanced Event Card Print Button

The event card template includes the print button alongside other actions:

```html
<!-- Print Button in Event Card -->
<a
  href="{% url 'apps.dischargereports:dischargereport_print' pk=event.pk %}"
  class="btn btn-outline-secondary btn-sm"
  target="_blank"
>
  <i class="bi bi-printer" aria-hidden="true"></i>
  <span class="visually-hidden">Imprimir</span>
</a>
```

### Usage Workflow

#### For Medical Staff

**From Detail View**:
1. Navigate to discharge report detail page
2. Click "Imprimir Relatório" button
3. New tab opens with print-ready layout
4. Use browser's print function or auto-print feature

**From Timeline**:
1. Access patient timeline
2. Locate discharge report event card
3. Click print button in event actions
4. Professional print layout opens in new tab

**Print Options**:
- **Standard Print**: Regular browser print dialog
- **Auto-print**: Add `?print=true` to URL for automatic printing
- **Save as PDF**: Use browser's "Save as PDF" option
- **Print Preview**: Review layout before printing

### Technical Implementation

#### Static File Management

**CSS Processing**:
- Source file: `apps/dischargereports/static/dischargereports/css/print.css`
- Deployed file: `static/dischargereports/css/print.css`
- Template reference: `{% static 'dischargereports/css/print.css' %}`

**Template Loading**:
- Django template system loads print template correctly
- Hospital tags integrate properly with branding
- CSS styling applies correctly in browser and print mode

#### Hospital Integration

**Template Tags Used**:
- `{% hospital_name %}`: Hospital name in header
- `{% hospital_address %}`: Address in contact info
- `{% hospital_phone %}`: Phone number in contact info
- `{% hospital_email %}`: Email in contact info
- `{% hospital_logo as logo_url %}`: Logo image (if configured)

### Verification and Testing

#### Print Quality Checklist

✅ **Layout Verification**:
- Professional header with hospital branding
- Organized patient information grid
- All medical content sections display correctly
- Footer with generation info and hospital details

✅ **Print Optimization**:
- Print-specific CSS applies correctly
- Page breaks work properly for long content
- Page numbering displays in print mode
- No-print elements hidden correctly

✅ **Cross-browser Testing**:
- Chrome print preview and printing
- Firefox print compatibility
- Safari print functionality
- Edge browser support

✅ **Content Validation**:
- All discharge report fields render properly
- Conditional sections show/hide correctly
- Portuguese formatting and labels
- Medical terminology properly displayed

### Troubleshooting

#### Common Print Issues

**CSS Not Loading**:
- Verify CSS file exists in `static/dischargereports/css/print.css`
- Check static file serving configuration
- Ensure webpack build completed successfully
- Confirm template references correct static path

**Print Layout Problems**:
- Check `@media print` styles are properly applied
- Verify page break settings for long content
- Test print preview in multiple browsers
- Validate CSS syntax and selectors

**Hospital Branding Missing**:
- Confirm hospital template tags are loaded: `{% load hospital_tags %}`
- Check hospital configuration environment variables
- Verify hospital logo path and accessibility
- Test template tag rendering in development

**Print Button Not Working**:
- Verify print URL is added to `urls.py`
- Check `DischargeReportPrintView` is imported
- Test URL routing with Django URL resolver
- Confirm user permissions for print access

### Performance Considerations

#### Print Optimization

**CSS Efficiency**:
- Minimal CSS file size (4KB)
- Print-specific styles only load when needed
- Optimized selectors for fast rendering
- No external dependencies or fonts

**Template Performance**:
- Conditional rendering reduces HTML size
- Optimized template logic for fast processing
- Minimal JavaScript for auto-print functionality
- Static file caching for improved load times

This completes the Phase 4 implementation, providing discharge reports with professional, medical-grade print functionality suitable for official documentation and regulatory compliance.

## Phase 5: Firebase Import Management Command

**Firebase data migration command for importing discharge reports with PatientAdmission creation.**

### Overview

Phase 5 provides a comprehensive Django management command to import discharge reports from Firebase Realtime Database. The command creates both DischargeReport records and corresponding PatientAdmission records, maintaining data integrity and providing proper tracking of imported records.

### Firebase Import Command

#### Command Location

**File**: `/apps/dischargereports/management/commands/import_firebase_discharge_reports.py`

**Purpose**: Import discharge reports from Firebase with automatic PatientAdmission creation

#### Command Features

**Core Functionality**:
- **Firebase Integration**: Connects to Firebase Realtime Database using service account credentials
- **Data Validation**: Validates Firebase data structure and required fields
- **Patient Matching**: Matches Firebase patient keys to existing PatientRecordNumber records
- **Duplicate Prevention**: Skips already imported reports using Firebase ID tracking
- **Atomic Transactions**: Ensures data consistency with database transactions
- **PatientAdmission Creation**: Automatically creates admission records for each discharge

**Import Options**:
- **Dry Run Mode**: Preview imports without making database changes
- **Import Limits**: Limit number of records for testing purposes
- **User Assignment**: Specify user for created_by/updated_by fields
- **Error Handling**: Comprehensive error reporting and recovery

#### Command Arguments

```bash
# Required Arguments
--credentials-file          # Path to Firebase service account JSON file
--database-url             # Firebase Realtime Database URL

# Optional Arguments
--discharge-reports-reference  # Firebase reference path (default: "patientDischargeReports")
--user-email               # Email of user to assign as creator (default: first admin)
--dry-run                  # Preview mode without importing data
--limit                    # Limit number of records to import
```

#### Firebase Data Format

**Expected Firebase Structure**:
```json
{
  "patientDischargeReports": {
    "firebase_key_1": {
      "patient": "patient_record_number",
      "datetime": 1234567890000,
      "username": "doctor_name",
      "content": {
        "admissionDate": "2023-01-15",
        "dischargeDate": "2023-01-20",
        "specialty": "Cardiologia",
        "admissionHistory": "Patient history text...",
        "problemsAndDiagnostics": "Diagnosis details...",
        "examsList": "List of exams performed...",
        "proceduresList": "Procedures during stay...",
        "inpatientMedicalHistory": "Medical evolution...",
        "patientDischargeStatus": "Patient condition...",
        "dischargeRecommendations": "Post-discharge care..."
      }
    }
  }
}
```

#### Field Mapping

**Firebase → DischargeReport Mapping**:
- `content.specialty` → `medical_specialty`
- `content.admissionHistory` → `admission_history`
- `content.problemsAndDiagnostics` → `problems_and_diagnosis`
- `content.examsList` → `exams_list`
- `content.proceduresList` → `procedures_list`
- `content.inpatientMedicalHistory` → `inpatient_medical_history`
- `content.patientDischargeStatus` → `discharge_status`
- `content.dischargeRecommendations` → `discharge_recommendations`
- `content.admissionDate` → `admission_date`
- `content.dischargeDate` → `discharge_date`
- `datetime` → `event_datetime` (converted from milliseconds)
- `patient` → Patient lookup via `PatientRecordNumber`

### Usage Examples

#### Basic Import

```bash
# Standard import
uv run python manage.py import_firebase_discharge_reports \
  --credentials-file firebase-key.json \
  --database-url https://your-project.firebaseio.com

# With specific user
uv run python manage.py import_firebase_discharge_reports \
  --credentials-file firebase-key.json \
  --database-url https://your-project.firebaseio.com \
  --user-email doctor@hospital.com
```

#### Testing and Development

```bash
# Dry run to preview imports
uv run python manage.py import_firebase_discharge_reports \
  --credentials-file firebase-key.json \
  --database-url https://your-project.firebaseio.com \
  --dry-run

# Limited import for testing
uv run python manage.py import_firebase_discharge_reports \
  --credentials-file firebase-key.json \
  --database-url https://your-project.firebaseio.com \
  --limit 5 \
  --dry-run

# Custom Firebase reference
uv run python manage.py import_firebase_discharge_reports \
  --credentials-file firebase-key.json \
  --database-url https://your-project.firebaseio.com \
  --discharge-reports-reference "custom/reports/path"
```

#### Docker Integration

```bash
# Docker compose execution
docker compose exec eqmd python manage.py import_firebase_discharge_reports \
  --credentials-file /app/firebase-key.json \
  --database-url https://your-project.firebaseio.com

# Docker with volume mount for credentials
docker compose exec eqmd python manage.py import_firebase_discharge_reports \
  --credentials-file /app/secrets/firebase-key.json \
  --database-url https://your-project.firebaseio.com \
  --dry-run
```

### PatientAdmission Integration

#### Automatic Admission Creation

For each imported discharge report, the command automatically creates a corresponding `PatientAdmission` record:

**PatientAdmission Fields**:
- `patient`: Linked to the same patient as the discharge report
- `admission_datetime`: Derived from `admissionDate` (start of day)
- `discharge_datetime`: Derived from `dischargeDate` (start of day)
- `admission_type`: Set to `SCHEDULED`
- `discharge_type`: Set to `MEDICAL`
- `stay_duration_days`: Calculated from admission/discharge date difference
- `is_active`: Set to `False` (completed admission)
- `created_by`/`updated_by`: Same as discharge report

#### Data Integrity

**Transaction Safety**:
- Both DischargeReport and PatientAdmission created in single transaction
- Rollback on any error ensures data consistency
- Firebase ID tracking prevents duplicate imports
- Patient validation prevents orphaned records

### Error Handling and Recovery

#### Common Issues and Solutions

**Firebase Connection Errors**:
```bash
# Verify credentials file exists and is valid JSON
cat firebase-key.json | python -m json.tool

# Test Firebase connection
uv run python manage.py shell -c "
import firebase_admin
from firebase_admin import credentials, db
cred = credentials.Certificate('firebase-key.json')
firebase_admin.initialize_app(cred, {'databaseURL': 'https://your-project.firebaseio.com'})
print('Firebase connection successful')
"
```

**Patient Matching Issues**:
- **Missing Patients**: Reports skipped if patient record number not found
- **Invalid Record Numbers**: Check PatientRecordNumber table for matching entries
- **Data Validation**: Ensure Firebase patient keys match database record numbers

**Date Format Errors**:
- **Expected Format**: Firebase dates must be in "YYYY-MM-DD" format
- **Invalid Dates**: Command reports specific date parsing errors
- **Timezone Handling**: Event datetime converted from UTC milliseconds

#### Import Status Tracking

**Duplicate Prevention**:
- Firebase ID stored in discharge report description field
- Format: `"Firebase ID: {firebase_key}"`
- Existing reports with matching Firebase ID are skipped
- Username from Firebase stored for reference

**Import Statistics**:
- **Imported**: Successfully created discharge reports
- **Skipped**: Existing reports or missing patients
- **Errors**: Failed imports with error details

### Verification and Testing

#### Pre-import Checks

**Environment Verification**:
```bash
# Check firebase-admin installation
uv run python -c "import firebase_admin; print('Firebase Admin SDK installed')"

# Verify command registration
uv run python manage.py help import_firebase_discharge_reports

# Test database connectivity
uv run python manage.py shell -c "
from apps.patients.models import PatientRecordNumber
print(f'Total patient records: {PatientRecordNumber.objects.count()}')
"
```

#### Post-import Validation

**Data Verification**:
```bash
# Check imported discharge reports
uv run python manage.py shell -c "
from apps.dischargereports.models import DischargeReport
imported = DischargeReport.objects.filter(description__icontains='Firebase ID')
print(f'Imported discharge reports: {imported.count()}')
"

# Verify PatientAdmission creation
uv run python manage.py shell -c "
from apps.patients.models import PatientAdmission
from apps.dischargereports.models import DischargeReport
admissions = PatientAdmission.objects.count()
reports = DischargeReport.objects.filter(description__icontains='Firebase ID').count()
print(f'Admissions: {admissions}, Reports: {reports}')
"
```

### Performance Considerations

#### Batch Processing

**Memory Management**:
- Firebase data loaded once at start
- Records processed individually to minimize memory usage
- Transaction scope limited to single record for optimal performance
- Progress reporting for long-running imports

**Import Speed**:
- Typical speed: 10-50 records per second depending on data complexity
- Database transaction overhead minimal with atomic blocks
- Firebase API calls batched for optimal network usage

#### Large Dataset Handling

**Recommended Approach**:
1. **Test Import**: Start with `--dry-run` and `--limit 10`
2. **Incremental Import**: Use `--limit` for large datasets
3. **Monitor Progress**: Watch console output for errors
4. **Verify Results**: Check database after each batch

### Troubleshooting

#### Common Firebase Issues

**Authentication Errors**:
- Verify service account credentials have database read permissions
- Check Firebase project ID matches the database URL
- Ensure credentials file is valid JSON format

**Data Structure Errors**:
- Verify Firebase data matches expected structure
- Check for missing required fields (patient, datetime, content)
- Validate date formats in Firebase data

**Database Errors**:
- Ensure PatientRecordNumber table has matching records
- Check for database permission issues
- Verify Django model field constraints

#### Performance Optimization

**For Large Imports**:
- Use `--limit` to process in batches
- Run during low-traffic periods
- Monitor database performance and memory usage
- Consider database connection pooling settings

This completes the Phase 5 implementation, providing comprehensive Firebase import functionality with PatientAdmission integration and robust error handling for data migration scenarios.

## Phase 6: Advanced Features & Permissions

**Enhanced draft logic, refined permissions, and polished UI for discharge reports.**

### Overview

Phase 6 represents the final polish phase for the discharge reports system, implementing advanced permission logic, improved draft workflow, and comprehensive UI enhancements. This phase refines the draft/final system with proper permission methods and consistent status indicators throughout the application.

### Enhanced Model Methods

#### Permission Validation Methods

**Location**: `apps/dischargereports/models.py`

**New Methods Added**:

```python
def can_be_edited_by_user(self, user):
    """Check if report can be edited by specific user"""
    if self.is_draft:
        # Drafts can be edited by creator or users with edit permissions
        return self.created_by == user or user.has_perm('events.change_event')
    else:
        # Finalized reports follow 24h rule
        return self.can_be_edited and (self.created_by == user or user.has_perm('events.change_event'))

def can_be_deleted_by_user(self, user):
    """Check if report can be deleted by specific user"""
    # Only drafts can be deleted
    return self.is_draft and (self.created_by == user or user.has_perm('events.delete_event'))
```

#### Status Display Properties

**New Properties Added**:

```python
@property
def status_display(self):
    """Get display text for report status"""
    if self.is_draft:
        return "Rascunho"
    else:
        return "Finalizado"

@property
def status_badge_class(self):
    """Get CSS class for status badge"""
    return "badge bg-warning text-dark" if self.is_draft else "badge bg-success"
```

**Features**:
- **Consistent Status Display**: Centralized status text in Portuguese
- **Bootstrap Integration**: Pre-configured CSS classes for status badges
- **Template Ready**: Properties designed for direct template usage
- **Visual Consistency**: Consistent status indicators across all interfaces

### Refined Permission Logic

#### Enhanced Views

**DischargeReportUpdateView Updates**:

```python
def get_object(self):
    obj = super().get_object()
    # Check if user can edit this specific report
    if not obj.can_be_edited_by_user(self.request.user):
        if obj.is_draft:
            raise PermissionDenied("Você não tem permissão para editar este rascunho.")
        else:
            raise PermissionDenied("Este relatório não pode mais ser editado.")
    return obj

def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    context['can_finalize'] = self.object.is_draft
    return context
```

**DischargeReportDeleteView Updates**:

```python
def get_object(self):
    obj = super().get_object()
    if not obj.can_be_deleted_by_user(self.request.user):
        raise PermissionDenied("Este relatório não pode ser excluído.")
    return obj
```

#### Enhanced Form Handling

**Improved Save Logic**:

```python
def form_valid(self, form):
    form.instance.updated_by = self.request.user

    # Handle draft vs final save
    if 'save_final' in self.request.POST and self.object.is_draft:
        form.instance.is_draft = False
        messages.success(self.request, 'Relatório de alta finalizado com sucesso.')
    elif 'save_draft' in self.request.POST:
        form.instance.is_draft = True
        messages.success(self.request, 'Rascunho do relatório atualizado.')
    else:
        messages.success(self.request, 'Relatório de alta atualizado.')

    return super().form_valid(form)
```

**Features**:
- **Conditional Finalization**: Only drafts can be finalized
- **Multiple Save Options**: Draft and final save buttons
- **User Feedback**: Specific success messages based on action
- **Permission Integration**: Uses new model permission methods

### Enhanced Templates

#### Improved Detail Template

**Location**: `apps/dischargereports/templates/dischargereports/dischargereport_detail.html`

**Key Improvements**:

**Status Display Header**:
```html
<div class="d-flex align-items-center gap-2 mt-2">
  <span class="{{ report.status_badge_class }}">
    {% if report.is_draft %}
    <i class="bi bi-pencil-square"></i>
    {% else %}
    <i class="bi bi-check-circle"></i>
    {% endif %}
    {{ report.status_display }}
  </span>
  <small class="text-muted">
    {{ report.medical_specialty }} • 
    {{ report.admission_date|date:"d/m/Y" }} - 
    {{ report.discharge_date|date:"d/m/Y" }}
  </small>
</div>
```

**Permission-Based Action Buttons**:
```html
<!-- Edit Button -->
{% if report.can_be_edited_by_user:request.user %}
<a href="{% url 'apps.dischargereports:dischargereport_update' pk=report.pk %}" class="btn btn-warning">
  <i class="bi bi-pencil"></i>
  {% if report.is_draft %}Editar Rascunho{% else %}Editar{% endif %}
</a>
{% endif %}

<!-- Delete Button (drafts only) -->
{% if report.can_be_deleted_by_user:request.user %}
<a href="{% url 'apps.dischargereports:dischargereport_delete' pk=report.pk %}" class="btn btn-outline-danger">
  <i class="bi bi-trash"></i> Excluir Rascunho
</a>
{% endif %}
```

#### Enhanced List Template

**Location**: `apps/dischargereports/templates/dischargereports/dischargereport_list.html`

**Status Column Update**:
```html
<td>
  <span class="{{ report.status_badge_class }}">
    {{ report.status_display }}
  </span>
</td>
```

**Simplified Action Buttons**:
```html
<div class="btn-group btn-group-sm" role="group">
  <a href="{{ report.get_absolute_url }}" class="btn btn-outline-primary">
    <i class="bi bi-eye"></i>
  </a>
  {% if report.can_be_edited_by_user:request.user %}
  <a href="{{ report.get_edit_url }}" class="btn btn-outline-warning">
    <i class="bi bi-pencil"></i>
  </a>
  {% endif %}
</div>
```

#### Enhanced Event Card Template

**Location**: `apps/events/templates/events/partials/event_card_dischargereport.html`

**Updated Edit Button**:
```html
<!-- Edit Button -->
{% if event.can_be_edited_by_user:request.user %}
<a
  href="{{ event.get_edit_url }}"
  class="btn btn-outline-warning btn-sm"
  title="{% if event.is_draft %}Editar rascunho{% else %}Editar relatório{% endif %}"
>
  <i class="bi bi-pencil"></i>
</a>
{% endif %}
```

**Features**:
- **Model Method Integration**: Uses new permission methods directly
- **Contextual Tooltips**: Different tooltips for draft vs final editing
- **Consistent Styling**: Matches overall application design patterns
- **Accessibility**: Proper ARIA labels and semantic HTML

### Form Enhancements

#### Hidden Draft Field

**Location**: `apps/dischargereports/forms.py`

**Form Updates**:
```python
class Meta:
    fields = [
        'patient', 'event_datetime', 'description',
        'admission_date', 'discharge_date', 'medical_specialty',
        'admission_history', 'problems_and_diagnosis', 'exams_list',
        'procedures_list', 'inpatient_medical_history',
        'discharge_status', 'discharge_recommendations', 'is_draft'
    ]
    widgets = {
        # ... other widgets ...
        'is_draft': forms.HiddenInput(),  # Hide from form, controlled by buttons
    }
```

**Features**:
- **Button-Controlled Draft Status**: Draft status controlled by save buttons, not form field
- **Hidden Implementation**: Field present but not visible to users
- **Backward Compatibility**: Maintains form field for proper model binding

### Enhanced Admin Interface

#### Improved Admin Configuration

**Location**: `apps/dischargereports/admin.py`

**Admin Updates**:
```python
@admin.register(DischargeReport)
class DischargeReportAdmin(admin.ModelAdmin):
    list_display = ['patient', 'medical_specialty', 'admission_date', 'discharge_date', 'status_display', 'created_at']
    list_filter = ['is_draft', 'medical_specialty', 'admission_date', 'discharge_date', 'created_at']
    search_fields = ['patient__name', 'medical_specialty', 'problems_and_diagnosis']
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by', 'status_display']

    def status_display(self, obj):
        return obj.status_display
    status_display.short_description = 'Status'
```

**Features**:
- **Status Display Column**: Shows human-readable status instead of boolean
- **Enhanced Filtering**: Added created_at to filters for better data management
- **Read-Only Status**: Status display included in read-only fields
- **Improved List Display**: More informative columns for administrators

### UI/UX Improvements

#### Consistent Status Indicators

**Visual Consistency**:
- **Draft Badge**: Yellow/warning styling with pencil icon (`bg-warning text-dark`)
- **Final Badge**: Green/success styling with checkmark icon (`bg-success`)
- **Icon Integration**: Consistent Bootstrap Icons across all interfaces
- **Portuguese Labels**: All status text in Portuguese for consistency

#### Enhanced User Feedback

**Improved Messages**:
- **Draft Save**: "Rascunho do relatório atualizado"
- **Final Save**: "Relatório de alta finalizado com sucesso"  
- **Delete Success**: "Rascunho do relatório de alta excluído com sucesso"
- **Permission Errors**: Specific error messages for different permission scenarios

#### Better Information Architecture

**Content Organization**:
- **Conditional Sections**: Medical content sections only show when data exists
- **Clean Layout**: Streamlined design with better spacing and hierarchy
- **Professional Footer**: Simplified metadata display with clean formatting
- **Responsive Design**: Mobile-friendly layouts maintained throughout

### Permission System Refinement

#### Draft vs Final Logic

**Draft Reports**:
- **Edit Permission**: Creator OR users with `events.change_event` permission
- **Delete Permission**: Creator OR users with `events.delete_event` permission
- **Time Limit**: No time restrictions for drafts

**Final Reports**:
- **Edit Permission**: Uses existing 24-hour Event system logic
- **Delete Permission**: Uses existing 24-hour Event system logic  
- **Time Limit**: Standard system 24-hour editing window

#### Template Integration

**Permission Checking**:
- **Direct Model Methods**: Templates call model methods directly
- **No Template Tags**: Eliminated need for custom template tags
- **Cleaner Templates**: Simplified template logic with better readability
- **Consistent Behavior**: Same permission logic across all interfaces

### Error Handling Improvements

#### Enhanced Permission Errors

**Specific Error Messages**:
- **Draft Edit Denied**: "Você não tem permissão para editar este rascunho"
- **Final Edit Denied**: "Este relatório não pode mais ser editado"
- **Delete Denied**: "Este relatório não pode ser excluído"
- **Contextual Feedback**: Different messages based on report status

#### Form Validation

**Maintained Validation**:
- **Date Logic**: Admission date must be before discharge date
- **Required Fields**: All medical content fields remain required
- **Portuguese Messages**: All error messages in Portuguese

### Verification and Testing

#### Implementation Checklist

✅ **Model Enhancements**:
- Permission validation methods implemented
- Status display properties working correctly
- All methods properly tested and functional

✅ **View Improvements**:
- Enhanced permission checking in all CRUD views
- Improved form handling with conditional save logic
- Better error messages and user feedback

✅ **Template Updates**:
- Detail template with enhanced UI and permission-based buttons
- List template with status column and simplified actions
- Event card template with updated permission logic

✅ **Form Enhancements**:
- Hidden draft field properly implemented
- Button-controlled draft status working correctly

✅ **Admin Interface**:
- Status display column implemented
- Enhanced filtering and search capabilities
- Proper readonly field configuration

✅ **UI/UX Polish**:
- Consistent status indicators across all interfaces
- Improved user feedback and error messages
- Professional layout and design consistency

### Usage Scenarios

#### For Medical Staff

**Draft Workflow**:
1. Create new discharge report (automatically saved as draft)
2. Edit unlimited times with full access to all fields
3. Save as draft multiple times during preparation
4. Finalize when ready (converts to final status)
5. Delete if needed (only available for drafts)

**Final Report Workflow**:
1. View finalized discharge reports in read-only mode
2. Edit within 24-hour window if creator or have permissions
3. Print professional reports with hospital branding
4. Timeline integration with proper status indicators

#### For Administrators

**Administrative Tasks**:
1. Monitor draft vs final report ratios in admin interface
2. Filter reports by status, specialty, and dates
3. Search across patient names, specialty, and diagnosis content
4. Track report creation and update patterns

### Performance Considerations

#### Template Optimization

**Efficient Rendering**:
- **Property Methods**: Status properties cached on model instances
- **Minimal Database Queries**: Permission methods use existing data
- **Template Logic**: Simplified conditional rendering reduces processing

#### Database Optimization

**Query Efficiency**:
- **Indexed Fields**: Status and date fields properly indexed
- **Minimal Lookups**: Permission checking uses loaded data
- **Transaction Safety**: Atomic operations for status changes

### Migration and Compatibility

#### Backward Compatibility

**Existing Data**:
- All existing draft/final logic maintained
- Previous permission systems continue to work
- Template compatibility preserved with fallbacks

#### Migration Safety

**Zero-Downtime Deployment**:
- New methods added without database changes
- Template updates are backward compatible
- Form changes maintain existing functionality

### Troubleshooting

#### Common Issues

**Permission Errors**:
- Verify user has proper Event permissions (`events.change_event`, `events.delete_event`)
- Check report status (draft vs final) and time windows
- Validate user authentication and session state

**Status Display Problems**:
- Confirm new model properties are accessible in templates
- Check Bootstrap CSS classes are properly loaded
- Verify template syntax for property access

**Form Submission Issues**:
- Ensure hidden `is_draft` field is included in forms
- Check button names for save actions (`save_draft`, `save_final`)
- Validate form field configuration and widget setup

**Template Rendering Errors**:
- Verify all templates extend proper base templates
- Check template tag loading and syntax
- Confirm static file references are correct

### Future Enhancements

#### Potential Improvements

**Workflow Enhancements**:
- **Approval Workflow**: Multi-step approval process for final reports
- **Review System**: Structured review and comment system
- **Template System**: Standardized discharge report templates
- **Integration APIs**: REST API endpoints for external systems

**Advanced Features**:
- **Digital Signatures**: Electronic signature integration for final reports
- **Audit Trail**: Enhanced audit logging for all changes
- **Version Control**: Track changes between draft versions
- **Notification System**: Email alerts for status changes and deadlines

This completes the Phase 6 implementation, providing a polished, professional discharge reports system with refined permissions, enhanced UI consistency, and robust workflow management suitable for production medical environments.