# Project Context

## Purpose

**EquipeMed** is a Django 5 medical team collaboration platform designed for single-hospital patient tracking and care management. It enables medical staff (doctors, residents, nurses, physiotherapists, students) to collaboratively manage patient care through:

- Patient admission and status tracking
- Daily evolution notes and medical events
- Secure media file management (photos/videos)
- Hospital-specific PDF form generation
- Role-based access control for medical professionals
- Comprehensive audit history and security monitoring
- User lifecycle management with automated account expiration

The platform emphasizes simplicity, security, and compliance with medical record-keeping requirements while providing a modern, responsive interface.

## Tech Stack

### Backend

- **Django 5.2.1** - Web framework
- **Python 3.12+** - Programming language
- **PostgreSQL** - Production database (SQLite for development)
- **django-allauth 0.57.0** - Authentication (email-based login)
- **django-simple-history 3.10.1** - Model change tracking and audit trails
- **django-taggit 6.1.0** - Patient tagging system
- **ReportLab 4.4.2** - PDF generation for medical forms
- **PyPDF 5.8.0** - PDF manipulation
- **Pillow 11.2.1** - Image processing
- **ffmpeg-python 0.2.0** - Video processing
- **firebase-admin 7.1.0** - Data import from Firebase
- **gunicorn 23.0.0** - WSGI HTTP server (production)

### Frontend

- **Bootstrap 5.3.6** - UI framework (user-facing only, NOT for admin)
- **Webpack 5** - Asset bundling and build system
- **JavaScript ES6+** - Client-side scripting
- **Sass** - CSS preprocessing
- **EasyMDE 2.20.0** - Markdown editor
- **FilePond** - File upload handling
- **heic2any 0.0.4** - HEIC image conversion
- **browser-image-compression 2.0.2** - Client-side image optimization

### Testing

- **pytest 8.3.5** - Primary test framework
- **pytest-django 4.11.1** - Django integration for pytest
- **pytest-cov 6.1.1** - Coverage reporting
- **factory-boy 3.3.3** - Test data generation
- **Django test runner** - Alternative for specific app tests
- **Coverage 7.8.2** - Code coverage analysis

### Deployment

- **Docker & Docker Compose** - Containerization
- **GitHub Container Registry / Docker Hub** - Container registry
- **Nginx** - Reverse proxy
- **uv** - Python package and environment manager

## Project Conventions

### Code Style

#### Python (Django)

- **PEP 8** compliant
- **Django conventions** for app structure and naming
- **Model naming**: Singular (e.g., `Patient`, `Event`, `DailyNote`)
- **View naming**: Descriptive function/class names (e.g., `patient_detail`, `PatientCreateView`)
- **URL patterns**: Lowercase with hyphens (e.g., `patient-create`, `event-edit`)
- **Manager methods**: Use custom managers for complex queries (e.g., `Patient.objects.active()`)
- **UUID primary keys**: All models use UUIDs instead of auto-increment IDs for security

#### JavaScript

- **ES6+ syntax** preferred
- **Vanilla JavaScript** for admin interface (NO Bootstrap JS)
- **Bootstrap JavaScript** allowed for user-facing templates only
- **Module pattern** for organization
- **Clear function naming**: Descriptive and action-oriented

#### CSS/SCSS

- **BEM methodology** where appropriate
- **Bootstrap utilities** first, custom CSS second
- **Separate files** per feature/component in `assets/scss/`
- **Never edit** `static/` directly - always edit `assets/` and rebuild with Webpack

### Architecture Patterns

#### App Structure

- **Small, focused apps**: Each app handles a specific domain (patients, events, dailynotes)
- **Base models with inheritance**: `Event` base model extended by `DailyNote`, `SimpleNote`, etc.
- **Manager pattern**: Custom managers for complex queries and business logic
- **Service layer**: Complex business logic in separate service modules (e.g., `services/` directories)
- **Template inheritance**: Base templates with blocks for consistent UI

#### Key Patterns

- **Event-based timeline**: All medical records inherit from `Event` base model with:
  - UUID primary key
  - Audit trail (created_at, updated_at, created_by, updated_by)
  - 24-hour edit window enforcement
  - Patient relationship
- **Permission system**: Simple role-based with `core.permissions` module:
  - Universal patient access (all staff can view all patients)
  - Role-specific actions (discharge, edit personal data)
  - Time-window validation for event editing
- **Hospital configuration**: Environment-based single hospital setup via template tags
- **Audit history**: Comprehensive change tracking using django-simple-history
- **User lifecycle**: Automated expiration and renewal workflows for temporary staff

#### Database Design

- **UUID primary keys** for security
- **Audit fields** on all models (created_at, updated_at, created_by, updated_by)
- **Soft deletes** where appropriate
- **History tables** for all critical models
- **Indexed foreign keys** for performance

### Testing Strategy

#### Test Organization

- **Per-app test directories**: Each app has `tests/` directory with separate files
- **Factory pattern**: factory-boy for test data generation
- **pytest preferred**: Use pytest for most tests (faster, better features, coverage)
- **Django test runner**: Use for apps with specific Django test requirements

#### Test Types

- **Unit tests**: Model methods, utility functions, business logic
- **Integration tests**: View tests with database interactions
- **Permission tests**: Role-based access control validation
- **Form tests**: Form validation and data processing
- **Template tests**: Template rendering and context

#### Running Tests

