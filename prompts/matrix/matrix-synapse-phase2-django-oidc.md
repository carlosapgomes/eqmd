# Phase 2: Django OIDC Provider Configuration

## Overview
Configure EquipeMed as an OpenID Connect (OIDC) provider for Matrix Synapse authentication using django-allauth identity provider functionality.

## Prerequisites
- Phase 1 infrastructure completed
- Django environment accessible
- Understanding of OIDC flow

## Step 1: Install Dependencies

### 1.1 Add OIDC Dependencies
Add to `requirements.txt` or install directly:
```bash
# Install OIDC provider capabilities
uv add "django-allauth[socialaccount,openid]"

# Install cryptographic dependencies
uv add cryptography jwcrypto
```

### 1.2 Verify Installation
```bash
# Check allauth version (should be 0.65.x or newer for OIDC provider support)
uv run python -c "import allauth; print(allauth.__version__)"
```

## Step 2: Generate RSA Key Pair for OIDC

### 2.1 Create Private Key
```bash
# Create keys directory
mkdir -p keys

# Generate RSA private key
openssl genpkey -algorithm RSA -out keys/oidc_private_key.pem -pkeyopt rsa_keygen_bits:2048

# Set proper permissions
chmod 600 keys/oidc_private_key.pem
```

### 2.2 Extract Public Key
```bash
# Extract public key
openssl rsa -pubout -in keys/oidc_private_key.pem -out keys/oidc_public_key.pem

# Verify key pair
openssl rsa -in keys/oidc_private_key.pem -check -noout
```

### 2.3 Convert to JWK Format (for debugging)
```bash
# Optional: create a script to view JWK format
uv run python -c "
from jwcrypto import jwk
with open('keys/oidc_private_key.pem', 'rb') as f:
    private_key = jwk.JWK.from_pem(f.read())
    print('Private Key JWK:', private_key.export_public())
"
```

## Step 3: Configure Django Settings

### 3.1 Update INSTALLED_APPS
Add to `config/settings.py`:
```python
INSTALLED_APPS = [
    # ... existing apps ...
    
    # django-allauth (existing)
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    
    # OIDC Identity Provider (NEW)
    "allauth.idp",
    "allauth.idp.oidc",
    
    # ... rest of apps ...
]
```

### 3.2 Add OIDC Provider Settings
Add to `config/settings.py`:
```python
# ================================================================================
# MATRIX OIDC PROVIDER CONFIGURATION
# ================================================================================

# Path to OIDC private key
OIDC_PRIVATE_KEY_PATH = BASE_DIR / "keys" / "oidc_private_key.pem"

# Load private key
if OIDC_PRIVATE_KEY_PATH.exists():
    with open(OIDC_PRIVATE_KEY_PATH, 'rb') as f:
        OIDC_PRIVATE_KEY = f.read()
else:
    OIDC_PRIVATE_KEY = None
    if not DEBUG:
        raise ValueError("OIDC private key not found at: " + str(OIDC_PRIVATE_KEY_PATH))

# OIDC Identity Provider Configuration
IDP_CONFIG = {
    "signing_key": OIDC_PRIVATE_KEY,
    "signing_alg": "RS256",
    "issuer": f"https://{os.getenv('ALLOWED_HOSTS', 'localhost').split(',')[0]}",
    "authorization_code_expires_seconds": 600,  # 10 minutes
    "access_token_expires_seconds": 3600,       # 1 hour
    "refresh_token_expires_seconds": 86400,     # 24 hours
}

# Matrix-specific OIDC scopes and claims
MATRIX_OIDC_SCOPES = {
    "openid": ["sub"],
    "profile": ["name", "preferred_username", "given_name", "family_name"],
    "email": ["email", "email_verified"],
}

# Custom Matrix user mapping
def matrix_user_claims(user, scopes):
    """Generate OIDC claims for Matrix integration."""
    claims = {}
    
    if "openid" in scopes:
        claims["sub"] = str(user.pk)
    
    if "profile" in scopes:
        claims["name"] = user.get_full_name() or user.username
        claims["preferred_username"] = user.username
        if user.first_name:
            claims["given_name"] = user.first_name
        if user.last_name:
            claims["family_name"] = user.last_name
            
        # Add Matrix-specific fields
        claims["matrix_localpart"] = user.username.lower().replace(' ', '_')
        
        # Add role information for future bot integration
        if hasattr(user, 'role'):
            claims["role"] = user.role
        claims["is_staff"] = user.is_staff
        claims["is_superuser"] = user.is_superuser
    
    if "email" in scopes:
        claims["email"] = user.email
        claims["email_verified"] = True  # We trust our own email verification
    
    return claims

# Register the claims function
IDP_CONFIG["user_claims"] = matrix_user_claims
```

