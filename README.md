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

### Production Deployment (Registry-based)

**Minimal deployment (recommended):**

```bash
# Download deployment files
wget https://raw.githubusercontent.com/carlosapgomes/eqmd/master/docker-compose.yml
wget https://raw.githubusercontent.com/carlosapgomes/eqmd/master/install-minimal.sh
wget https://raw.githubusercontent.com/carlosapgomes/eqmd/master/create_eqmd_user.sh
chmod +x install-minimal.sh create_eqmd_user.sh

# Deploy
sudo ./install-minimal.sh
```

**Full customization:**

```bash
# Clone repository for customization
git clone https://github.com/carlosapgomes/eqmd.git
cd eqmd
sudo ./install.sh
```

### Development Setup

**Local development with Docker:**

```bash
git clone https://github.com/carlosapgomes/eqmd.git
cd eqmd

# Set up development environment
cp .env.example .env.dev
docker compose --profile dev up -d eqmd-dev

# Access at http://localhost:8779
```

**Local development without Docker:**

```bash
git clone https://github.com/carlosapgomes/eqmd.git
cd eqmd
uv install

# Database setup
uv run python manage.py migrate
uv run python manage.py createsuperuser

# Sample data (optional)
uv run python manage.py create_sample_tags
uv run python manage.py create_sample_content

# Run development server
uv run python manage.py runserver
```

## First Time Setup

After creating a superuser:

1. Log in to admin at `/admin/`
2. Create user groups: `uv run python manage.py setup_groups`
3. Assign users to appropriate professional groups
4. Configure hospital information via environment variables
5. Create patients and start using the system

## Container Images

EquipeMed uses a registry-based deployment with pre-built Docker images:

**GitHub Container Registry:**

- **Latest**: `ghcr.io/carlosapgomes/eqmd:latest`
- **Development**: `ghcr.io/carlosapgomes/eqmd:dev`
- **Specific versions**: `ghcr.io/carlosapgomes/eqmd:v1.0.0`

**Docker Hub Alternative:**

- **Latest**: `carlosapgomes/eqmd:latest`
- **Development**: `carlosapgomes/eqmd:dev`

## Environment Configuration

### Production Settings

```bash
# Basic Django settings
SECRET_KEY=your-production-secret-key
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Registry configuration
REGISTRY=ghcr.io
REGISTRY_USER=your-github-username
EQMD_IMAGE=ghcr.io/carlosapgomes/eqmd:latest

# User configuration (handled by create_eqmd_user.sh)
EQMD_UID=1001
EQMD_GID=1001

# Hospital Configuration
HOSPITAL_NAME="Your Hospital Name"
HOSPITAL_ADDRESS="123 Medical Center Drive, City, State 12345"
HOSPITAL_PHONE="+1-555-123-4567"
HOSPITAL_EMAIL="info@yourhospital.com"
HOSPITAL_PDF_FORMS_ENABLED=true
```

### Development Settings

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

## Documentation

### Deployment Guides

- **[Registry Setup](docs/deployment/registry-setup.md)** - Container registry configuration
- **[User Management](docs/deployment/user-management.md)** - UID conflict resolution
- **[Rollback Procedures](docs/deployment/rollback-procedures.md)** - Emergency rollback guide
- **[Docker Development](docs/development/docker-development.md)** - Development with Docker

### Operation Guides

- **[Production Deployment](docs/deployment/docker-production-deployment.md)** - Complete production setup
- **[Nginx Configuration](nginx.conf.example)** - Reverse proxy setup
- **[Upgrade Procedures](upgrade.sh)** - Automated upgrade script

## Production Deployment

### Quick Registry Deployment

**Features:**

- ✅ Uses pre-built container images from registry
- ✅ Automated user creation with UID conflict resolution
- ✅ Named volumes for optimized static file serving
- ✅ Health checks and automated rollback capability
- ✅ Sub-minute deployment time
- ✅ No repository cloning required

### Production Checklist

- [ ] Configure `.env` with production settings
- [ ] Set up container registry authentication
- [ ] Create eqmd system user (`./create_eqmd_user.sh`)
- [ ] Deploy application (`./install.sh`)
- [ ] Configure nginx reverse proxy (see `nginx.conf.example`)
- [ ] Set up SSL certificate
- [ ] Run security checks
- [ ] Create user groups and permissions
- [ ] Configure hospital information
- [ ] Set up monitoring and backups

## Permission System

EquipeMed uses a simple role-based permission system:

- **Universal Patient Access**: All medical staff can access all patients
- **Role-Based Actions**: Different permissions for discharge and personal data editing
- **Time-Limited Editing**: 24-hour window for editing medical events
- **Status-Based Logic**: Patient status affects available actions

## Support

For setup assistance or feature requests, please check the project documentation in `CLAUDE.md` or create an issue.

## Development Acknowledgments

This project was developed with the assistance of Large Language Model (LLM) coding assistants, including Gemini by Google and Claude by Anthropic. LLM tools were used to help with code generation, architecture design, documentation, and problem-solving throughout the development process.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

