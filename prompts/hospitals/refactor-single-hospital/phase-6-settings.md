# Phase 6: Settings and Configuration Cleanup

**Estimated Time:** 30-45 minutes  
**Complexity:** Low  
**Dependencies:** Phase 5 completed

## Objectives

1. Remove hospital-related Django settings
2. Remove hospital middleware
3. Clean up URL patterns
4. Update configuration files
5. Remove hospital-related management commands

## Tasks

### 1. Update Django Settings (`eqmd/settings.py`)

**Remove hospitals app from INSTALLED_APPS:**
```python
# Before
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    # ... other apps
    'apps.hospitals',  # Remove this line
    'apps.accounts',
    'apps.patients',
    # ... other apps
]

# After (hospitals app removed)
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    # ... other apps
    'apps.accounts',
    'apps.patients',
    # ... other apps
]
```

**Remove hospital middleware:**
```python
# Before
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # ... other middleware
    'apps.hospitals.middleware.HospitalContextMiddleware',  # Remove this
    # ... other middleware
]

# After (hospital middleware removed)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # ... other middleware (no hospital middleware)
]
```

**Remove hospital-related template context processors:**
```python
# Before
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                # ... other processors
                'apps.hospitals.context_processors.hospital_context',  # Remove this
            ],
        },
    },
]

# After (hospital context processor removed)
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                # ... other processors (no hospital processor)
            ],
        },
    },
]
```

### 2. Update Main URL Configuration (`eqmd/urls.py`)

**Remove hospital URL includes:**
```python
# Before
urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('hospitals/', include('apps.hospitals.urls')),  # Remove this line
    path('patients/', include('apps.patients.urls')),
    # ... other URL patterns
]

# After (hospital URLs removed)
urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('patients/', include('apps.patients.urls')),
    # ... other URL patterns
]
```

### 3. Remove Hospital-Related Configuration

**Remove hospital-specific settings:**
- [ ] Remove any hospital-related cache settings
- [ ] Remove hospital context session settings
- [ ] Remove hospital-related logging configuration
- [ ] Remove hospital permission settings

**Check for and remove:**
```python
# Remove settings like these if they exist
HOSPITAL_CONTEXT_SESSION_KEY = 'current_hospital_id'
HOSPITAL_CACHE_TIMEOUT = 300
HOSPITAL_PERMISSION_CACHE_TIMEOUT = 600
```

### 4. Update Authentication Settings

**Simplify login redirects (no hospital selection):**
```python
# Before (redirect to hospital selection)
LOGIN_REDIRECT_URL = '/hospitals/select/'

# After (direct to dashboard)
LOGIN_REDIRECT_URL = '/dashboard/'
```

### 5. Update Management Commands

**Delete hospital-specific management commands:**
- [ ] Delete `apps/hospitals/management/` (entire directory with hospitals app)
- [ ] Delete `apps/core/management/commands/assign_users_to_hospitals.py` (assigns users to hospitals)

**Update hospital-dependent management commands:**

**`setup_groups.py` updates needed:**
- [ ] Remove `_get_hospital_permissions()` and `_get_hospital_view_permissions()` methods
- [ ] Remove hospital permission calls from group creation methods (lines 93, 110, 126, 142)
- [ ] Remove PatientHospitalRecord references from patient permission methods
- [ ] Update to work with simplified permission model

**`populate_sample_data.py` updates needed:**
- [ ] Remove hospital creation logic (`create_hospitals()` method)
- [ ] Remove hospital imports (`from apps.hospitals.models import Hospital, Ward`)
- [ ] Remove user-hospital assignments in `create_users()` method
- [ ] Remove hospital assignments in patient creation
- [ ] Remove PatientHospitalRecord creation
- [ ] Update to work with environment-based hospital configuration

**Keep as-is (no hospital dependencies):**
- [ ] `apps/core/management/commands/permission_audit.py` - Works with profession-based groups
- [ ] `apps/core/management/commands/permission_performance.py` - Tests permission functions
- [ ] `apps/core/management/commands/user_permissions.py` - Manages user-group assignments

### 6. Update Database Configuration

**Remove hospital-related database indexes (if any custom ones):**
- [ ] Check for custom database indexes related to hospitals
- [ ] Remove hospital-related database constraints
- [ ] Update database optimization settings

### 7. Clean Up Static Files Configuration

**Remove hospital-related static file configurations:**
- [ ] Remove hospital-specific CSS/JS from static files
- [ ] Remove hospital-related webpack configurations
- [ ] Update static file collection

### 8. Update Logging Configuration

**Remove hospital context from logging:**
```python
# Before (hospital context in logs)
LOGGING = {
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {hospital} {message}',
        },
    },
}

# After (no hospital context)
LOGGING = {
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
        },
    },
}
```

### 9. Update Cache Configuration

