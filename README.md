# EquipeMed

A Django 5 medical team collaboration platform for single-hospital patient tracking and care management.

## Features

- **Patient Management**: Complete CRUD operations with status tracking
- **Medical Events**: Comprehensive event system for medical records
- **Daily Notes**: Evolution notes with timeline display and duplicate functionality
- **Media Files**: Secure handling of medical images and videos with FilePond integration
- **Role-Based Permissions**: Access control for medical professionals
- **Tagging System**: Flexible patient categorization with color-coded tags
- **Responsive Design**: Bootstrap 5.3 with mobile support and Portuguese localization
- **Hospital Configuration**: Environment-based single hospital setup

## Medical Professions Supported

- **Doctors**: Full system access including patient discharge and personal data editing
- **Residents**: Full patient access including discharge and personal data editing
- **Nurses**: Full patient access but cannot discharge or edit personal data
- **Physiotherapists**: Full patient access but cannot discharge or edit personal data  
- **Students**: Full patient access but cannot discharge or edit personal data

## Quick Start

### 1. Clone and Setup

```bash
git clone <repository>
cd eqmd
uv install
```

### 2. Database Setup

```bash
uv run python manage.py migrate
uv run python manage.py createsuperuser
```

### 3. Sample Data (Optional)

```bash
uv run python manage.py create_sample_tags
uv run python manage.py create_sample_content
```

### 4. Run Development Server

```bash
uv run python manage.py runserver
```

## First Time Setup

After creating a superuser:

1. Log in to admin at `/admin/`
2. Create user groups: `uv run python manage.py setup_groups`
3. Assign users to appropriate professional groups
4. Configure hospital information via environment variables
5. Create patients and start using the system

## Environment Configuration

### Required Settings

```bash
# Basic Django settings
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (default uses SQLite)
DATABASE_URL=sqlite:///db.sqlite3

# Hospital Configuration
HOSPITAL_NAME="Your Hospital Name"
HOSPITAL_ADDRESS="123 Medical Center Drive, City, State 12345"
HOSPITAL_PHONE="+1-555-123-4567"
HOSPITAL_EMAIL="info@yourhospital.com"
HOSPITAL_WEBSITE="https://www.yourhospital.com"
HOSPITAL_LOGO_PATH="static/images/hospital-logo.png"
```

### Optional Settings

```bash
# Email (for django-allauth)
EMAIL_HOST=smtp.your-provider.com
EMAIL_HOST_USER=your-email@domain.com
EMAIL_HOST_PASSWORD=your-email-password

# Media storage
MEDIA_ROOT=/path/to/media/files
STATIC_ROOT=/path/to/static/files
```

## Development Commands

```bash
# Development
uv run python manage.py runserver
uv run python manage.py migrate
uv run python manage.py makemigrations

# Testing
uv run pytest                                      # All tests with coverage
uv run pytest --no-cov                           # Without coverage
uv run python manage.py test apps.patients.tests # Specific app tests

# Frontend
npm install && npm run build

# User management
uv run python manage.py setup_groups              # Create professional groups
uv run python manage.py user_permissions --action=assign # Assign users to groups

# Sample data
uv run python manage.py create_sample_tags        # Create sample patient tags
uv run python manage.py create_sample_content     # Create sample medical templates
```

## Architecture

### Core Apps

- **core**: Dashboard, permissions, hospital configuration, landing page
- **accounts**: Custom user model with medical professions
- **patients**: Patient management with tagging system and status tracking
- **events**: Base event model for medical records (UUID, audit trail, 24h edit window)
- **dailynotes**: Daily evolution notes extending Event model
- **sample_content**: Template content management for various event types
- **mediafiles**: Secure media file management for medical images and videos

### Key Technologies

- **Backend**: Django 5, Python 3.11+
- **Frontend**: Bootstrap 5.3, Webpack, JavaScript ES6+
- **Database**: SQLite (development), PostgreSQL (production)
- **Authentication**: django-allauth with email-based login
- **Media Processing**: FilePond for video uploads, custom image processing
- **Testing**: pytest + Django test runner, factory-boy

## Production Deployment

### Production Checklist

- [ ] Set `DEBUG=False`
- [ ] Configure production database (PostgreSQL recommended)
- [ ] Set up email backend for notifications
- [ ] Configure static files serving (WhiteNoise or CDN)
- [ ] Set up SSL/HTTPS
- [ ] Run security checks: `uv run python manage.py check --deploy`
- [ ] Create user groups: `uv run python manage.py setup_groups`
- [ ] Configure hospital environment variables

### Environment Variables

```bash
# Production settings
DEBUG=False
SECRET_KEY=your-production-secret-key
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database
DATABASE_URL=postgres://user:password@localhost/eqmd_prod

# Hospital Configuration
HOSPITAL_NAME="Your Hospital Name"
HOSPITAL_ADDRESS="Your Hospital Address"
HOSPITAL_PHONE="Your Hospital Phone"
HOSPITAL_EMAIL="contact@yourhospital.com"
HOSPITAL_WEBSITE="https://www.yourhospital.com"

# Email
EMAIL_HOST=smtp.your-provider.com
EMAIL_HOST_USER=noreply@yourhospital.com
EMAIL_HOST_PASSWORD=your-email-password
```

## Permission System

EquipeMed uses a simple role-based permission system:

- **Universal Patient Access**: All medical staff can access all patients
- **Role-Based Actions**: Different permissions for discharge and personal data editing
- **Time-Limited Editing**: 24-hour window for editing medical events
- **Status-Based Logic**: Patient status affects available actions

## Support

For setup assistance or feature requests, please check the project documentation in `CLAUDE.md` or create an issue.

## Development Acknowledgments

This project was developed with the assistance of Large Language Model (LLM) coding assistants, including Claude by Anthropic. LLM tools were used to help with code generation, architecture design, documentation, and problem-solving throughout the development process.

## License

[Add your license information here]