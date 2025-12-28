<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Essential Commands

### Development

````bash
# Development server
uv run python manage.py runserver

# Database
uv run python manage.py migrate
uv run python manage.py makemigrations
uv run python manage.py createsuperuser

# Testing

## Test Running Options

### Option 1: pytest (Recommended for most cases)
```bash
# All tests with coverage (requires DJANGO_SETTINGS_MODULE)
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest

# All tests without coverage
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest --no-cov

# Specific app tests with coverage
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/pdf_forms/tests/

# Single test file
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/pdf_forms/tests/test_models.py

# Single test method
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/pdf_forms/tests/test_models.py::PDFFormTemplateTests::test_str_method
````

### Option 2: Django test runner (Use for specific apps)

```bash
# For apps that work better with Django's test runner
uv run python manage.py test apps.patients.tests
uv run python manage.py test apps.core.tests.test_permissions

# For specific test files
uv run python manage.py test apps.pdf_forms.tests.test_models
```

### Option 3: pytest with coverage reports

```bash
# Generate HTML coverage report (opens in browser)
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest --cov=apps --cov-report=html

# Coverage for specific app with terminal output
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/pdf_forms/tests/ --cov=apps.pdf_forms --cov-report=term-missing
```

## Which to Use?

- **Use pytest** for most testing (faster, better features, coverage)
- **Use Django test runner** for specific apps that have import issues
- **Set DJANGO_SETTINGS_MODULE** when using pytest to avoid configuration errors

### Password Change Security Tests

```bash
# Test forced password change functionality
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/accounts/tests/test_password_change_required.py

# Test password change middleware
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/core/tests/test_password_change_middleware.py

# Test complete password security flow
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/accounts/tests/test_password_change_required.py apps/core/tests/test_password_change_middleware.py
```

### Terms of Use System Tests

```bash
# Test terms acceptance functionality (when tests are available)
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/accounts/tests/test_terms_acceptance.py

# Test terms acceptance middleware (when tests are available)  
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/core/tests/test_terms_middleware.py

# Manual verification of terms system
uv run python manage.py shell -c "
from apps.accounts.models import EqmdCustomUser
users = EqmdCustomUser.objects.all()
print(f'Users without terms accepted: {users.filter(terms_accepted=False).count()}')
print(f'Users with terms accepted: {users.filter(terms_accepted=True).count()}')
"
```

### Admission Edit Permissions Tests

```bash
# Test admission edit permissions functionality
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/patients/tests/test_admission_permissions.py

# Test admission edit views integration
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/patients/tests/test_admission_edit_views.py

# Test specific permission scenarios
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/patients/tests/test_admission_permissions.py::AdmissionEditPermissionTests
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/patients/tests/test_admission_permissions.py::DischargePatientPermissionTests
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/patients/tests/test_admission_permissions.py::EditDischargeDataPermissionTests
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/patients/tests/test_admission_permissions.py::CancelDischargePermissionTests
```

# Frontend

npm install && npm run build

## Static Files Organization

**This project uses Webpack for static file management with the following directory structure:**

### Directory Structure

```
├── assets/                    # SOURCE FILES (committed to git)
│   ├── js/                   # JavaScript source files
│   ├── scss/                 # SCSS source files  
│   ├── images/               # Image assets
│   └── index.js              # Webpack entry point
├── static/                    # WEBPACK OUTPUT (committed, but regenerated)
│   ├── js/                   # Compiled/copied JavaScript
│   ├── css/                  # Compiled CSS
│   └── images/               # Copied images
└── staticfiles/              # DJANGO COLLECTSTATIC OUTPUT (not committed)
    └── ...                   # All static files for production
