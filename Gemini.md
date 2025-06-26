# Gemini Project Guide: EquipeMed

This document provides a summary of conventions, architecture, and important commands for the EquipeMed project, based on the files in the `docs/` directory.

## 1. Project Overview

EquipeMed is a medical collaboration platform for healthcare professionals to manage patient records securely. Key features include patient management, event tracking (daily notes, photos, etc.), role-based permissions, and hospital context management.

## 2. Tech Stack

- **Backend**: Django
- **Frontend**: Bootstrap 5.3.6, Sass/SCSS, Webpack
- **Testing**: Pytest, pytest-django, factory-boy, faker
- **Package Management**: uv

## 3. Development Workflow & Commands

### Database and Migrations

- **To completely reset the database (development only):**
  1. `find . -path "*/migrations/*.py" -not -name "__init__.py" -delete`
  2. `find . -path "*/migrations/*.pyc" -delete`
  3. `rm db.sqlite3`
  4. `python manage.py makemigrations`
  5. `python manage.py migrate`

### Initial Data Setup

- **Set up permission groups (CRITICAL):**

  ```bash
  python manage.py setup_groups
  ```

- **Populate with realistic sample data for testing:**

  ```bash
  python manage.py populate_sample_data
  ```

  - Use `--dry-run` to preview.
  - Use `--clear-existing` to start fresh.
  - **Password for all sample users is `samplepass123`**.
- **Create sample content templates:**

  ```bash
  python manage.py create_sample_content
  ```

## 4. Testing

- **Framework**: `pytest` with `pytest-django`, `pytest-cov`, `factory-boy`, and `faker`.
- **Configuration**: See `pytest.ini` and `.coveragerc`. Test-specific settings are in `config/test_settings.py`.
- **Running Tests**:
  - **Recommended**: `uv run pytest`
  - **With coverage**: `uv run pytest --cov=apps --cov-report=html`
  - **Alternative**: `uv run python manage.py test --settings=config.test_settings`
- **Structure**: Tests are located in `apps/<app_name>/tests/`. Factories for test data are in `apps/<app_name>/tests/factories.py`.
- **Coverage**: The goal is 80%+ coverage. The HTML report is generated in `htmlcov/`.

## 5. Permissions System

The permission system is a core part of the application, enforcing access control based on user roles, hospital context, and time limits.

- **Architecture**:

  - **Role-Based Access Control (RBAC)**: Permissions are assigned to groups based on user profession.
  - **Hospital Context**: A user's access to admitted patients is restricted to their currently selected hospital, which is managed via `HospitalContextMiddleware` and stored in the session.
  - **Object-Level Permissions**: A custom backend (`EquipeMedPermissionBackend`) handles fine-grained permissions on individual objects (e.g., a specific patient or event).
  - **Time-Based Rules**: Editing/deleting medical events is restricted to a 24-hour window for the creator.

- **User Roles & Key Permissions**:

  - **Medical Doctors**: Full access. The only role that can discharge patients and edit patient personal data.
  - **Residents/Physiotherapists**: Full access to patients within their current hospital context, but cannot discharge.
  - **Nurses**: Similar to Residents, but cannot delete patients. Can admit emergency patients to inpatient status.
  - **Students**: View-only access, restricted to outpatients.

- **Key Code**:
  - **Utilities**: `apps/core/permissions/utils.py` (e.g., `can_access_patient`, `can_edit_event`).
  - **Decorators**: `apps/core/permissions/decorators.py` (e.g., `@patient_access_required`, `@doctor_required`).
  - **Template Tags**: `apps/core/templatetags/permission_tags.py`.

## 6. Styling & Frontend

- **Framework**: A custom Bootstrap 5.3.6 theme is used. See `assets/scss/main.scss`.
- **Color Palette**: A professional, medical-focused color palette is defined (primary: `$medical-deep-blue: #1e3a8a`).
- **Custom Components**:
  - Use specific classes like `.card-medical`, `.timeline-card`, `.navbar-medical`, and `.form-medical` for consistent styling.
- **Forms**: Forms are rendered manually using Bootstrap's HTML structure for full control. No form-rendering libraries are used.
- **Printing**: The project uses an **HTML + browser print** strategy, not server-side PDF generation. Print-specific views and templates (e.g., `dailynote_print.html`) provide a professional, medical-grade document format.

## 7. MediaFiles App

- **Purpose**: Manages secure uploads, storage, and access for medical images and videos.
- **Architecture**:
  - A central `MediaFile` model stores file metadata.
  - `Photo`, `PhotoSeries`, and `VideoClip` models inherit from the base `Event` model and link to `MediaFile`.
- **Security**:
  - **Filenames**: Uses UUIDs for filenames to prevent enumeration. Original filenames are stored in the DB.
  - **Paths**: File paths do not contain any patient information.
  - **Access**: All files are served via Django views that enforce permissions. There is no direct web access to the media directory.
- **Storage Structure**: `media/{photos|photo_series|videos}/{YYYY}/{MM}/{originals|large|medium|thumbnails}/{uuid}.{ext}`.

## 8. API

- **Authentication**: All endpoints require token authentication (`Authorization: Token <your-token>`).
- **Endpoints**: The API provides endpoints for managing patients, hospital records, and tags. Refer to `docs/patients/api.md` for details.
