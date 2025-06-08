# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Essential Commands

### Development Server
```bash
python manage.py runserver
```

### Database Management
```bash
# Run migrations
python manage.py migrate

# Create migrations
python manage.py makemigrations

# Create superuser
python manage.py createsuperuser
```

### Testing
```bash
# Run all tests with coverage
pytest

# Run specific app tests
pytest apps/accounts/tests/
pytest apps/core/tests/
pytest apps/patients/tests/
pytest apps/hospitals/tests/
pytest apps/events/tests/

# Run single test file
pytest apps/accounts/tests/test_models.py

# Run tests without coverage
pytest --no-cov

# Run Django-specific tests (alternative method - recommended for patients app)
python manage.py test apps.patients.tests.test_tags
python manage.py test apps.patients.tests.test_integration
python manage.py test apps.patients.tests.test_models
python manage.py test apps.patients.tests.test_views

# Run events app tests (recommended due to django-model-utils dependency)
python manage.py test apps.events.tests

# Run comprehensive patients app test suite
python manage.py test apps.patients.tests.test_integration apps.patients.tests.test_models apps.patients.tests.test_views apps.patients.tests.test_tags

# Run integration tests for dashboard features
python manage.py test apps.patients.tests.test_integration

# Run permission system tests
python manage.py test apps.core.tests.test_permissions.test_utils
python manage.py test apps.core.tests.test_permissions.test_decorators
python manage.py test apps.core.tests.test_permissions

# Run hospital context middleware tests
python manage.py test apps.hospitals.tests.test_middleware
python manage.py test apps.hospitals.tests.test_hospital_selection_view
```

### Frontend Assets
```bash
# Install dependencies
npm install

# Build assets for development
npm run build

# Watch for changes (if available)
npm run dev
```

### Python Environment
```bash
# Install dependencies
uv install

# Add new dependency
uv add package-name

# Add development dependency
uv add --dev package-name
```

### Sample Data Creation
```bash
# Create sample allowed tags for patients
python manage.py create_sample_tags
```

## Project Architecture

**EquipeMed** is a Django 5-based medical team collaboration platform for tracking patients across multiple hospitals.

