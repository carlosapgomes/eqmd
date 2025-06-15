# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Essential Commands

### Development
```bash
# Development server
python manage.py runserver

# Database
python manage.py migrate
python manage.py makemigrations
python manage.py createsuperuser

# Testing
pytest                                      # All tests with coverage
pytest --no-cov                           # Without coverage
python manage.py test apps.patients.tests # Recommended for patients/events/dailynotes apps
python manage.py test apps.core.tests.test_permissions

# Frontend
npm install && npm run build

# Python environment
uv install
uv add package-name

# Sample data
python manage.py create_sample_tags
```

## Project Architecture

**EquipeMed** - Django 5 medical team collaboration platform for patient tracking across hospitals.

### Apps Overview
- **core**: Dashboard, permissions, landing page
- **accounts**: Custom user model with medical professions (Doctor, Resident, Nurse, Physiotherapist, Student)
- **hospitals**: Hospital/ward management with context middleware
- **patients**: Patient management with tagging system and hospital records
- **events**: Base event model for medical records (UUID, audit trail, 24h edit window)
- **dailynotes**: Daily evolution notes extending Event model

### Key Features
- **Authentication**: django-allauth with email-based login
- **Frontend**: Bootstrap 5.3, Webpack, Portuguese localization, Crispy Forms
- **Security**: UUID identifiers, CSRF protection, role-based permissions
- **Testing**: pytest + Django test runner, factory-boy, comprehensive coverage

## App Details

### Patients App
**Full CRUD patient management with tagging system and intelligent hospital relationships**
- Patient models: Patient, PatientHospitalRecord, AllowedTag, Tag
- Search by name, ID, fiscal/health card numbers
- Status tracking: inpatient, outpatient, emergency, discharged, transferred
- Color-coded tagging system with web admin interface
- Dashboard widgets: patient stats, recent patients
- Template tags: `patient_status_badge`, `patient_tags`
- URL structure: `/patients/`, `/patients/<uuid>/`, `/patients/tags/`

#### Hospital Assignment Logic
- **Admitted Patients** (inpatient, emergency, transferred): Require `current_hospital` assignment
- **Outpatients/Discharged**: No `current_hospital` assignment (hospital-independent)
- **Automatic Management**: Hospital assignments auto-cleared/set on status changes
- **Historical Tracking**: PatientHospitalRecord maintains treatment history across facilities
- **Form Validation**: Dynamic hospital field visibility based on patient status

### Events App
**Base event system for medical records**
- Event types: History/Physical, Daily Notes, Photos, Exam Results, etc.
- UUID primary keys, audit trail, 24-hour edit/delete window
- django-model-utils inheritance for extensibility
- URLs: `/events/patient/<uuid>/`, `/events/user/`

#### Timeline Template Architecture
**Modular event card system with type-specific functionality**
- **Template Partials**: Located in `apps/events/templates/events/partials/`
  - `event_card_base.html` - Base template with common structure
  - `event_card_dailynote.html` - DailyNote-specific card with duplicate button
  - `event_card_default.html` - Standard card for other event types
- **Dynamic Rendering**: Timeline uses `event.event_type` to select appropriate template
- **Event Type Detection**: `event.event_type == 1` identifies DailyNote events
- **Extensibility**: Easy to add custom cards for new event types

### Daily Notes App
**Medical evolution notes extending Event model**
- DailyNote model inherits from Event
- Portuguese localization ("Evolução"/"Evoluções")
- Automatic event_type assignment
- Admin interface with fieldsets and optimizations

#### Advanced Features (Slice 5)
- **Patient Integration**: Patient-specific daily note views with date filtering
- **Search & Filtering**: Advanced search by content, patient, creator, and date ranges
- **Dashboard Integration**: Recent daily notes widget and statistics counters
- **Export/Print**: Print-friendly individual notes and patient evolution reports
- **URLs**: `/dailynotes/`, `/dailynotes/patient/<uuid>/`, `/dailynotes/<uuid>/print/`
- **Template Tags**: `recent_dailynotes_widget`, `dailynotes_count_today`, `dailynotes_count_week`