```

### Where to Put New Files

#### ✅ JavaScript Files
- **Source**: `assets/js/your_file.js`
- **Output**: `static/js/your_file.js` (auto-generated)
- **Template**: `{% static 'js/your_file.js' %}`

#### ✅ CSS/SCSS Files  
- **Source**: `assets/scss/your_file.scss`
- **Output**: `static/your_file.css` (auto-generated)
- **Template**: `{% static 'your_file.css' %}`

#### ✅ Images
- **Source**: `assets/images/your_image.png`
- **Output**: `static/images/your_image.png` (auto-copied)
- **Template**: `{% static 'images/your_image.png' %}`

### Adding New Static Files

#### 1. For Individual JavaScript Files (Recommended)

Add to `webpack.config.js` copy patterns:

```javascript
{
  from: "assets/js/your_file.js",
  to: "js/your_file.js",
},
```

#### 2. For Bundled JavaScript Files

Add to webpack entry points:

```javascript
entry: {
  your_bundle: [
    "./assets/js/file1.js",
    "./assets/js/file2.js"
  ]
}
```

#### 3. Build Process

```bash
npm run build    # Compiles and copies all assets
```

### Important Rules

- **❌ NEVER edit files in `static/` directly** - Webpack overwrites them
- **✅ ALWAYS put source files in `assets/`**
- **✅ ALWAYS update `webpack.config.js` for new files**  
- **✅ ALWAYS run `npm run build` after changes**
- **📝 COMMIT both `assets/` and `static/` to git**

## Frontend Styling Guidelines

**IMPORTANT: Bootstrap vs Django Admin Styling**

### ✅ Use Bootstrap 5.3 for:
- **User-facing templates** (`templates/` directories in apps)
- **Main application interface** (patient management, forms, dashboards)
- **Public pages** (login, landing pages, user workflows)
- **Custom views and templates** accessed by medical staff

### ❌ Keep Django Admin styling for:
- **Admin interface templates** (`templates/admin/` directories)
- **Django admin customizations**
- **Administrative backend interfaces**
- **Staff-only management interfaces**

### Key Rules:
- **NEVER** add Bootstrap CSS/JS to admin templates - use vanilla JavaScript instead
- **ALWAYS** use Bootstrap for main application templates and user-facing interfaces
- **MAINTAIN** Django's default admin styling for consistency and functionality
- **PREFER** vanilla JavaScript over Bootstrap JS in admin contexts when needed

### Examples:
```
✅ templates/patients/patient_list.html - Use Bootstrap
✅ templates/pdf_forms/form_fill.html - Use Bootstrap
❌ templates/admin/pdf_forms/configure_fields.html - NO Bootstrap, use vanilla JS
❌ templates/admin/patients/change_form.html - Keep Django admin styling
```

# Python environment

uv install
uv add package-name

# Sample data

uv run python manage.py create_sample_tags
uv run python manage.py create_sample_wards
uv run python manage.py create_sample_content
uv run python manage.py create_sample_pdf_forms

# Clinical Research and Full-Text Search

## Full-Text Search Setup

```bash
# Initialize search vectors for existing daily notes
uv run python manage.py populate_search_vectors

# Check search functionality
uv run python manage.py shell -c "
from apps.research.utils import perform_fulltext_search_queryset
results = perform_fulltext_search_queryset('diabetes', max_patients=10)
print(f'Found {len(results)} patients')
"
```

## Advanced Search Capabilities

The clinical research module supports PostgreSQL's advanced full-text search with:

- **Auto-optimization**: `diabetes` → `diabetes*`, `diabetes dor` → `diabetes & dor`
- **Exact phrases**: `"diabetes mellitus"`, `"dor torácica"`
- **Boolean logic**: `diabetes & hipertensão`, `diabetes | hipertensão`, `diabetes & !gestacional`
- **Prefix matching**: `medicaç*`, `cardio*`, `hiperten*`
- **Complex queries**: `diabetes & (medicaç* | insulin*)`

**📖 Complete documentation**: See [docs/fts-vector-indexation.md](docs/fts-vector-indexation.md)

# Data Import

## Firebase Import

For incremental sync of patients and dailynotes from Firebase Realtime Database, see the detailed guide:

**📖 [Firebase Import Documentation](docs/firebase-import.md)**

Quick command reference:
```bash
# Single command sync (patients + dailynotes)
uv run python manage.py sync_firebase_data \
  --credentials-file firebase-key.json \
  --database-url https://your-project.firebaseio.com \
  --project-name your-project \
  --since-date $(date -d "yesterday" +%Y-%m-%d)