```bash
# Pytest (recommended)
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest

# Django test runner (for specific apps)
uv run python manage.py test apps.patients.tests

# Coverage reports
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest --cov=apps --cov-report=html
```

#### Test Requirements

- **All new features** must have tests
- **Coverage goal**: 80%+ for new code
- **Test both success and failure paths**
- **Test permissions** for all protected views
- **Test edge cases** (empty data, invalid input, boundary conditions)

### Git Workflow

#### Branching Strategy

- **master**: Production-ready code
- **dev**: Development branch (primary working branch)
- **feature/***: Feature branches from dev
- **fix/***: Bug fix branches from dev
- **hotfix/***: Emergency fixes from master

#### Commit Conventions

- **Descriptive messages**: Clear, concise, action-oriented
- **Type prefixes**: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`
- **Examples**:
  - `feat(patients): add bulk patient import functionality`
  - `fix(dailynotes): resolve duplicate note creation bug`
  - `docs: update deployment guide for registry setup`
  - `refactor(events): extract timeline logic to service layer`
  - `test(permissions): add admission edit permission tests`

#### Workflow

1. Create feature branch from `dev`
2. Make changes with descriptive commits
3. Run tests locally
4. Push and create pull request to `dev`
5. After review and merge to `dev`, periodically merge `dev` to `master`

## Domain Context

### Medical Terminology

- **Admission**: Patient entry into hospital care
- **Evolution**: Daily progress note documenting patient status
- **Discharge**: Patient release from hospital
- **Ward**: Hospital unit/department
- **Bed**: Physical bed assignment within ward

### Medical Professions & Permissions

- **Doctors/Residents**: Full access including discharge and personal data editing
- **Nurses**: Full patient access, cannot discharge or edit personal data
- **Physiotherapists**: Same as nurses
- **Students**: Same as nurses
- **User Managers**: Administrative staff managing user accounts (not patient access)

### Patient Status Types

- **OUTPATIENT (1)**: Ambulatorial - Patient not currently admitted to hospital (includes discharged and transferred patients)
- **INPATIENT (2)**: Internado - Patient currently admitted to hospital
- **EMERGENCY (3)**: Emergência - Patient in emergency care
- **DISCHARGED (4)**: Alta - Patient discharged from hospital
- **TRANSFERRED (5)**: Transferido - Patient transferred to another facility
- **DECEASED (6)**: Óbito - Patient deceased

### Event System

- **24-hour edit window**: Medical events can only be edited within 24 hours of creation
- **Audit trail**: All changes tracked with user and timestamp
- **Timeline view**: Chronological display of all patient events

### User Lifecycle

- **Expiration dates**: Residents and students have account expiration dates
- **Activity tracking**: Login and action timestamps for lifecycle management
- **Renewal workflows**: Self-service renewal requests with admin approval
- **Automated notifications**: Email warnings before expiration

## Important Constraints

### Security & Compliance

- **CSRF protection**: All forms require CSRF tokens
- **UUID identifiers**: No sequential IDs exposed in URLs
- **Audit history**: All changes tracked for medical record compliance
- **User activity monitoring**: Security event detection and alerts
- **Permission enforcement**: All views check user permissions
- **Email-based authentication**: django-allauth with email confirmation

### Business Rules

- **Single hospital**: System designed for one hospital instance
- **Universal patient access**: All medical staff can view all patients
- **24-hour edit window**: Events locked after 24 hours
- **Status-based workflow**: Patient status affects available actions
- **Account expiration**: Temporary staff (residents/students) have expiration dates

### Technical Constraints

- **Python 3.12+** required
- **PostgreSQL** for production (no other databases supported)
- **Environment variables** for all configuration (no hardcoded secrets)
- **Docker deployment** strongly recommended
- **Webpack build** required for frontend changes
- **Browser compatibility**: Modern browsers only (ES6+ support required)

### Frontend Constraints

- **Bootstrap 5.3 ONLY** for user-facing templates
- **NO Bootstrap** in admin templates (use vanilla JavaScript)
- **Portuguese localization** primary language
- **Mobile responsive** required for all views
- **Webpack assets**: All static files must go through Webpack build

## External Dependencies

### Authentication

- **django-allauth**: Email-based user authentication with verification
- **Email service**: SMTP server for email delivery (configurable)

### File Storage

- **django-storages**: Cloud storage support (optional, local filesystem default)
- **FilePond**: Frontend file upload handling

### Media Processing

- **FFmpeg**: Video transcoding and thumbnail generation (system-level dependency)
- **Pillow**: Image processing and thumbnail generation

### Data Import

- **Firebase Admin SDK**: Import historical data from Firebase Realtime Database
- **Firebase credentials**: JSON key file for authentication

### PDF Generation

- **ReportLab**: Dynamic PDF form generation with coordinate-based field positioning
- **pdf2image**: PDF preview rendering

### Monitoring & Logging

- **Django logging**: Configured for security events and errors
- **Security alerts**: Custom management commands for suspicious activity detection

### Container Registry

- **GitHub Container Registry** (primary): `ghcr.io/carlosapgomes/eqmd`
- **Docker Hub** (alternative): `carlosapgomes/eqmd`

### Deployment

- **Nginx**: Reverse proxy for production deployments
- **Docker Compose**: Multi-container orchestration
- **System dependencies**: FFmpeg, poppler-utils (for pdf2image)
