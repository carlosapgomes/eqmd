# Docker Development Guide

**Complete guide for developing EquipeMed using Docker and registry-based workflow**

## Overview

This guide covers local development using Docker containers, registry-based images, and development workflows that align with the production deployment strategy.

## Development Environment Setup

### Prerequisites

- Docker and Docker Compose installed
- Node.js 18+ (for local asset building)
- Git configured
- Text editor or IDE

### Quick Start

```bash
# Clone repository
git clone https://github.com/yourorg/eqmd.git
cd eqmd

# Set up environment
cp .env.example .env.dev
# Edit .env.dev with your development settings

# Create development user (optional, for consistency)
./create_eqmd_user.sh

# Start development environment
docker compose --profile dev up -d eqmd-dev

# Access application
open http://localhost:8779
```

## Development Modes

### Mode 1: Full Development (Hot Reload)

**Best for:** Active development with code changes

```bash
# Start with hot reload
docker compose --profile dev up eqmd-dev

# Features:
# - Code changes reload automatically
# - Debug mode enabled
# - Local volumes for real-time editing
# - Development database
```

**Configuration:**
```yaml
# docker-compose.yml (dev profile)
eqmd-dev:
  build:
    context: .
    args:
      USER_ID: ${EQMD_UID:-1001}
      GROUP_ID: ${EQMD_GID:-1001}
  command: >
    sh -c "python manage.py migrate &&
           python manage.py collectstatic --noinput &&
           python manage.py runserver 0.0.0.0:8000"
  volumes:
    - .:/app  # Live code mounting
    - ./media:/app/media
  ports:
    - "8779:8000"
  environment:
    - DEBUG=True
```

### Mode 2: Production Simulation

**Best for:** Testing production-like deployment locally

```bash
# Use production image locally
export EQMD_IMAGE=ghcr.io/yourorg/eqmd:dev
docker compose up -d eqmd

# Features:
# - Uses registry image
# - Production-like configuration
# - Named volumes for static files
# - Gunicorn server
```

### Mode 3: Registry Development

**Best for:** Testing registry workflow and CI/CD integration

```bash
# Build and push to development registry
docker build -t ghcr.io/yourorg/eqmd:dev .
docker push ghcr.io/yourorg/eqmd:dev

# Pull and run locally
export EQMD_IMAGE=ghcr.io/yourorg/eqmd:dev
docker compose up -d eqmd
```

## Local Development Workflow

### Daily Development Process

```bash
# 1. Start development environment
docker compose --profile dev up -d eqmd-dev

# 2. Make code changes (auto-reloads)
# Edit files in your IDE

# 3. Run tests
docker compose exec eqmd-dev python manage.py test

# 4. Check migrations
docker compose exec eqmd-dev python manage.py makemigrations
docker compose exec eqmd-dev python manage.py migrate

# 5. Build frontend assets (if changed)
npm run build
docker compose restart eqmd-dev  # Reload static files

# 6. Stop when done
docker compose --profile dev down
```

### Frontend Development

#### Asset Building

```bash
# Install frontend dependencies
npm install

# Development build (watch mode)
npm run dev

# Production build
npm run build

# In separate terminal, restart container to reload assets
docker compose restart eqmd-dev
```

#### Hot Module Replacement (HMR)

For advanced frontend development:

```bash
# Start webpack dev server
npm run dev-server  # Runs on port 8080

# Configure Django to use webpack-dev-server for assets
# Add to .env.dev:
WEBPACK_DEV_SERVER=true
```

### Database Development

#### Local Database Management

```bash
# Reset database
docker compose exec eqmd-dev python manage.py flush

# Create migrations
docker compose exec eqmd-dev python manage.py makemigrations

# Apply migrations
docker compose exec eqmd-dev python manage.py migrate

# Create superuser
docker compose exec eqmd-dev python manage.py createsuperuser

# Load sample data
docker compose exec eqmd-dev python manage.py create_sample_tags
docker compose exec eqmd-dev python manage.py create_sample_wards
docker compose exec eqmd-dev python manage.py create_sample_content
```

#### Database Backup/Restore

```bash
# Backup development database
docker compose exec eqmd-dev python manage.py dumpdata > dev_backup.json

# Restore from backup
docker compose exec eqmd-dev python manage.py loaddata dev_backup.json
```

## Testing in Development

### Running Tests

```bash
# All tests
docker compose exec eqmd-dev python manage.py test

# Specific app tests
docker compose exec eqmd-dev python manage.py test apps.patients

# With coverage
docker compose exec eqmd-dev coverage run --source='.' manage.py test
docker compose exec eqmd-dev coverage html

# Using pytest
docker compose exec eqmd-dev pytest apps/patients/tests/
```

### Test Database

Development uses a separate test database:

```python
# settings/dev.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db_dev.sqlite3',
    }
}

# Test database is automatically created/destroyed
```

## Registry Integration for Development

### Using Development Registry

```bash
# Set up development registry authentication
export REGISTRY="ghcr.io"
export REGISTRY_USER="your-github-username"
export REGISTRY_TOKEN="your-github-token"

# Login to registry
echo $REGISTRY_TOKEN | docker login $REGISTRY -u $REGISTRY_USER --password-stdin
```

### Development Image Workflow

```bash
#!/bin/bash
# dev-build-push.sh

# Build development image
docker build -t eqmd:dev-local .

# Tag for registry
docker tag eqmd:dev-local ghcr.io/yourorg/eqmd:dev-$(git rev-parse --short HEAD)
docker tag eqmd:dev-local ghcr.io/yourorg/eqmd:dev

# Push to registry
docker push ghcr.io/yourorg/eqmd:dev-$(git rev-parse --short HEAD)
docker push ghcr.io/yourorg/eqmd:dev

echo "✅ Development image pushed"
echo "🐳 Image: ghcr.io/yourorg/eqmd:dev-$(git rev-parse --short HEAD)"
```

