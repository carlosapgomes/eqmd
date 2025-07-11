# Phase 8: Documentation Update

**Estimated Time:** 45-60 minutes  
**Complexity:** Medium  
**Dependencies:** Phase 7 completed

## Objectives

1. Update CLAUDE.md to reflect single-hospital architecture
2. Update project documentation and README
3. Remove hospital-related documentation
4. Update setup and deployment instructions
5. Update API documentation (if any)
6. Create migration guide from multi-hospital

## Tasks

### 1. Update CLAUDE.md - Major Rewrite

**Remove hospital-related sections:**
- [ ] Remove entire "Hospitals App" section
- [ ] Remove hospital context middleware documentation
- [ ] Remove hospital permission system details
- [ ] Remove hospital-related commands

**Update App Details sections:**

**Patients App** - Simplify hospital assignment logic:
```markdown
<!-- Before (complex hospital logic) -->
#### Hospital Assignment Logic

- **Admitted Patients** (inpatient, emergency, transferred): Require `current_hospital` assignment
- **Outpatients/Discharged**: No `current_hospital` assignment (hospital-independent)
- **Automatic Management**: Hospital assignments auto-cleared/set on status changes
- **Historical Tracking**: PatientHospitalRecord maintains treatment history across facilities
- **Form Validation**: Dynamic hospital field visibility based on patient status

<!-- After (simple status logic) -->
#### Patient Status Management

- **Patient Status**: Tracks patient care status (inpatient, outpatient, emergency, discharged, transferred)
- **Status-Based Access**: Different user roles have different access levels based on patient status
- **Form Validation**: Simple status validation without complex assignment logic
```

**Permission System** - Complete rewrite:
```markdown
<!-- Before (complex hospital + role permissions) -->
## Permission System

**Comprehensive role-based access control with hospital context**

### Core Framework
- **Hospital Context**: Status-dependent access control
- **Permission Rules**: Doctors: Full permissions, can discharge patients
- **Residents/Physiotherapists**: Full access to current hospital patients

<!-- After (simplified role-based) -->
## Permission System

**Simple role-based access control focused on medical professions**

### Core Framework
Located in `apps/core/permissions/`:
- **constants.py**: Profession types (Doctor, Resident, Nurse, Physiotherapist, Student)
- **utils.py**: Core permission functions (`can_access_patient`, `can_edit_event`, etc.)
- **decorators.py**: View decorators (`@patient_access_required`, `@doctor_required`)

### Permission Rules
- **Doctors**: Full access to all patients, can discharge patients
- **Residents/Physiotherapists**: Full access to all patients, cannot discharge
- **Nurses**: Access to all patients, limited status changes, cannot discharge
- **Students**: View-only access to outpatients and discharged patients only
- **Time limits**: 24-hour edit/delete window for events
```

**Update Essential Commands:**
```markdown
<!-- Remove hospital-related commands -->
# Development
python manage.py runserver
python manage.py migrate
python manage.py makemigrations
python manage.py createsuperuser

# Testing
pytest                                      # All tests with coverage
python manage.py test apps.patients.tests  # Recommended for patients/events/dailynotes apps
python manage.py test apps.core.tests.test_permissions

# Sample data
python manage.py create_sample_tags
python manage.py create_sample_content
```

### 2. Update Project Architecture Overview

**Simplify Apps Overview:**
```markdown
<!-- Remove hospitals app -->
### Apps Overview

- **core**: Dashboard, permissions, landing page
- **accounts**: Custom user model with medical professions (Doctor, Resident, Nurse, Physiotherapist, Student)
- **patients**: Patient management with tagging system and status tracking
- **events**: Base event model for medical records (UUID, audit trail, 24h edit window)
- **dailynotes**: Daily evolution notes extending Event model
- **sample_content**: Template content management for various event types
- **mediafiles**: Secure media file management for medical images and videos
```

**Update Key Features:**
```markdown
### Key Features

- **Authentication**: django-allauth with email-based login
- **Frontend**: Bootstrap 5.3, Webpack, Portuguese localization
- **Security**: UUID identifiers, CSRF protection, role-based permissions
- **Testing**: pytest + Django test runner, factory-boy, comprehensive coverage
- **Permission System**: Simple role-based access control for medical staff
```

