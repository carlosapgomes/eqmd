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

# Firebase Data Import

## Import Dailynotes from Firebase

Import dailynotes from Firebase Realtime Database to EQMD. Requires `firebase-admin` package (already installed).

### Prerequisites
1. Firebase service account credentials JSON file
2. Patients already imported (command matches using `PatientRecordNumber.record_number`)
3. Valid user account for import attribution

### Basic Usage

```bash
# Dry run to preview import
uv run python manage.py import_firebase_dailynotes \
  --credentials-file /path/to/firebase-key.json \
  --database-url https://your-project.firebaseio.com \
  --project-name your-project \
  --dry-run

# Import with specific user
uv run python manage.py import_firebase_dailynotes \
  --credentials-file /path/to/firebase-key.json \
  --database-url https://your-project.firebaseio.com \
  --project-name your-project \
  --user-email admin@yourcompany.com

# Test import with limited records
uv run python manage.py import_firebase_dailynotes \
  --credentials-file /path/to/firebase-key.json \
  --database-url https://your-project.firebaseio.com \
  --project-name your-project \
  --limit 10
```

### Docker Usage

#### Docker Compose

**Option 1: Temporary Mount (Recommended - Most Secure)**
```bash
# Mount as read-only temporary volume (auto-cleanup)
docker-compose run --rm \
  -v /path/to/firebase-key.json:/tmp/firebase-key.json:ro \
  web uv run python manage.py import_firebase_dailynotes \
    --credentials-file /tmp/firebase-key.json \
    --database-url https://your-project.firebaseio.com \
    --project-name your-project \
    --user-email admin@yourcompany.com
```

**Option 2: Copy with Cleanup**
```bash
# Copy, run, and remove in one command
docker-compose cp firebase-key.json web:/app/firebase-key.json && \
docker-compose exec web uv run python manage.py import_firebase_dailynotes \
  --credentials-file firebase-key.json \
  --database-url https://your-project.firebaseio.com \
  --project-name your-project \
  --user-email admin@yourcompany.com && \
docker-compose exec web rm /app/firebase-key.json
```

**Option 3: Manual Copy with Shell Cleanup**
```bash
# Copy credentials
docker-compose cp firebase-key.json web:/app/firebase-key.json

# Run with cleanup in single command
docker-compose exec web bash -c "
  uv run python manage.py import_firebase_dailynotes \
    --credentials-file firebase-key.json \
    --database-url https://your-project.firebaseio.com \
    --project-name your-project \
    --user-email admin@yourcompany.com && \
  rm firebase-key.json
"
```

#### Standalone Docker

**Secure Mount (Recommended)**
```bash
# Mount credentials as read-only volume (auto-cleanup)
docker run --rm -it \
  -v /path/to/firebase-key.json:/tmp/firebase-key.json:ro \
  -v /path/to/db:/app/db \
  your-eqmd-image \
  uv run python manage.py import_firebase_dailynotes \
    --credentials-file /tmp/firebase-key.json \
    --database-url https://your-project.firebaseio.com \
    --project-name your-project \
    --user-email admin@yourcompany.com
```

#### Production Docker (Using Secrets)

**Docker Swarm Secrets**
```bash
# Create secret from credentials file
echo "$(cat firebase-key.json)" | docker secret create firebase-creds -

# Run service with secret (auto-cleanup)
docker service create --rm \
  --secret firebase-creds \
  --mount type=tmpfs,destination=/tmp \
  your-eqmd-image sh -c "
    cp /run/secrets/firebase-creds /tmp/firebase-key.json && \
    uv run python manage.py import_firebase_dailynotes \
      --credentials-file /tmp/firebase-key.json \
      --database-url https://your-project.firebaseio.com \
      --project-name your-project \
      --user-email admin@yourcompany.com
  "

# Clean up secret after use
docker secret rm firebase-creds
```

**Kubernetes Secrets**
```bash
# Create secret
kubectl create secret generic firebase-creds \
  --from-file=firebase-key.json

# Run job with secret mount
kubectl run firebase-import --rm -i --restart=Never \
  --image=your-eqmd-image \
  --overrides='{
    "spec": {
      "containers": [{
        "name": "firebase-import",
        "image": "your-eqmd-image",
        "command": ["uv", "run", "python", "manage.py", "import_firebase_dailynotes"],
        "args": [
          "--credentials-file", "/tmp/firebase-key.json",
          "--database-url", "https://your-project.firebaseio.com",
          "--project-name", "your-project",
          "--user-email", "admin@yourcompany.com"
        ],
        "volumeMounts": [{
          "name": "firebase-creds",
          "mountPath": "/tmp",
          "readOnly": true
        }]
      }],
      "volumes": [{
        "name": "firebase-creds",
        "secret": {
          "secretName": "firebase-creds",
          "items": [{"key": "firebase-key.json", "path": "firebase-key.json"}]
        }
      }]
    }
  }'

# Clean up secret
kubectl delete secret firebase-creds
```

### Command Options

- `--credentials-file`: Firebase service account JSON (required)
- `--database-url`: Firebase Realtime Database URL (required)
- `--project-name`: Firebase project name (required)  
- `--base-reference`: Database reference path (default: "dailynotes")
- `--user-email`: User email for import attribution (uses first superuser if not provided)
- `--dry-run`: Preview without importing
- `--limit`: Import only N records (useful for testing)

### Security Best Practices

**Credential Handling Priority:**
1. **🥇 Temporary Mounts** - Credentials never persist in container (Options 1)
2. **🥈 Docker Secrets** - Enterprise-grade secret management (Production)
3. **🥉 Copy with Cleanup** - Manual cleanup required (Options 2-3)

**Environment Recommendations:**
- **Development**: Use temporary mount (Option 1)
- **CI/CD Pipelines**: Use Docker/Kubernetes secrets
- **Production**: Always use secrets management systems
- **Quick Testing**: Copy with cleanup (Option 2)

### Notes

- Matches patients using Firebase `patient` field against `PatientRecordNumber.record_number`
- Converts epoch milliseconds timestamps to Django datetime
- Formats content as: Subjective → Objective → Exams → Assessment/Plan
- Allows duplicate imports (creates additional dailynotes)
- Provides detailed reporting of unmatched patients and errors
- **Security**: Always use read-only mounts and clean up credentials after import

# Security monitoring and audit history

uv run python manage.py detect_suspicious_activity --comprehensive --days=7
uv run python manage.py security_alert_monitor --continuous --critical-only
uv run python manage.py security_report --days=30 --format=json --output=report.json

````

## Project Architecture

**EquipeMed** - Django 5 medical team collaboration platform for single-hospital patient tracking and care management.

### Apps Overview

- **core**: Dashboard, permissions, landing page, hospital configuration
- **accounts**: Custom user model with medical professions (Doctor, Resident, Nurse, Physiotherapist, Student)
- **patients**: Patient management with tagging system, status tracking, and internal ward/bed transfer management
- **events**: Base event model for medical records (UUID, audit trail, 24h edit window)
- **dailynotes**: Daily evolution notes extending Event model
- **sample_content**: Template content management for various event types
- **mediafiles**: Secure media file management for medical images and videos
- **pdf_forms**: Hospital-specific PDF form overlay functionality with dynamic form generation

### Key Features

- **Authentication**: django-allauth with email-based login
- **Frontend**: Bootstrap 5.3 (user-facing only), Webpack, Portuguese localization
- **Security**: UUID identifiers, CSRF protection, role-based permissions, comprehensive audit history
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