# Docker production sync
docker compose run --rm \
  -v ./firebase-key.json:/app/firebase-key.json:ro \
  eqmd python manage.py sync_firebase_data \
    --credentials-file firebase-key.json \
    --database-url https://your-project.firebaseio.com \
    --project-name your-project \
    --since-date $(date -d "yesterday" +%Y-%m-%d) \
    --chunk-size 500

# With email reporting for adoption tracking
docker compose run --rm \
  -v ./firebase-key.json:/app/firebase-key.json:ro \
  eqmd python manage.py sync_firebase_data \
    --credentials-file firebase-key.json \
    --database-url https://your-project.firebaseio.com \
    --project-name your-project \
    --since-date $(date -d "yesterday" +%Y-%m-%d) \
    --chunk-size 500 \
    --email admin@yourcompany.com
```

# Cache management (performance)

uv run python manage.py update_dashboard_stats
uv run python manage.py update_ward_mapping_cache
uv run python manage.py check_cache_health --verbose

# Security monitoring and audit history

uv run python manage.py detect_suspicious_activity --comprehensive --days=7
uv run python manage.py security_alert_monitor --continuous --critical-only
uv run python manage.py security_report --days=30 --format=json --output=report.json

# User lifecycle management commands

docker compose exec eqmd python manage.py check_user_expiration --dry-run
docker compose exec eqmd python manage.py send_expiration_notifications --dry-run
docker compose exec eqmd python manage.py cleanup_inactive_users --format table
docker compose exec eqmd python manage.py extend_user_access username --days 90 --reason "Extension reason"
docker compose exec eqmd python manage.py lifecycle_report --output-file report.csv

````

## Project Architecture

**EquipeMed** - Django 5 medical team collaboration platform for single-hospital patient tracking and care management.

### Apps Overview

- **core**: Dashboard, permissions, landing page, hospital configuration
- **accounts**: Custom user model with medical professions (Doctor, Resident, Nurse, Physiotherapist, Student)
- **patients**: Patient management with tagging system, status tracking, and internal ward/bed transfer management
- **events**: Base event model for medical records (UUID, audit trail, 24h edit window)
- **dailynotes**: Daily evolution notes extending Event model
- **research**: Clinical research with advanced full-text search capabilities
- **sample_content**: Template content management for various event types
- **mediafiles**: Secure media file management for medical images and videos
- **pdf_forms**: Hospital-specific PDF form overlay functionality with dynamic form generation

### Key Features

- **Authentication**: django-allauth with email-based login
- **Frontend**: Bootstrap 5.3 (user-facing only), Webpack, Portuguese localization
- **Security**: UUID identifiers, CSRF protection, role-based permissions, comprehensive audit history
- **User Lifecycle Management**: Automated account expiration, activity tracking, and renewal workflows for residents/students
- **Testing**: pytest + Django test runner, factory-boy, comprehensive coverage
- **Hospital Configuration**: Environment-based single hospital setup
- **Permission System**: Simple role-based access control for medical staff
- **Audit History**: Complete change tracking with security monitoring capabilities

## Security and Audit History

**EquipeMed includes comprehensive audit history tracking and security monitoring.**

### Quick Reference
- All model changes tracked in dedicated history tables
- Django admin "History" button for detailed view
- Security monitoring commands: `detect_suspicious_activity`, `security_alert_monitor`, `security_report`
- Patient history: `/patients/<patient_id>/history/`

**📖 Detailed documentation**: See [docs/security/audit-history.md](docs/security/audit-history.md)

## User Lifecycle Management

**EquipeMed includes automated user lifecycle management for account expiration and renewal.**

### Quick Reference
- Automated account expiration for residents and students
- Simple activity tracking and status management
- Self-service renewal workflows with administrative approval
- Management commands for daily automation and reporting
- Email notifications for expiration warnings

### Key Commands

```bash
docker compose exec eqmd python manage.py check_user_expiration --dry-run
docker compose exec eqmd python manage.py send_expiration_notifications
docker compose exec eqmd python manage.py extend_user_access username --days 90 --reason "reason"
docker compose exec eqmd python manage.py bulk_user_operations set-expiration --role resident --months 12
docker compose exec eqmd python manage.py lifecycle_report --output-file report.csv
```

**📖 Detailed documentation**: 
- [docs/security/user-lifecycle-management.md](docs/security/user-lifecycle-management.md) - Complete system overview
- [docs/security/user-lifecycle-admin-setup.md](docs/security/user-lifecycle-admin-setup.md) - Admin configuration guide
- [docs/security/user-lifecycle-cronjobs.md](docs/security/user-lifecycle-cronjobs.md) - Automated scheduling setup

## App Details

### Core Apps Overview

- **patients**: Patient management, tagging, status tracking, internal transfer system
- **events**: Base event system, timeline architecture, 24h edit window
- **dailynotes**: Medical evolution notes, duplicate functionality, performance optimizations
- **sample_content**: Template content management, superuser-only editing
- **mediafiles**: Secure file management, photos/videos, FilePond integration
- **pdf_forms**: Hospital forms with coordinate-based positioning

**📖 Detailed documentation**:
- [docs/apps/patients.md](docs/apps/patients.md) - Complete patient management guide
- [docs/apps/events.md](docs/apps/events.md) - Timeline architecture and event system
- [docs/apps/dailynotes.md](docs/apps/dailynotes.md) - Daily notes features and optimizations
- [docs/apps/mediafiles.md](docs/apps/mediafiles.md) - Complete media implementation
- [docs/apps/pdf-forms.md](docs/apps/pdf-forms.md) - PDF forms implementation


## Permission System

**Role-based access control with medical/administrative separation**

### Key Principle
**Medical staff manage patients, administrative staff manage users.**

### Role Types
- **Medical**: Doctors/Residents, Nurses, Physiotherapists, Students
- **Administrative**: Superuser, User Managers

### Core Functions
```python
can_access_patient(user, patient)           # Always True (universal access)
can_edit_event(user, event)                 # 24h time window
can_change_patient_status(user, patient, status)  # Doctors/residents only
````