### 3.3 Add Environment Variables
Add to `.env`:
```bash
# OIDC Configuration
OIDC_MATRIX_CLIENT_ID=matrix_synapse_client
OIDC_MATRIX_CLIENT_SECRET=your_secure_matrix_client_secret_here_32_chars_min
```

## Step 4: Create Matrix OIDC Django App

### 4.1 Create New Django App
```bash
# Create the app
uv run python manage.py startapp matrix_integration

# Add to INSTALLED_APPS in settings.py
INSTALLED_APPS = [
    # ... other apps ...
    'matrix_integration',
]
```

### 4.2 Create Matrix OIDC Models
Create `matrix_integration/models.py`:
```python
from django.db import models
from django.contrib.auth import get_user_model
from allauth.socialaccount.models import SocialApp

User = get_user_model()

class MatrixIntegration(models.Model):
    """Configuration for Matrix OIDC integration."""
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Matrix server configuration
    matrix_server_name = models.CharField(max_length=255, default="matrix.yourhospital.com")
    matrix_client_id = models.CharField(max_length=255, unique=True)
    matrix_client_secret = models.CharField(max_length=255)
    
    # OIDC configuration
    oidc_issuer = models.URLField()
    oidc_authorization_endpoint = models.URLField()
    oidc_token_endpoint = models.URLField()
    oidc_userinfo_endpoint = models.URLField()
    oidc_jwks_uri = models.URLField()
    
    # Settings
    auto_create_users = models.BooleanField(default=True)
    sync_user_profiles = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Matrix Integration"
        verbose_name_plural = "Matrix Integrations"
    
    def __str__(self):
        return f"Matrix Integration - {self.matrix_server_name}"

class MatrixUser(models.Model):
    """Mapping between Django users and Matrix users."""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='matrix_profile')
    matrix_user_id = models.CharField(max_length=255, unique=True)
    matrix_localpart = models.CharField(max_length=255)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    
    # Sync flags
    profile_synced_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Matrix User"
        verbose_name_plural = "Matrix Users"
    
    def __str__(self):
        return f"{self.user.username} -> {self.matrix_user_id}"
    
    def save(self, *args, **kwargs):
        if not self.matrix_localpart:
            self.matrix_localpart = self.user.username.lower().replace(' ', '_')
        if not self.matrix_user_id:
            self.matrix_user_id = f"@{self.matrix_localpart}:{self.matrix_user_id.split(':')[-1] if ':' in str(self.matrix_user_id) else 'matrix.yourhospital.com'}"
        super().save(*args, **kwargs)
```

### 4.3 Create Matrix Admin
Create `matrix_integration/admin.py`:
```python
from django.contrib import admin
from .models import MatrixIntegration, MatrixUser

@admin.register(MatrixIntegration)
class MatrixIntegrationAdmin(admin.ModelAdmin):
    list_display = ('matrix_server_name', 'matrix_client_id', 'auto_create_users', 'created_at')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Matrix Server', {
            'fields': ('matrix_server_name', 'matrix_client_id', 'matrix_client_secret')
        }),
        ('OIDC Endpoints', {
            'fields': ('oidc_issuer', 'oidc_authorization_endpoint', 'oidc_token_endpoint', 
                      'oidc_userinfo_endpoint', 'oidc_jwks_uri')
        }),
        ('Settings', {
            'fields': ('auto_create_users', 'sync_user_profiles')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

@admin.register(MatrixUser)
class MatrixUserAdmin(admin.ModelAdmin):
    list_display = ('user', 'matrix_localpart', 'matrix_user_id', 'is_active', 'last_login_at')
    list_filter = ('is_active', 'created_at', 'last_login_at')
    search_fields = ('user__username', 'user__email', 'matrix_localpart', 'matrix_user_id')
    readonly_fields = ('created_at', 'updated_at', 'profile_synced_at')
    
    fieldsets = (
        ('User Mapping', {
            'fields': ('user', 'matrix_localpart', 'matrix_user_id')
        }),
        ('Status', {
            'fields': ('is_active', 'last_login_at', 'profile_synced_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    actions = ['sync_matrix_users', 'deactivate_matrix_users']
    
    def sync_matrix_users(self, request, queryset):
        # Implementation will be in Phase 5
        self.message_user(request, "Matrix user sync functionality will be implemented in Phase 5.")
    sync_matrix_users.short_description = "Sync selected users with Matrix"
    
    def deactivate_matrix_users(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f"Deactivated {count} Matrix users.")
    deactivate_matrix_users.short_description = "Deactivate selected Matrix users"
```