### 3. Update Patient App Documentation

**Simplify patient documentation:**
```markdown
### Patients App

**Full CRUD patient management with tagging system and status tracking**

- Patient models: Patient, AllowedTag, Tag
- Search by name, ID, fiscal/health card numbers
- Status tracking: inpatient, outpatient, emergency, discharged, transferred
- Color-coded tagging system with web admin interface
- Dashboard widgets: patient stats, recent patients
- Template tags: `patient_status_badge`, `patient_tags`
- URL structure: `/patients/`, `/patients/<uuid>/`, `/patients/tags/`

#### Patient Status Management

- **Status Types**: inpatient, outpatient, emergency, discharged, transferred
- **Role-Based Access**: Different access levels based on user profession and patient status
- **Simple Validation**: Basic status validation without complex assignment logic
```

### 4. Remove Hospital-Related Documentation

**Delete hospital documentation sections:**
- [ ] Remove "Hospital Context Middleware" section
- [ ] Remove "Hospital Assignment Logic" section
- [ ] Remove hospital-related template tags documentation
- [ ] Remove hospital management commands

### 5. Update Permission System Documentation

**Rewrite permission documentation:**
```markdown
## Permission System

**Simple role-based access control for medical professionals**

### Permission Rules

**Doctors:**
- Full access to all patients regardless of status
- Can discharge patients
- Can edit patient personal data
- Can create and edit all types of events

**Residents/Physiotherapists:**
- Full access to all patients
- Cannot discharge patients
- Can edit patient data and create events

**Nurses:**
- Access to all patients
- Limited status changes (cannot discharge)
- Cannot edit patient personal data
- Can create daily notes and basic events

**Students:**
- View-only access to outpatients and discharged patients only
- No access to inpatients, emergency, or transferred patients
- Cannot edit any patient data or create events

### Key Functions

```python
can_access_patient(user, patient)           # Role and status-based access
can_edit_event(user, event)                 # Time-limited editing (24h)
can_change_patient_status(user, patient, status)  # Role-based status changes
can_change_patient_personal_data(user, patient)   # Doctor-only data changes
get_user_accessible_patients(user)          # Role-filtered patient queryset
```

### Management Commands

```bash
python manage.py setup_groups              # Create profession-based groups
python manage.py permission_audit --action=report  # System audit
python manage.py user_permissions --action=assign # Assign user to group
```
```

### 6. Update Setup and Installation Instructions

**Simplify setup instructions:**
```markdown
## Installation and Setup

### Quick Start

1. **Clone and setup:**
   ```bash
   git clone <repository>
   cd eqmd
   uv install
   ```

2. **Database setup:**
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

3. **Sample data (optional):**
   ```bash
   python manage.py create_sample_tags
   python manage.py create_sample_content
   ```

4. **Run development server:**
   ```bash
   python manage.py runserver
   ```

### First Time Setup

After creating a superuser:
1. Log in to admin at `/admin/`
2. Create user groups: `python manage.py setup_groups`
3. Assign users to appropriate professional groups
4. Create patients and start using the system

<!-- Remove hospital setup instructions -->
```

### 7. Update API Documentation (if applicable)

**Simplify API documentation:**
- [ ] Remove hospital context from API endpoints
- [ ] Update permission documentation for API
- [ ] Remove hospital filtering from API examples

### 8. Update Deployment Documentation

**Simplify deployment:**
```markdown
## Deployment

### Environment Variables

```bash
# Required settings
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=your-domain.com

# Database
DATABASE_URL=postgres://user:pass@localhost/dbname

# Email (for allauth)
EMAIL_HOST=smtp.your-provider.com
EMAIL_HOST_USER=your-email@domain.com
EMAIL_HOST_PASSWORD=your-email-password

<!-- Remove hospital-related environment variables -->
```

### Production Checklist

- [ ] Set DEBUG=False
- [ ] Configure database
- [ ] Set up email backend
- [ ] Configure static files serving
- [ ] Set up SSL/HTTPS
- [ ] Run security checks: `python manage.py check --deploy`
- [ ] Create user groups: `python manage.py setup_groups`

<!-- Remove hospital-related deployment steps -->
```