### Key Commands

```bash
uv run python manage.py setup_groups
uv run python manage.py permission_audit --action=report
```

**📖 Detailed documentation**: See existing [docs/permissions/](docs/permissions/) directory

## Hospital Configuration

**Environment-based single hospital setup**

### Environment Variables

```bash
HOSPITAL_NAME="Your Hospital Name"
HOSPITAL_ADDRESS="123 Medical Center Drive"
HOSPITAL_PHONE="+1-555-123-4567"
HOSPITAL_EMAIL="info@yourhospital.com"
HOSPITAL_LOGO_PATH="static/images/hospital-logo.png"
```

### Template Tags

```django
{% load hospital_tags %}
{% hospital_name %}
{% hospital_header %}
```

**📖 Detailed documentation**: See [docs/deployment/hospital-configuration.md](docs/deployment/hospital-configuration.md)

## Template Development Guidelines

**Critical Rule**: ALL content must be within template blocks when extending templates.

### Event Card Structure

Event card templates extend `event_card_base.html` with blocks:

- `{% block event_actions %}` - Buttons
- `{% block event_content %}` - Main content
- `{% block extra_css %}` - CSS
- `{% block extra_js %}` - JavaScript

**📖 Detailed documentation**: See [docs/development/template-guidelines.md](docs/development/template-guidelines.md)

# important-instruction-reminders

Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (\*.md) or README files. Only create documentation files if explicitly requested by the User.