## Step 5: Configure URL Routing

### 5.1 Create Matrix Integration URLs
Create `matrix_integration/urls.py`:
```python
from django.urls import path
from . import views

app_name = 'matrix_integration'

urlpatterns = [
    # OIDC provider URLs will be automatically added by allauth.idp
    path('status/', views.matrix_status, name='status'),
]
```

### 5.2 Update Main URLs
Add to `config/urls.py`:
```python
from django.urls import path, include

urlpatterns = [
    # ... existing URLs ...
    
    # OIDC Identity Provider URLs
    path('.well-known/', include('allauth.idp.oidc.urls')),
    path('oauth2/', include('allauth.idp.oidc.urls')),
    
    # Matrix integration URLs
    path('matrix/', include('matrix_integration.urls')),
    
    # ... rest of URLs ...
]
```

### 5.3 Create Basic Views
Create `matrix_integration/views.py`:
```python
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from .models import MatrixIntegration, MatrixUser

@staff_member_required
def matrix_status(request):
    """Status endpoint for Matrix integration."""
    total_users = MatrixUser.objects.count()
    active_users = MatrixUser.objects.filter(is_active=True).count()
    
    try:
        config = MatrixIntegration.objects.first()
        configured = config is not None
    except:
        configured = False
    
    return JsonResponse({
        'configured': configured,
        'total_matrix_users': total_users,
        'active_matrix_users': active_users,
        'matrix_server': 'matrix.yourhospital.com',
        'oidc_issuer': request.build_absolute_uri('/')[:-1]  # Remove trailing slash
    })
```

## Step 6: Database Migration

### 6.1 Create and Apply Migrations
```bash
# Create migrations
uv run python manage.py makemigrations matrix_integration

# Apply migrations
uv run python manage.py migrate
```

### 6.2 Create Matrix OIDC Application
Create management command `matrix_integration/management/commands/setup_matrix_oidc.py`:
```python
from django.core.management.base import BaseCommand
from django.conf import settings
from allauth.socialaccount.models import SocialApp
from allauth.idp.oidc.models import OpenIDConnectProvider
from matrix_integration.models import MatrixIntegration
import os

class Command(BaseCommand):
    help = 'Setup Matrix OIDC integration'

    def handle(self, *args, **options):
        # Create or update Matrix integration config
        config, created = MatrixIntegration.objects.get_or_create(
            matrix_server_name="matrix.yourhospital.com",
            defaults={
                'matrix_client_id': os.getenv('OIDC_MATRIX_CLIENT_ID'),
                'matrix_client_secret': os.getenv('OIDC_MATRIX_CLIENT_SECRET'),
                'oidc_issuer': f"https://{os.getenv('ALLOWED_HOSTS', 'localhost').split(',')[0]}",
                'oidc_authorization_endpoint': f"https://{os.getenv('ALLOWED_HOSTS', 'localhost').split(',')[0]}/oauth2/authorize/",
                'oidc_token_endpoint': f"https://{os.getenv('ALLOWED_HOSTS', 'localhost').split(',')[0]}/oauth2/token/",
                'oidc_userinfo_endpoint': f"https://{os.getenv('ALLOWED_HOSTS', 'localhost').split(',')[0]}/oauth2/userinfo/",
                'oidc_jwks_uri': f"https://{os.getenv('ALLOWED_HOSTS', 'localhost').split(',')[0]}/.well-known/jwks.json",
            }
        )
        
        action = "Created" if created else "Updated"
        self.stdout.write(
            self.style.SUCCESS(f'{action} Matrix integration configuration')
        )
        
        # Output OIDC endpoints for Matrix configuration
        self.stdout.write("\n" + "="*50)
        self.stdout.write("MATRIX SYNAPSE OIDC CONFIGURATION")
        self.stdout.write("="*50)
        self.stdout.write(f"OIDC Issuer: {config.oidc_issuer}")
        self.stdout.write(f"Client ID: {config.matrix_client_id}")
        self.stdout.write(f"Client Secret: {config.matrix_client_secret}")
        self.stdout.write(f"Authorization Endpoint: {config.oidc_authorization_endpoint}")
        self.stdout.write(f"Token Endpoint: {config.oidc_token_endpoint}")
        self.stdout.write(f"Userinfo Endpoint: {config.oidc_userinfo_endpoint}")
        self.stdout.write(f"JWKS URI: {config.oidc_jwks_uri}")
        self.stdout.write("="*50 + "\n")
```