### Pull Development Images

```bash
# Pull latest development image
docker pull ghcr.io/yourorg/eqmd:dev

# Use in local environment
export EQMD_IMAGE=ghcr.io/yourorg/eqmd:dev
docker compose up -d eqmd

# Test production-like behavior locally
curl http://localhost:8778/health/
```

## Development Tools Integration

### IDE Configuration

#### VS Code

`.vscode/settings.json`:
```json
{
    "python.defaultInterpreterPath": "docker compose exec eqmd-dev python",
    "python.terminal.activateEnvironment": false,
    "docker.commands.attach": [
        {
            "label": "Attach to Django Dev",
            "command": "docker compose exec eqmd-dev /bin/bash"
        }
    ]
}
```

`.vscode/tasks.json`:
```json
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "Django: Run Tests",
            "type": "shell",
            "command": "docker compose exec eqmd-dev python manage.py test",
            "group": "test",
            "presentation": {
                "echo": true,
                "reveal": "always"
            }
        },
        {
            "label": "Django: Make Migrations",
            "type": "shell",
            "command": "docker compose exec eqmd-dev python manage.py makemigrations",
            "group": "build"
        }
    ]
}
```

### Debugging

#### Django Debug Toolbar

Add to development requirements:
```python
# requirements/dev.txt
django-debug-toolbar
```

Enable in settings:
```python
# settings/dev.py
if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
    
    INTERNAL_IPS = ['127.0.0.1', '172.16.0.0/12']  # Docker networks
```

#### Remote Debugging

For breakpoint debugging:
```python
# Install in development image
pip install debugpy

# Add to code where you want breakpoint
import debugpy
debugpy.listen(5678)
debugpy.wait_for_client()
```

Docker compose configuration:
```yaml
eqmd-dev:
  ports:
    - "8779:8000"
    - "5678:5678"  # Debug port
```

## Performance Development

### Static Files Optimization

```bash
# Optimize static files during development
docker compose exec eqmd-dev python manage.py collectstatic --noinput

# Test static file serving
curl -I http://localhost:8779/static/css/app.css

# Check file sizes
docker compose exec eqmd-dev find /app/staticfiles -name "*.css" -exec wc -c {} +
```

### Database Performance

```bash
# Enable query debugging
# Add to .env.dev
DEBUG_QUERIES=True

# Check slow queries
docker compose exec eqmd-dev python manage.py shell
>>> from django.db import connection
>>> connection.queries
```

## Environment Management

### Environment Files

`.env.dev`:
```bash
# Development-specific settings
DEBUG=True
SECRET_KEY=dev-secret-key-not-for-production

# Database (use local SQLite for development)
# No DATABASE_* variables needed - SQLite is default

# Registry settings (for testing)
REGISTRY=ghcr.io
REGISTRY_USER=your-username

# Development features
WEBPACK_DEV_SERVER=True
DEBUG_TOOLBAR=True

# Hospital settings (can be fake for development)
HOSPITAL_NAME=Development Hospital
HOSPITAL_ADDRESS=123 Dev Street
HOSPITAL_PHONE=+1-555-DEV-EQMD
HOSPITAL_EMAIL=dev@localhost
```

`.env.test`:
```bash
# Test-specific settings
DEBUG=False
SECRET_KEY=test-secret-key
# Database (use test SQLite database)
DATABASE_NAME=test_db.sqlite3

# Disable external services in tests
REGISTRY=
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

### Switching Environments

```bash
# Development
docker compose --env-file .env.dev --profile dev up eqmd-dev

# Testing
docker compose --env-file .env.test up eqmd

# Production simulation
docker compose --env-file .env.prod up eqmd
```

## Troubleshooting Development Issues

### Common Problems

#### Permission Denied
```bash
# Fix container permissions
sudo chown -R $USER:$USER .
./create_eqmd_user.sh

# Rebuild with correct UID
docker compose build --no-cache eqmd-dev
```

#### Static Files Not Loading
```bash
# Rebuild static files
npm run build
docker compose restart eqmd-dev

# Check static files in container
docker compose exec eqmd-dev ls -la /app/staticfiles/
```

#### Database Locked
```bash
# Stop all containers
docker compose down

# Remove database file
rm db_dev.sqlite3

# Restart and migrate
docker compose --profile dev up -d eqmd-dev
docker compose exec eqmd-dev python manage.py migrate
```

#### Container Won't Start
```bash
# Check logs
docker compose logs eqmd-dev

# Rebuild container
docker compose build --no-cache eqmd-dev

# Reset completely
docker compose down --volumes
docker compose --profile dev up eqmd-dev
```

### Debug Commands

```bash
# Container shell access
docker compose exec eqmd-dev bash

# Django shell
docker compose exec eqmd-dev python manage.py shell

# Database shell
docker compose exec eqmd-dev python manage.py dbshell

# Check configuration
docker compose exec eqmd-dev python manage.py check

# Show settings
docker compose exec eqmd-dev python manage.py diffsettings
```

## Development Best Practices

### Code Quality

```bash
# Linting and formatting
docker compose exec eqmd-dev ruff check .
docker compose exec eqmd-dev black .

# Type checking
docker compose exec eqmd-dev mypy .

# Security checks
docker compose exec eqmd-dev bandit -r apps/
```

### Commit Hooks

Setup pre-commit hooks:
```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run on all files
pre-commit run --all-files
```

### Development Workflow

1. **Feature branches** for all development
2. **Test locally** with development mode
3. **Build and test** with registry images
4. **Submit PR** with CI/CD validation
5. **Deploy to staging** before production

This development guide ensures consistency between development and production while providing efficient workflows for daily development tasks.