#### Duplicate Functionality
**Create new dailynotes based on existing ones**
- **Multiple Access Points**: Available from detail page, list views, and patient timeline
- **Pre-population**: Original content copied, datetime set to current time
- **Permission-Based**: Only visible to users with `events.add_event` permission
- **Timeline Integration**: Specialized event card template with duplicate button
- **URL Pattern**: `/dailynotes/<uuid>/duplicate/`
- **Success Redirect**: Returns to patient timeline after creation

#### Performance Optimizations (Slice 6)
- **Database Optimization**: Added indexes for common query patterns on Event model
- **Query Optimization**: Enhanced views with `select_related()` and `prefetch_related()`
- **Pagination**: Improved pagination with `paginate_orphans` for better UX
- **Permission Caching**: Bulk patient access checks with `get_user_accessible_patients()`
- **Filter Caching**: Cached filter dropdown options for list views (5-minute cache)
- **Query Patterns**: Optimized patient/creator lookups with `only()` clauses

### Hospitals App
**Hospital and ward management with context middleware**
- Hospital/Ward models with capacity tracking
- HospitalContextMiddleware for session-based hospital selection
- Template tag: `capacity_bar` with color-coded occupancy
- URLs: `/hospitals/`, `/hospitals/wards/`, `/hospitals/select/`

## Permission System
**Comprehensive role-based access control with hospital context**

### Core Framework
Located in `apps/core/permissions/`:
- **constants.py**: Profession types (Doctor, Resident, Nurse, Physiotherapist, Student)
- **utils.py**: Core permission functions (`can_access_patient`, `can_edit_event`, etc.)
- **decorators.py**: View decorators (`@patient_access_required`, `@doctor_required`)
- **cache.py**: Permission caching system
- **backends.py**: Custom Django permission backend

### Permission Rules
- **Doctors**: Full permissions, can discharge patients
- **Residents/Physiotherapists**: Full access to current hospital patients
- **Nurses**: Limited status changes, cannot discharge
- **Students**: View-only outpatients (accessible across all user hospitals)
- **Time limits**: 24-hour edit/delete window for events
- **Hospital context**: Status-dependent access control

#### Patient Access Rules (Updated)
- **Admitted Patients** (inpatient, emergency, transferred): Strict hospital matching required
- **Outpatients/Discharged**: Broader access - users can access patients from any hospital where:
  - Patient has historical records (PatientHospitalRecord) at user's hospitals, OR
  - Patient has current hospital assignment at user's hospitals, OR
  - User belongs to hospitals where patient was previously treated
- **Students**: Limited to outpatients only, but accessible across all user hospitals

### Key Functions
```python
can_access_patient(user, patient)           # Status-dependent hospital access
can_edit_event(user, event)                 # Time-limited editing
can_change_patient_status(user, patient, status)  # Role-based status changes
can_change_patient_personal_data(user, patient)   # Doctor-only data changes
get_user_accessible_patients(user)          # Optimized patient queryset filtering
```

### Patient Model Methods
```python
patient.requires_hospital_assignment        # Check if status requires hospital
patient.should_clear_hospital_assignment    # Check if status should clear hospital
patient.is_currently_admitted()             # Check if patient is actively admitted
patient.has_hospital_record_at(hospital)    # Check treatment history at hospital
```

### Management Commands
```bash
python manage.py setup_groups              # Create profession-based groups
python manage.py permission_audit --action=report  # System audit
python manage.py user_permissions --action=assign # Assign user to group
python manage.py permission_performance --action=stats  # Performance stats
```

### Template Tags
```django
{% load permission_tags %}
{% if user|has_permission:"patients.add_patient" %}...{% endif %}
{% if user|in_group:"Medical Doctors" %}...{% endif %}
{% check_multiple_permissions user "perm1" "perm2" as has_all %}
```