## Step 7: Test OIDC Configuration

### 7.1 Run Setup Command
```bash
# Create Matrix OIDC configuration
uv run python manage.py setup_matrix_oidc
```

### 7.2 Test OIDC Endpoints
```bash
# Test JWKS endpoint
curl https://yourhospital.com/.well-known/jwks.json

# Test OIDC discovery
curl https://yourhospital.com/.well-known/openid_configuration

# Test Matrix integration status (requires staff login)
curl -H "Authorization: Bearer <admin-session>" https://yourhospital.com/matrix/status/
```

### 7.3 Verify in Django Admin
1. Login to Django admin
2. Navigate to "Matrix Integration" section
3. Verify configuration is created
4. Check that OIDC endpoints are properly set

## Step 8: Security Configuration

### 8.1 Update CORS Settings (if needed)
Add to `config/settings.py`:
```python
# CORS settings for OIDC (if using django-cors-headers)
CORS_ALLOWED_ORIGINS = [
    f"https://matrix.yourhospital.com",
    f"https://chat.yourhospital.com",
]

# Allow OIDC-specific headers
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]
```

### 8.2 Update CSRF Settings
Add to `config/settings.py`:
```python
# CSRF trusted origins for Matrix OIDC
CSRF_TRUSTED_ORIGINS = [
    f"https://matrix.yourhospital.com",
    f"https://chat.yourhospital.com",
]
```

## Verification Commands

### Check OIDC Configuration
```bash
# Verify private key
openssl rsa -in keys/oidc_private_key.pem -check -noout

# Check Django configuration
uv run python manage.py check

# Test OIDC endpoints
uv run python manage.py shell -c "
from matrix_integration.models import MatrixIntegration
config = MatrixIntegration.objects.first()
print('OIDC Issuer:', config.oidc_issuer if config else 'Not configured')
"
```

### Test User Claims Generation
```bash
# Test claims generation
uv run python manage.py shell -c "
from django.contrib.auth import get_user_model
from config.settings import matrix_user_claims
User = get_user_model()
user = User.objects.first()
if user:
    claims = matrix_user_claims(user, ['openid', 'profile', 'email'])
    print('Sample claims:', claims)
else:
    print('No users found for testing')
"
```

## File Structure Check

After Phase 2, you should have:
```
├── config/settings.py          # Updated with OIDC configuration
├── config/urls.py              # Updated with OIDC URLs
├── keys/
│   ├── oidc_private_key.pem    # RSA private key
│   └── oidc_public_key.pem     # RSA public key
├── matrix_integration/         # New Django app
│   ├── models.py               # Matrix integration models
│   ├── admin.py                # Admin interface
│   ├── views.py                # Basic views
│   ├── urls.py                 # URL configuration
│   └── management/commands/
│       └── setup_matrix_oidc.py # Setup command
└── requirements.txt            # Updated with OIDC dependencies
```

## Next Steps

1. ✅ **Complete Phase 2** OIDC provider setup
2. ➡️ **Proceed to Phase 3** for Matrix Synapse configuration
3. 🔐 **Keep private keys secure** - never commit to git
4. 📝 **Document OIDC endpoints** for Matrix configuration

## Troubleshooting

### Common Issues
- **Private key not found**: Verify key generation and file paths
- **OIDC endpoints not accessible**: Check URL configuration and CORS settings
- **Claims generation errors**: Verify user model compatibility

### Debug Commands
```bash
# Check OIDC provider registration
uv run python manage.py shell -c "from allauth.idp.oidc.models import *; print(OpenIDConnectProvider.objects.all())"

# Test OIDC endpoints
uv run python manage.py runserver --settings=config.settings
curl http://localhost:8000/.well-known/openid_configuration
```

---

**Status**: Django OIDC provider configured and ready for Matrix integration