### App Structure
- **apps/core**: Main application with landing page, dashboard, and permission system
- **apps/accounts**: User management with custom user model and profiles
- **apps/hospitals**: Hospital and ward management with CRUD operations
- **apps/patients**: Patient management with tagging system and hospital records
- **apps/events**: Base event system for medical records and activities
- **config/**: Django project configuration directory
- **assets/**: Webpack-managed frontend assets (SCSS, JS)
- **static/**: Compiled static files

### Key Models

#### Accounts App
- **EqmdCustomUser**: Custom user model with medical profession fields (Medical Doctor, Resident, Nurse, Physiotherapist, Student)
- **UserProfile**: Separate profile model with UUID-based public IDs for security

#### Hospitals App
- **Hospital**: Hospital management model with address, contact info, and tracking fields
- **Ward**: Ward management model with hospital relationship, capacity tracking, and occupancy calculations

#### Patients App
- **Patient**: Patient model with personal info, medical status, and hospital assignment
- **PatientHospitalRecord**: Junction model for patient-hospital relationships with record numbers and dates
- **AllowedTag**: Predefined tags that can be assigned to patients (admin-managed)
- **Tag**: Tag instances that link patients to allowed tags with optional notes

#### Events App
- **Event**: Base model for all medical record events with inheritance support
  - Event types: History/Physical, Daily Notes, Simple Notes, Photos, Exam Results, Exam Requests, Discharge Reports, Prescriptions, Reports, Photo Series
  - UUID primary keys for security and scalability
  - Audit fields with created/updated by tracking
  - Custom permissions for 24-hour edit/delete windows
  - django-model-utils InheritanceManager for extensibility

### Authentication
- Uses django-allauth for email-based authentication
- Custom user model at `accounts.EqmdCustomUser`
- Profile URLs use UUIDs instead of primary keys

### Frontend
- Bootstrap 5.3 with Bootstrap Icons
- Webpack build pipeline compiling SASS/SCSS
- Portuguese (pt-br) localization
- Crispy Forms with Bootstrap 5 styling for form layouts

### Testing
- pytest with django integration (use Django test runner for patients and events apps due to settings configuration)
- Coverage reporting (HTML and terminal)
- factory-boy for test data generation
- Uses `config.test_settings` for test configuration
- Comprehensive integration tests for dashboard widgets and template tags
- Context processor testing with permission validation
- Complete patient workflow testing including hospital transfers and discharge
- Permission-based testing for different user roles
- Events app: Full test coverage for models, admin, forms, views, and templates

### Security Notes
- Environment variables for sensitive configuration
- UUID-based public profile identifiers for patients and records
- CSRF protection enabled
- Debug mode controlled via environment
- Permission-based access control for CRUD operations
- Role-based user groups: Patient Managers (full permissions) and Patient Viewers (read-only)
- Advanced permission framework with hospital context and time-based restrictions

## Patients App Features

### Patient Management
- **Full CRUD Operations**: Create, read, update, and delete patients
- **Advanced Search**: Search patients by name, ID number, fiscal number, or health card number
- **Personal Information**: Complete patient demographics and contact details
- **Medical Status Tracking**: Outpatient, inpatient, emergency, and discharged status options
- **Hospital Assignment**: Link patients to current hospitals with bed information
- **Permission-based Access**: Role-based permissions for all patient operations

### Hospital Records Management
- **Patient-Hospital Relationships**: Track patient records across multiple hospitals
- **Record Numbers**: Unique hospital record numbers for each patient-hospital relationship
- **Admission Tracking**: First admission, last admission, and discharge date tracking
- **CRUD Operations**: Full management of hospital records with proper permissions
- **Audit Trail**: Created/updated by tracking for all records

### Patient Tagging System

#### Overview
The patients app includes a comprehensive tagging system that allows administrators to define allowed tags and users to assign them to patients.

#### Tag Models
- **AllowedTag**: Administrator-defined tags with name, description, color (hex), and active status
- **Tag**: Tag instances assigned to patients, linking to AllowedTag with optional notes
- **Patient-Tag Relationship**: Many-to-many relationship allowing multiple tags per patient

#### Tag Management Features
- **Web-based Tag Administration**: Full CRUD operations for AllowedTag management via web interface
- **Color-coded System**: Custom hex color support for visual tag identification
- **Active/Inactive Status**: Toggle tag availability without deletion
- **Permission-based Access**: Role-based permissions for tag management operations
- **Pagination Support**: Efficient handling of large tag collections

#### Tag Features
- **Color-coded badges**: Tags display with custom hex colors in list and detail views
- **Dual Management**: AllowedTag creation/editing through both Django admin and web interface
- **Form integration**: Tag selection via checkbox interface in patient forms
- **Template display**: Tags shown as colored badges in patient list and detail templates
- **Responsive Design**: Bootstrap 5 styled interface with proper mobile support

#### Tag Usage Workflows
1. **Admin/Staff Workflow**: Create AllowedTag entries via web interface or Django admin
2. **User Assignment**: Select from active allowed tags when creating/editing patients
3. **Automatic Linking**: Tags are automatically created and assigned to patients upon form submission
4. **Visual Display**: Tags display throughout the application with their defined colors
5. **Management**: Update, deactivate, or delete tags as needed with proper permission checks

#### Sample Tags
The system includes a management command to create sample tags:
- High Priority (Red)
- Follow Up (Yellow)
- VIP (Purple)
- Diabetic (Orange)
- Cardiac (Dark Red)
- Elderly (Gray)
- Pediatric (Teal)

### URL Structure
The patients app uses a well-organized URL structure:
- `/patients/` - Patient list with search and pagination
- `/patients/create/` - Create new patient
- `/patients/<uuid:pk>/` - Patient detail view
- `/patients/<uuid:pk>/update/` - Edit patient
- `/patients/<uuid:pk>/delete/` - Delete patient confirmation
- `/patients/<uuid:patient_id>/records/create/` - Create hospital record for specific patient
- `/patients/records/<uuid:pk>/update/` - Edit hospital record
- `/patients/records/<uuid:pk>/delete/` - Delete hospital record
- `/patients/tags/` - Tag management list
- `/patients/tags/create/` - Create new tag
- `/patients/tags/<int:pk>/update/` - Edit tag
- `/patients/tags/<int:pk>/delete/` - Delete tag confirmation

### Forms and Validation
- **Crispy Forms Integration**: Bootstrap 5 styled forms with proper layout
- **Field Validation**: Comprehensive validation for all patient and tag fields
- **Date Widgets**: HTML5 date inputs for birthday and admission dates
- **Color Picker**: HTML5 color input for tag color selection
- **Multi-select Tags**: Checkbox interface for tag assignment with visual feedback

### Dashboard Integration and Template System

#### Dashboard Widgets
The patients app provides comprehensive dashboard integration with reusable widgets:

- **Patient Statistics Widget**: Real-time metrics showing total patients, inpatients, outpatients, and hospital count
- **Recent Patients Widget**: Dynamic list of recently added patients with quick action buttons
- **Permission-aware Display**: All widgets respect user permissions and gracefully handle missing permissions
- **Bootstrap 5 Styling**: Fully responsive widgets using Bootstrap card components

#### Template Tags and Filters
Custom template tags for consistent patient data display:

- **`patient_status_badge`**: Filter that renders color-coded Bootstrap badges for patient status
  - Usage: `{{ patient.status|patient_status_badge }}`
  - Colors: Inpatient (green), Outpatient (blue), Emergency (yellow), Discharged (gray), Transferred (blue)
- **`patient_tags`**: Inclusion tag for rendering patient tags with proper styling
  - Usage: `{% patient_tags patient %}`
  - Displays tags as colored badges with Bootstrap Icons

#### Context Processors
Global context data available in all templates:

- **`patient_stats`**: Provides patient statistics (total, inpatients, outpatients, hospital count)
- **`recent_patients`**: Supplies recent patients data for dashboard widgets
- **Permission-based**: Only loads data for authenticated users with proper permissions
- **Error-safe**: Gracefully handles database connection issues during development

#### Sidebar Navigation Integration
Dynamic navigation system with conditional rendering:

- **Permission-based Menu Items**: Navigation links only appear for users with appropriate permissions
- **Dynamic URL Generation**: Uses Django URL reversing for proper link generation
- **Fallback Support**: Provides static navigation when patients app is not available
- **Mobile Support**: Includes both desktop sidebar and mobile offcanvas navigation

#### Widget Template Structure
Organized template hierarchy for maintainability:

```
apps/patients/templates/patients/
├── widgets/
│   ├── patient_stats.html       # Statistics cards widget
│   └── recent_patients.html     # Recent patients table widget
├── includes/
│   └── sidebar_items.html       # Navigation menu items
└── tags/
    └── patient_tags.html        # Patient tags display template
```

#### Dashboard Template Integration
The core dashboard template includes conditional patient widgets:

```django
<!-- Patient Statistics Row -->
{% if 'apps.patients' in INSTALLED_APPS %}
{% include 'patients/widgets/patient_stats.html' %}
{% endif %}

<!-- Recent Patients Widget -->
{% if 'apps.patients' in INSTALLED_APPS %}
  <div class="col-lg-6">
    {% include 'patients/widgets/recent_patients.html' %}
  </div>
{% endif %}
```

#### Testing Coverage
Comprehensive test suite for dashboard integration:

- **Context Processor Tests**: Verify data accuracy and permission handling
- **Template Tag Tests**: Ensure proper rendering and error handling
- **Integration Tests**: End-to-end testing of dashboard widget functionality including:
  - Complete patient lifecycle workflow (creation → admission → transfer → discharge)
  - Patient-hospital relationship integrity
  - Tag assignment and display with dynamic colors
  - Dashboard widget rendering and data accuracy
- **Permission Tests**: Validate access control for all dashboard features
- **User Role Testing**: Tests for Patient Managers vs Patient Viewers permissions

#### Performance Considerations
Optimized for production use:

- **Efficient Queries**: Context processors use optimized database queries
- **Caching Ready**: Structure supports Redis/Memcached integration
- **Lazy Loading**: Widgets can be enhanced with AJAX for dynamic updates
- **Mobile Optimized**: Responsive design with proper touch interactions

## Permission System

### User Groups
The system includes two pre-configured user groups for patient management:

#### Patient Managers
- **Full CRUD permissions** for all patient-related models:
  - Patient: add, change, delete, view
  - PatientHospitalRecord: add, change, delete, view
  - AllowedTag: add, change, delete, view
  - Tag: add, change, delete, view
- **Total permissions**: 16

#### Patient Viewers
- **Read-only permissions** for all patient-related models:
  - Patient: view only
  - PatientHospitalRecord: view only
  - AllowedTag: view only
  - Tag: view only
- **Total permissions**: 4

### Group Assignment
Groups are automatically created via Django migration `patients.0006_add_patient_groups` and can be assigned to users through Django admin or programmatically.

## Core Permission Framework

### Overview
EquipeMed implements a comprehensive permission framework that provides role-based access control, hospital context management, and time-based restrictions for medical record operations.

### Permission System Architecture
The permission system is located in `apps/core/permissions/` and consists of:

#### Module Structure
```
apps/core/permissions/
├── __init__.py          # Public API exports
├── constants.py         # Permission constants and profession types
├── utils.py            # Core permission checking functions
├── decorators.py       # View-level permission decorators
├── cache.py            # Permission caching utilities
├── queries.py          # Query optimization utilities
└── backends.py         # Custom permission backend
```

#### Permission Constants (`constants.py`)
- **Profession Types**: Maps to `EqmdCustomUser.profession_type` integer values
  - `MEDICAL_DOCTOR` (0): Full permissions
  - `RESIDENT` (1): Full access to current hospital patients
  - `NURSE` (2): Limited patient status changes, full current hospital access
  - `PHYSIOTHERAPIST` (3): Full access to current hospital patients
  - `STUDENT` (4): Limited to outpatients in current hospital
- **Patient Status Types**: `INPATIENT`, `OUTPATIENT`, `EMERGENCY`, `DISCHARGED`, `TRANSFERRED`
- **Time Limits**: Events can be edited for 24 hours after creation

#### Core Permission Functions (`utils.py`)

##### `can_access_patient(user, patient)`
Hospital-based patient access control:
- Doctors, nurses, physiotherapists, and residents: Full access to patients in their current hospital
- Students: Limited to outpatients in their current hospital
- No access if user lacks hospital context or patient is in different hospital

##### `can_edit_event(user, event)`
Time-limited event editing permissions:
- Only event creators can edit their events
- Editing restricted to 24 hours after event creation
- Supports audit trail for medical record integrity

##### `can_change_patient_status(user, patient, new_status)`
Role-based patient status management:
- **Doctors**: Can change any patient status (including discharge)
- **Nurses/Physiotherapists/Residents**: Limited status changes (cannot discharge patients)
- **Students**: Cannot change patient status
- Special rule: Nurses can admit emergency patients to inpatient status

##### `is_doctor(user)`
Simple role verification for doctor-only operations

##### `has_hospital_context(user)`
Validates that user has selected a current hospital context

#### Permission Decorators (`decorators.py`)

##### `@patient_access_required`
View decorator for patient-specific operations:
- Extracts `patient_id` from URL parameters
- Validates user access to the specified patient
- Returns 403 Forbidden for unauthorized access

##### `@doctor_required`
Restricts view access to doctors only:
- Simple role-based restriction
- Returns 403 Forbidden for non-doctors

##### `@can_edit_event_required`
Event editing permission decorator:
- Extracts `event_id` from URL parameters
- Validates user can edit the specified event (creator + time limit)
- Returns 403 Forbidden for unauthorized edits

##### `@hospital_context_required`
Ensures user has hospital context:
- Validates user has selected a current hospital
- Required for hospital-specific operations

### Testing Framework
Comprehensive test suite in `apps/core/tests/test_permissions/`:

#### Test Coverage
- **16 Total Tests**: All passing with complete functionality coverage
- **Utils Tests** (`test_utils.py`): 10 tests covering all permission functions
- **Decorator Tests** (`test_decorators.py`): 6 tests covering all view decorators
- **Mock Integration**: Uses mock objects for Patient and Event models
- **User Model Integration**: Proper integration with `EqmdCustomUser` profession types

#### Test Commands
```bash
# Run all permission tests
python manage.py test apps.core.tests.test_permissions

# Run specific test modules
python manage.py test apps.core.tests.test_permissions.test_utils
python manage.py test apps.core.tests.test_permissions.test_decorators
```

### Integration Points

#### URL Integration
Permission test interface available at:
- `/test/permissions/` - Permission system test dashboard
- `/test/doctor-only/` - Doctor-only view test
- `/test/hospital-context/` - Hospital context requirement test
- `/test/patient-access/<uuid:patient_id>/` - Patient access test
- `/test/event-edit/<uuid:event_id>/` - Event editing test
- `/test/patient-data-change/<uuid:patient_id>/` - Patient personal data change test
- `/test/event-delete/<uuid:event_id>/` - Event deletion test
- `/test/object-level-permissions/` - Object-level permissions comprehensive test dashboard
- `/test/hospital-context-middleware/` - Hospital context middleware test interface
- `/test/hospital-context-required/` - Test view that requires hospital context
- `/test/hospital-context-api/` - API endpoint for hospital context information
- `/test/role-permissions/` - Role-based permissions test dashboard
- `/test/role-permissions-api/` - API endpoint for role permission information
- `/test/template-tags/` - Template tags testing interface

#### Usage Examples

##### View Protection
```python
from apps.core.permissions import (
    patient_access_required,
    doctor_required,
    patient_data_change_required,
    can_delete_event_required
)

@patient_access_required
def patient_detail_view(request, patient_id):
    # User access to patient already validated
    patient = get_object_or_404(Patient, pk=patient_id)
    return render(request, 'patient_detail.html', {'patient': patient})

@patient_data_change_required
def patient_edit_personal_data_view(request, patient_id):
    # User permission to change patient personal data already validated
    patient = get_object_or_404(Patient, pk=patient_id)
    # Handle personal data editing logic
    pass

@can_delete_event_required
def event_delete_view(request, event_id):
    # User permission to delete event already validated
    event = get_object_or_404(Event, pk=event_id)
    # Handle event deletion logic
    pass

@doctor_required
def discharge_patient_view(request, patient_id):
    # Only doctors can access this view
    pass
```

##### Manual Permission Checks
```python
from apps.core.permissions import (
    can_access_patient,
    can_edit_event,
    can_change_patient_personal_data,
    can_delete_event,
    can_see_patient_in_search
)

def some_business_logic(user, patient, event):
    if can_access_patient(user, patient):
        # User can access patient
        if can_edit_event(user, event):
            # User can edit event
            pass

        if can_change_patient_personal_data(user, patient):
            # User can change patient personal data
            pass

    if can_delete_event(user, event):
        # User can delete event
        pass

    if can_see_patient_in_search(user, patient):
        # Patient should be visible in search results
        pass
```

##### Custom Permission Backend Usage
```python
# Using Django's permission system with objects
if user.has_perm('patients.change_patient_personal_data', patient):
    # User can change this specific patient's personal data
    pass

if user.has_perm('events.delete_event', event):
    # User can delete this specific event
    pass
```

### Implementation Status
The permission framework follows a vertical slicing approach for systematic implementation:

1. **Vertical Slice 1: Basic Permission Framework** ✅ **COMPLETED**
   - Core permission utilities and decorators
   - Basic permission checking functions
   - Comprehensive test coverage (16 tests)

2. **Vertical Slice 2: Hospital Context Management** ✅ **COMPLETED**
   - HospitalContextMiddleware for session-based hospital selection
   - Hospital selection view and template
   - Integration with existing permission utilities
   - Complete test coverage (16 tests across middleware and views)

3. **Vertical Slice 3: Role-Based Permission Groups** ✅ **COMPLETED**
   - Management command for setting up profession-based groups
   - Automatic user-group assignment via signal handlers
   - Django permission integration with role-based access control
   - Template tags for permission checking in templates
   - Comprehensive test coverage (37+ tests across all permission modules)

4. **Object-Level Permissions** (Vertical Slice 4) ✅ **COMPLETED**
   - Object-level permission utility functions for fine-grained access control
   - Custom permission backend integration with Django's permission system
   - Additional permission decorators for patient data and event deletion
   - Template tags for object-level permission checking in UI
   - Comprehensive test coverage (45+ tests for object-level permissions)

5. **UI Integration and Performance Optimization** (Vertical Slice 5) ✅ **COMPLETED**
   - Permission caching system with cache_permission_result decorator
   - Query optimization utilities for improved database performance
   - Enhanced template tags with performance widgets and bulk permission checks
   - Cache management utilities with statistics and invalidation
   - Performance monitoring and benchmarking tools
   - Comprehensive test coverage (45+ tests for performance optimization)

6. **Documentation and Final Integration** (Vertical Slice 6) ✅ **COMPLETED**
   - Comprehensive documentation suite (README, user guide, API reference)
   - Management commands for permission auditing and user management
   - Integration tests covering complete user workflows
   - Interactive demo application with real-time permission testing
   - Verification tools and quality assurance
   - Complete implementation with 14 new files and enhanced functionality

### Role-Based Permission Groups

#### Automatic Group Assignment
The system automatically assigns users to profession-based groups using Django signals:

- **Medical Doctors**: Full permissions for all models and operations
- **Residents**: Full access to patients, events, and hospital records in current hospital
- **Nurses**: Limited patient permissions (no delete), full event access, view-only hospitals
- **Physiotherapists**: Full access to patients, events, and hospital records in current hospital
- **Students**: View-only permissions for patients, events, and hospitals

#### Management Commands
```bash
# Set up all profession-based groups with appropriate permissions
python manage.py setup_groups

# Force recreation of groups (removes existing groups first)
python manage.py setup_groups --force

# Audit permission system
python manage.py permission_audit --action=report

# Manage user permissions
python manage.py user_permissions --action=assign --user-email=user@example.com --profession=medical_doctor

# Monitor performance
python manage.py permission_performance --action=stats
```

#### Template Tags for Permission Checking
The system provides comprehensive template tags for UI permission checks:

```django
{% load permission_tags %}

<!-- Django permission checks -->
{% if user|has_permission:"patients.add_patient" %}
    <a href="{% url 'patients:create' %}">Add Patient</a>
{% endif %}

<!-- Group membership checks -->
{% if user|in_group:"Medical Doctors" %}
    <p>Welcome, Doctor!</p>
{% endif %}

<!-- Profession type checks -->
{% if user|is_profession:"medical_doctor" %}
    <p>Doctor-specific content</p>
{% endif %}

<!-- Convenience permission filters -->
{% if user|can_manage_patients %}
    <p>You can manage patients</p>
{% endif %}

<!-- Multiple permission checks -->
{% check_multiple_permissions user "patients.add_patient" "patients.change_patient" as has_all_perms %}
{% if has_all_perms %}
    <p>You have all required permissions</p>
{% endif %}

<!-- Permission debug widget -->
{% permission_debug user %}

<!-- Performance monitoring widgets -->
{% permission_performance_widget user %}
{% permission_cache_stats as cache_stats %}

<!-- Any permission check -->
{% check_any_permission user "patients.add_patient" "patients.view_patient" as has_any_perm %}
{% if has_any_perm %}
    <p>You have at least one permission</p>
{% endif %}
```

#### Signal-Based Group Assignment
Users are automatically assigned to appropriate groups when:
- A new user is created with a profession type
- An existing user's profession type is changed
- Groups are created/removed automatically based on profession changes

### Object-Level Permissions

#### Overview
The system implements fine-grained object-level permissions that control access to specific patients and events based on user roles, hospital context, and time-based restrictions.

#### Object-Level Permission Functions

##### Patient-Related Permissions
- **`can_change_patient_personal_data(user, patient)`**: Controls who can modify patient personal information
  - Only doctors can change patient personal data
  - For outpatients: Any doctor can change data
  - For inpatients/emergency/discharged/transferred: Doctor must be in same hospital with hospital context

- **`can_see_patient_in_search(user, patient)`**: Controls patient visibility in search results
  - Uses same logic as `can_access_patient` for consistent access control
  - Extensible for future search-specific filtering requirements

##### Event-Related Permissions
- **`can_delete_event(user, event)`**: Controls event deletion permissions
  - Only event creators can delete their events
  - Events can only be deleted within 24 hours of creation
  - Same time-based restrictions as editing for audit trail integrity

#### Object-Level Permission Decorators

- **`@patient_data_change_required`**: View decorator for patient personal data modification
  - Validates user can change patient personal data
  - Extracts patient_id from URL parameters
  - Returns 403 Forbidden for unauthorized access

- **`@can_delete_event_required`**: View decorator for event deletion
  - Validates user can delete specific events
  - Extracts event_id from URL parameters
  - Enforces creator and time-based restrictions

#### Custom Permission Backend

**`EquipeMedPermissionBackend`** integrates object-level permissions with Django's permission system:

- **Integration**: Added to `AUTHENTICATION_BACKENDS` in settings
- **Object-Level Support**: Handles `user.has_perm(permission, obj)` calls
- **Supported Permissions**:
  - `patients.access_patient`
  - `patients.change_patient_personal_data`
  - `patients.see_patient_in_search`
  - `events.edit_event`
  - `events.delete_event`

#### Object-Level Template Tags

```django
{% load permission_tags %}

<!-- Patient personal data change permission -->
{% can_user_change_patient_personal_data user patient as can_change_data %}
{% if can_change_data %}
    <a href="{% url 'patients:edit_personal_data' patient.pk %}">Edit Personal Data</a>
{% endif %}

<!-- Event deletion permission -->
{% can_user_delete_event user event as can_delete %}
{% if can_delete %}
    <button class="btn btn-danger" onclick="deleteEvent('{{ event.pk }}')">Delete Event</button>
{% endif %}

<!-- Patient search visibility -->
{% can_user_see_patient_in_search user patient as can_see %}
{% if can_see %}
    <!-- Display patient in search results -->
{% endif %}

<!-- General permission filters -->
{% if user|can_change_patient_data %}
    <p>You have permission to change patient data</p>
{% endif %}
```

### Performance Optimization

#### Permission Caching System
The permission system includes comprehensive caching to improve performance:

- **`@cache_permission_result`**: Decorator for caching permission check results
- **Cache Key Generation**: Intelligent cache keys based on user ID, permission type, and object ID
- **Cache Invalidation**: Automatic cache invalidation when user permissions or object data changes
- **Cache Statistics**: Real-time monitoring of cache hit ratios and performance metrics

```python
from apps.core.permissions.cache import cache_permission_result

@cache_permission_result('can_access_patient', use_object_id=True)
def can_access_patient(user, patient):
    # Function implementation with automatic caching
    pass
```

#### Query Optimization
Optimized database queries for better performance:

- **`get_optimized_user_queryset()`**: User queries with prefetched permission data
- **`get_optimized_patient_queryset()`**: Patient queries with hospital and permission optimization
- **`get_patients_for_user(user)`**: Efficient patient filtering based on user permissions
- **`get_permission_summary_optimized(user)`**: Comprehensive permission summary with minimal queries

#### Cache Management
```python
from apps.core.permissions import (
    invalidate_user_permissions,
    clear_permission_cache,
    get_cache_stats
)

# Invalidate specific user permissions
invalidate_user_permissions(user.id)

# Clear all permission cache
clear_permission_cache()

# Get performance statistics
stats = get_cache_stats()
```

#### Performance Monitoring
- **Management Command**: `permission_performance` for benchmarking and monitoring
- **Template Tags**: Performance widgets for real-time cache statistics
- **Benchmarking Tools**: Automated performance testing with configurable iterations

### Security Features
- **Hospital Isolation**: Users can only access patients in their current hospital context
- **Time-Based Restrictions**: Medical record editing and deletion limited to 24-hour windows
- **Role-Based Access**: Different permissions for each medical profession via Django groups
- **Object-Level Permissions**: Fine-grained control over individual patient and event access
- **Custom Permission Backend**: Seamless integration with Django's permission system for object-level checks
- **Automatic Group Management**: Signal-based assignment ensures users always have correct permissions
- **Audit Trail Support**: Permission checks consider event creators and timestamps
- **Fail-Safe Defaults**: Permission functions return `False` for unauthorized access
- **CSRF Protection**: All permission-protected views include CSRF protection
- **Template-Level Security**: Permission checks available directly in templates
- **Personal Data Protection**: Strict controls on who can modify patient personal information

### Documentation and Management Tools

#### Comprehensive Documentation Suite
The permission system includes complete documentation for developers and end users:

- **`docs/permissions/README.md`**: Technical documentation covering architecture, API reference, and implementation details
- **`docs/permissions/user-guide.md`**: End-user guide with role explanations, workflows, and troubleshooting
- **`docs/permissions/api-reference.md`**: Comprehensive API reference with function signatures and usage examples

#### Management Commands

##### Permission Auditing
```bash
# Generate comprehensive permission report
python manage.py permission_audit --action=report

# Check system consistency and fix issues
python manage.py permission_audit --action=check --fix-issues

# List permissions for specific user
python manage.py permission_audit --action=list --user-id=123
```

##### User Permission Management
```bash
# Assign user to profession-based group
python manage.py user_permissions --action=assign --user-email=doctor@example.com --profession=medical_doctor

# Sync all users with their profession groups
python manage.py user_permissions --action=sync --all-users

# Reset user permissions
python manage.py user_permissions --action=reset --user-id=123 --dry-run
```

##### Performance Monitoring
```bash
# Show cache statistics
python manage.py permission_performance --action=stats

# Run performance benchmarks
python manage.py permission_performance --action=benchmark --iterations=1000

# Test query optimization
python manage.py permission_performance --action=test-queries --user-id=1
```

#### Demo Application
Interactive demo application for testing and demonstrating permission features:

- **Demo Dashboard**: `/demo/permissions/` - Overview of user permissions and system status
- **Patient Access Demo**: Real-time testing of patient access permissions
- **Doctor-Only Demo**: Demonstration of role-based access restrictions
- **Hospital Context Demo**: Hospital context requirement testing
- **Role Comparison**: Side-by-side comparison of permissions across different roles
- **Cache Management**: Interactive cache statistics and management interface

#### Integration Testing
Comprehensive integration test suite covering:
- Complete user workflows for all profession types
- Security edge cases and boundary conditions
- Performance validation with multiple permission checks
- End-to-end user journey simulation
- Cross-hospital access prevention testing

#### Verification and Quality Assurance
The permission system includes comprehensive verification tools:

- **`verify_permission_system.py`**: Automated verification script that checks all components
- **Module Structure Verification**: Ensures all required modules and files exist
- **Function Testing**: Validates that all permission utilities work correctly
- **Documentation Completeness**: Verifies all documentation files are present and substantial
- **Integration Testing**: Confirms all components work together properly

```bash
# Run comprehensive system verification
python verify_permission_system.py

# Expected output: Success rate and detailed component status
```

#### Testing Coverage Summary
- **45+ Total Tests**: Comprehensive test coverage across all permission modules
- **Unit Tests**: Individual function and decorator testing
- **Integration Tests**: End-to-end workflow validation
- **Performance Tests**: Cache effectiveness and query optimization
- **Security Tests**: Edge cases and unauthorized access attempts
- **UI Tests**: Template tag functionality and rendering

#### Quality Metrics
- **100% Module Coverage**: All required modules implemented and documented
- **Complete API Documentation**: Every function has comprehensive docstrings
- **Security Audit**: All edge cases and boundary conditions tested
- **Performance Optimization**: Caching and query optimization implemented
- **User Experience**: Interactive demo and comprehensive user guide

## Hospitals App Features

### Hospital Management
- **Full CRUD Operations**: Create, read, update, and delete hospitals
- **Address and Contact Information**: Complete hospital details including location and contact data
- **Search and Filtering**: Search hospitals by name, location, and other criteria
- **Audit Trail**: Created/updated by tracking for all hospital records

### Hospital Context Management
- **Session-based Hospital Selection**: Users can select their current hospital context via web interface
- **HospitalContextMiddleware**: Automatically injects hospital context into user objects for all requests
- **Context Persistence**: Selected hospital persists across browser sessions
- **Permission Integration**: Hospital context is seamlessly integrated with the permission framework
- **User-friendly Interface**: Bootstrap 5 styled hospital selection form with validation and messaging

### Ward Management

#### Ward Model Features
- **Hospital Association**: Each ward belongs to a specific hospital via foreign key relationship
- **Capacity Management**: Track total bed capacity and current occupancy
- **Status Tracking**: Active/inactive status for ward availability
- **Audit Fields**: Complete audit trail with created/updated timestamps and user tracking

#### Ward Properties
- **`patient_count`**: Dynamic property to count current patients in the ward (placeholder for Patient model integration)
- **`occupancy_rate`**: Calculated property showing percentage of capacity utilization

#### Ward CRUD Operations
- **Full CRUD Interface**: Complete create, read, update, delete operations with permission-based access
- **Permission-Required Views**: All modification operations require appropriate hospital permissions
- **Form Integration**: Crispy Forms with Bootstrap 5 styling for ward management

#### Ward Template System
- **Template Tags**: Custom `capacity_bar` template tag for visual capacity representation
- **Color-coded Display**: Progress bars with color coding based on occupancy levels:
  - Green: Under 70% occupancy
  - Yellow: 70-90% occupancy  
  - Red: Over 90% occupancy
- **Responsive Templates**: Bootstrap 5 styled templates for all ward views

### URL Structure
The hospitals app includes comprehensive URL routing:

#### Hospital URLs
- `/hospitals/` - Hospital list with search and filtering
- `/hospitals/create/` - Create new hospital
- `/hospitals/<uuid:pk>/` - Hospital detail view
- `/hospitals/<uuid:pk>/edit/` - Edit hospital
- `/hospitals/<uuid:pk>/delete/` - Delete hospital confirmation
- `/hospitals/select/` - Hospital context selection interface

#### Ward URLs
- `/hospitals/wards/` - Ward list with capacity visualization
- `/hospitals/wards/create/` - Create new ward
- `/hospitals/wards/<int:pk>/` - Ward detail view
- `/hospitals/wards/<int:pk>/update/` - Edit ward
- `/hospitals/wards/<int:pk>/delete/` - Delete ward confirmation
- `/hospitals/test/ward-tags/` - Template tag testing interface

### Template Tags and Filters
Custom template tags for hospitals app:

- **`capacity_bar`**: Template tag that renders Bootstrap progress bars for ward capacity
  - Usage: `{% load hospital_tags %}{% capacity_bar ward %}`
  - Features: Color-coded based on occupancy percentage, accessible markup, responsive design

### Forms and Validation
- **Hospital Forms**: Comprehensive validation for hospital data including address formatting and phone number validation
- **Ward Forms**: Crispy Forms integration with proper field layout and capacity validation
- **Bootstrap 5 Styling**: Consistent form styling across all hospital and ward operations

### Admin Integration
- **Hospital Admin**: Full admin interface with search, filtering, and bulk operations
- **Ward Admin**: Comprehensive ward management with hospital filtering and capacity display
- **Related Object Display**: Admin interfaces show related objects and relationships

### Middleware Architecture
- **HospitalContextMiddleware**: Located at `apps/hospitals/middleware.py`
- **Session Management**: Uses Django sessions to store current hospital selection
- **User Object Enhancement**: Adds `current_hospital` and `has_hospital_context` attributes to user objects
- **Error Handling**: Gracefully handles invalid hospital IDs by removing them from session
- **Helper Methods**: Provides static methods for setting, clearing, and getting available hospitals

### Testing Coverage
- **Middleware Tests**: Complete test suite in `apps/hospitals/tests/test_middleware.py` (8 tests)
- **View Tests**: Hospital selection view tests in `apps/hospitals/tests/test_hospital_selection_view.py` (8 tests)
- **Integration Tests**: Tests cover session management, context injection, and permission integration
- **Edge Cases**: Tests handle authentication, invalid hospitals, and session persistence

### Security and Permissions
- **Login Required**: All hospital and ward operations require user authentication
- **Permission-based Access**: Ward modifications require specific hospital permissions
- **Audit Logging**: Complete tracking of who created and updated hospital/ward records
- **CSRF Protection**: All forms include proper CSRF protection
- **Hospital Context Security**: Users can only access patients in their selected hospital context

## Events App Features

The Events app provides a foundational system for all medical record events and activities in the EquipeMed platform.

### Event Management
- **Base Event Model**: Extensible foundation for all event types using django-model-utils inheritance
- **Multiple Event Types**: Support for 10 different medical record event types in Portuguese
- **UUID Primary Keys**: Enhanced security and scalability for event identification
- **Audit Trail**: Complete tracking of creation and update information with user attribution
- **Custom Permissions**: Special permissions for editing/deleting own events within 24 hours

### Event Types Supported
1. **Anamnese e Exame Físico** (History and Physical Event)
2. **Evolução** (Daily Note Event)
3. **Nota/Observação** (Simple Note Event)
4. **Imagem** (Photo Event)
5. **Resultado de Exame** (Exam Result Event)
6. **Requisição de Exame** (Exams Request Event)
7. **Relatório de Alta** (Discharge Report Event)
8. **Receita** (Outpatient Prescription Event)
9. **Relatório** (Report Event)
10. **Série de Fotos** (Photo Series Event)

### Event Features
- **Patient Association**: Each event is linked to a specific patient with foreign key protection
- **DateTime Tracking**: Event date/time separate from creation timestamp for accurate medical records
- **Description Field**: 255-character description for event summary
- **Ordering**: Events ordered by creation date (newest first) for chronological display
- **Inheritance Ready**: Uses InheritanceManager to support specialized event type extensions

### URL Structure
The events app provides clean URL routing:
- `/events/patient/<uuid:patient_id>/` - List all events for a specific patient
- `/events/user/` - List all events created or updated by the current user

### Views and Templates
- **Patient Events List**: Paginated view of all events for a specific patient (10 per page)
- **User Events List**: Paginated view of events created/updated by current user (10 per page)
- **Bootstrap 5 Templates**: Responsive templates with proper pagination controls
- **Portuguese Localization**: All interface text in Portuguese
- **Login Required**: All views require user authentication

### Admin Integration
- **EventAdmin**: Full Django admin integration with optimized queries
- **List Display**: Shows description, event type, datetime, patient, creator, and creation date
- **Filtering**: Filter by event type, creation date, and event datetime
- **Search**: Search by description and patient name
- **Date Hierarchy**: Browse events by creation date
- **Readonly Fields**: ID, creation, and update timestamps protected

### Forms and Validation
- **EventForm**: Crispy Forms integration with Bootstrap 5 styling
- **DateTime Widget**: HTML5 datetime-local input for precise event timing
- **Field Layout**: Responsive two-column layout for event type and datetime
- **Form Validation**: Comprehensive validation for all required fields

### Extensibility
The Events app is designed for extension with specific event types:

```python
from apps.events.models import Event

class DailyNoteEvent(Event):
    content = models.TextField(verbose_name="Conteúdo")
    
    def save(self, *args, **kwargs):
        self.event_type = self.DAILY_NOTE_EVENT
        super().save(*args, **kwargs)
```

### Testing Coverage
Comprehensive test suite includes:
- **Model Tests**: Event creation, string representation, ordering
- **Admin Tests**: Registration and configuration verification
- **Form Tests**: Valid/invalid data validation
- **View Tests**: Authentication, pagination, template usage
- **Template Tests**: Content rendering and proper display
- **13 Total Tests**: All passing with complete functionality coverage

### Dependencies
- **django-model-utils**: Required for InheritanceManager functionality
- **Bootstrap 5**: For consistent UI styling
- **Crispy Forms**: For form layout and styling

### Security Features
- **UUID Primary Keys**: Non-sequential identifiers for enhanced security
- **PROTECT on Delete**: Prevents accidental data loss through foreign key protection
- **Login Required**: All operations require authenticated users
- **Audit Fields**: Complete tracking of who created and modified events
- **CSRF Protection**: All forms include proper CSRF protection