**Simplify cache keys (no hospital context):**
```python
# Remove hospital-aware cache configurations
# Simplify cache key patterns
```

### 10. Update Security Settings

**Remove hospital-related security settings:**
- [ ] Remove hospital context from CSRF settings
- [ ] Remove hospital-related CORS settings (if any)
- [ ] Simplify session security

### 11. Hospital Configuration via Environment Variables

**Add single hospital configuration (.env files):**
```bash
# Hospital Information
HOSPITAL_NAME="Your Hospital Name"
HOSPITAL_ADDRESS="123 Medical Center Drive, City, State 12345"
HOSPITAL_PHONE="+1-555-123-4567"
HOSPITAL_EMAIL="info@yourhospital.com"
HOSPITAL_WEBSITE="https://www.yourhospital.com"

# Hospital Logo for Reports
HOSPITAL_LOGO_PATH="static/images/hospital-logo.png"
# Alternative: Use URL for external logo
# HOSPITAL_LOGO_URL="https://yourcdn.com/logo.png"
```

**Update settings.py to include hospital config:**
```python
# Hospital Configuration
HOSPITAL_CONFIG = {
    'name': os.getenv('HOSPITAL_NAME', 'Medical Center'),
    'address': os.getenv('HOSPITAL_ADDRESS', ''),
    'phone': os.getenv('HOSPITAL_PHONE', ''),
    'email': os.getenv('HOSPITAL_EMAIL', ''),
    'website': os.getenv('HOSPITAL_WEBSITE', ''),
    'logo_path': os.getenv('HOSPITAL_LOGO_PATH', 'static/images/default-logo.png'),
    'logo_url': os.getenv('HOSPITAL_LOGO_URL', ''),
}
```

### 12. Docker Configuration (if applicable)

**Update Docker settings:**
- [ ] Remove hospital-related environment variables from docker-compose
- [ ] Update container configuration
- [ ] Remove hospital data volumes

## Files to Modify

### Configuration Files:
- [ ] `eqmd/settings.py` - Major cleanup
- [ ] `eqmd/urls.py` - Remove hospital URLs
- [ ] `.env` / `.env.example` - Remove hospital variables
- [ ] `docker-compose.yml` (if applicable) - Remove hospital config

### Files to Delete:
- [ ] `apps/hospitals/urls.py`
- [ ] `apps/hospitals/management/` (entire directory)
- [ ] `apps/core/management/commands/assign_users_to_hospitals.py`
- [ ] Any hospital-specific configuration files

### Management Commands Modified:
- [ ] **Deleted:** `assign_users_to_hospitals.py` (hospital-specific functionality)
- [ ] **Updated:** `setup_groups.py` (remove hospital permissions)
- [ ] **Updated:** `populate_sample_data.py` (remove hospital creation/assignment)
- [ ] **Unchanged:** `permission_audit.py`, `permission_performance.py`, `user_permissions.py`

## Validation Steps

**Test configuration changes:**
```bash
# Check Django configuration
uv run python manage.py check

# Test settings loading
uv run python manage.py shell -c "from django.conf import settings; print('Settings loaded successfully')"

# Test URL patterns
uv run python manage.py show_urls

# Test management commands
uv run python manage.py help
```

### 1. Verify Django Check Passes
```bash
uv run python manage.py check
# Should show no errors

uv run python manage.py check --deploy
# Should show no critical issues
```

### 2. Test URL Resolution
```bash
uv run python manage.py show_urls
# Should not show any hospital URLs
```

### 3. Test Static Files
```bash
uv run python manage.py collectstatic --dry-run
# Should work without hospital-related files
```

### 4. Test Development Server
```bash
uv run python manage.py runserver
# Should start without errors
```

### 5. Test Database Connection
```bash
uv run python manage.py migrate --dry-run
# Should show no pending migrations
```

## Validation Checklist

Before proceeding to Phase 7:
- [ ] `uv run python manage.py check` passes
- [ ] Development server starts successfully
- [ ] No hospital URLs in URL patterns
- [ ] No hospital apps in INSTALLED_APPS
- [ ] No hospital middleware in settings
- [ ] Static files collect successfully
- [ ] No import errors on settings load
- [ ] Database connections work

## Configuration Simplifications

**Benefits of simplified configuration:**
- Faster Django startup (less apps/middleware)
- Simpler URL routing
- Reduced memory usage
- Easier deployment configuration
- Fewer potential configuration errors

## Security Review

**Ensure security is maintained:**
- [ ] Authentication still works correctly
- [ ] Permission system functions properly
- [ ] Session management works
- [ ] CSRF protection active
- [ ] No security regressions from removed middleware

## Performance Improvements

**Expected performance gains:**
- Faster request processing (no hospital middleware)
- Faster URL resolution (fewer patterns)
- Reduced memory usage (fewer apps)
- Faster static file serving