### 9. Update README.md

**Rewrite project description:**
```markdown
# EquipeMed

A Django 5 medical team collaboration platform for patient tracking and care management.

## Features

- **Patient Management**: Complete CRUD operations with status tracking
- **Medical Events**: Comprehensive event system for medical records
- **Daily Notes**: Evolution notes with timeline display
- **Media Files**: Secure handling of medical images and videos
- **Role-Based Permissions**: Access control for medical professionals
- **Tagging System**: Flexible patient categorization
- **Responsive Design**: Bootstrap 5.3 with mobile support

## Medical Professions Supported

- **Doctors**: Full system access
- **Residents**: Full patient access, limited administrative functions  
- **Nurses**: Patient care access with restrictions
- **Physiotherapists**: Full patient access for treatment
- **Students**: Limited read-only access for learning

<!-- Remove hospital-related features -->
```

### 10. Create Migration Guide

**Create hospital-to-single migration guide:**
```markdown
# Migration Guide: Multi-Hospital to Single-Hospital

If you have an existing multi-hospital deployment and want to migrate to the simplified single-hospital architecture:

## Before Migration

1. **Backup your database completely**
2. **Export critical hospital assignment data if needed**
3. **Document current user-hospital assignments**
4. **Test migration process on a copy first**

## Migration Process

1. **Switch to single-hospital branch:**
   ```bash
   git checkout single-hospital-refactor
   ```

2. **Run migrations in order:**
   ```bash
   python manage.py migrate patients remove_patient_hospital_record
   python manage.py migrate patients remove_hospital_fields  
   python manage.py migrate accounts remove_hospital_fields
   ```

3. **Update user permissions:**
   ```bash
   python manage.py setup_groups
   python manage.py permission_audit --action=report
   ```

## Data Loss Warning

This migration will permanently remove:
- All hospital assignments
- PatientHospitalRecord history
- User-hospital memberships
- Hospital-related audit trails

## Rollback

To rollback to multi-hospital:
```bash
git checkout prescriptions  # Original multi-hospital branch
python manage.py migrate
```
```

### 11. Update Development Guidelines

**Simplify development guidelines:**
```markdown
## Development Guidelines

### Adding New Features

1. **Follow role-based permissions** - Use existing permission functions
2. **Simple patient access** - Use `can_access_patient(user, patient)`
3. **Status-based logic** - Focus on patient status rather than location
4. **Template patterns** - Follow existing template inheritance

### Testing

- **Permission Tests**: Test role-based access patterns
- **Patient Tests**: Test status transitions and access
- **Event Tests**: Test time-based and role-based editing
- **Integration Tests**: Test complete user workflows

<!-- Remove hospital-related development guidelines -->
```

## Files to Update

### Documentation Files:
- [ ] `CLAUDE.md` - Major rewrite removing hospital complexity
- [ ] `README.md` - Simplify project description and features
- [ ] `docs/` directory (if exists) - Remove hospital documentation
- [ ] `CONTRIBUTING.md` (if exists) - Update development guidelines

### Configuration Documentation:
- [ ] `.env.example` - Remove hospital environment variables
- [ ] Deployment guides - Simplify without hospital context
- [ ] Docker documentation - Remove hospital configuration

### New Files to Create:
- [ ] `MIGRATION.md` - Guide for migrating from multi-hospital
- [ ] Updated architecture diagrams (if any exist)

## Validation Checklist

Before completing the refactor:
- [ ] CLAUDE.md accurately reflects simplified architecture
- [ ] README shows correct feature set
- [ ] Setup instructions work for new installations
- [ ] Permission system documented correctly
- [ ] No references to removed hospital functionality
- [ ] Migration guide provides clear path
- [ ] All documentation consistent with codebase

## Final Project Status

**After Phase 8 completion:**
- Single-hospital architecture fully implemented
- Documentation reflects simplified system
- Permission system is role-based only
- Hospital complexity completely removed
- Clean, maintainable codebase
- Simplified development and deployment

**Benefits Achieved:**
- ~60% reduction in permission system complexity
- ~40% reduction in overall codebase complexity
- Simpler development workflow
- Easier testing and deployment
- Better security through simplified permissions
- Improved performance through reduced overhead