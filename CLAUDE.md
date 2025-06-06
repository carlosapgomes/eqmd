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

# Run single test file
pytest apps/accounts/tests/test_models.py

# Run tests without coverage
pytest --no-cov
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

## Project Architecture

**EquipeMed** is a Django 5-based medical team collaboration platform for tracking patients across multiple hospitals.

### App Structure
- **apps/core**: Main application with landing page and dashboard
- **apps/accounts**: User management with custom user model and profiles
- **config/**: Django project configuration directory
- **assets/**: Webpack-managed frontend assets (SCSS, JS)
- **static/**: Compiled static files

### Key Models
- **EqmdCustomUser**: Custom user model with medical profession fields (Medical Doctor, Resident, Nurse, Physiotherapist, Student)
- **UserProfile**: Separate profile model with UUID-based public IDs for security

### Authentication
- Uses django-allauth for email-based authentication
- Custom user model at `accounts.EqmdCustomUser`
- Profile URLs use UUIDs instead of primary keys

### Frontend
- Bootstrap 5.3 with Bootstrap Icons
- Webpack build pipeline compiling SASS/SCSS
- Portuguese (pt-br) localization

### Testing
- pytest with django integration
- Coverage reporting (HTML and terminal)
- factory-boy for test data generation
- Uses `config.test_settings` for test configuration

### Security Notes
- Environment variables for sensitive configuration
- UUID-based public profile identifiers
- CSRF protection enabled
- Debug mode controlled via environment