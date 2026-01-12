# Phase 02 – OIDC Provider Setup

## Goal

Install and configure django-oidc-provider with zero behavior change to existing authentication. After this phase, the OIDC provider infrastructure exists but is not yet used.

## Prerequisites

- Phase 01 completed (baseline assessment)
- All existing tests passing

## Tasks

### Task 2.1: Install Dependency

```bash
uv add django-oidc-provider
```

Verify in `pyproject.toml`:
```toml
dependencies = [
    # ... existing deps ...
    "django-oidc-provider>=0.7.0",
]
```

Also install PyJWT for token handling:
```bash
uv add pyjwt
```

### Task 2.2: Add to INSTALLED_APPS

Edit `config/settings.py`:

```python
INSTALLED_APPS = [
    # ... existing apps ...
    
    # OIDC Provider (for bot delegation)
    "oidc_provider",
]
```

### Task 2.3: Run Migrations

```bash
uv run python manage.py migrate oidc_provider
```

Verify tables created:
- `oidc_provider_client`
- `oidc_provider_code`
- `oidc_provider_token`
- `oidc_provider_userconsent`
- `oidc_provider_rsakey`

### Task 2.4: Generate RSA Key

```bash
uv run python manage.py creatersakey
```

This creates a signing key in the database for JWT signatures.

### Task 2.5: Configure OIDC Settings

Add to `config/settings.py`:

```python
# =============================================================================
# OIDC Provider Configuration (for Bot Delegation)
# =============================================================================

OIDC_PROVIDER = {
    # Issuer identifier - must match what's in JWTs
    'OIDC_ISSUER': os.getenv('OIDC_ISSUER', 'https://eqmd.local'),
    
    # Token expiration (these are defaults, delegation endpoint overrides)
    'OIDC_TOKEN_EXPIRE': 600,  # 10 minutes max for delegated tokens
    'OIDC_CODE_EXPIRE': 60,    # 1 minute for auth codes (not used for bots)
    
    # ID Token expiration
    'OIDC_IDTOKEN_EXPIRE': 600,
    
    # Disable refresh tokens for bot clients
    'OIDC_TOKEN_INTROSPECTION_ENABLED': True,
    
    # Custom claims (we'll add physician info)
    'OIDC_EXTRA_SCOPE_CLAIMS': 'apps.botauth.claims.EqmdScopeClaims',
    
    # Session management (disabled for bots)
    'OIDC_SESSION_MANAGEMENT_ENABLE': False,
    
    # Grant types allowed
    'OIDC_GRANT_TYPE_SUPPORTED': [
        'client_credentials',  # For bot authentication
    ],
    
    # Response types (minimal for our use case)
    'OIDC_RESPONSE_TYPES_SUPPORTED': [
        'token',
    ],
    
    # Scopes we support
    'OIDC_SCOPES': {
        'patient:read': 'Read patient demographics and status',
        'exam:read': 'Read exam results',
        'dailynote:draft': 'Create daily note drafts',
        'dischargereport:draft': 'Create discharge report drafts',
        'prescription:draft': 'Create prescription drafts',
        'summary:generate': 'Generate summaries from existing data',
    },
}

# JWT signing key (for our custom delegated tokens)
# In production, use a proper secret management system
DELEGATED_TOKEN_SECRET = os.getenv('DELEGATED_TOKEN_SECRET', SECRET_KEY)
DELEGATED_TOKEN_ALGORITHM = 'HS256'  # Or RS256 if using RSA keys
DELEGATED_TOKEN_ISSUER = os.getenv('OIDC_ISSUER', 'eqmd')
DELEGATED_TOKEN_AUDIENCE = 'eqmd-api'
DELEGATED_TOKEN_LIFETIME_SECONDS = 600  # 10 minutes max
```

### Task 2.6: Add OIDC URLs (Minimal)

Edit `config/urls.py`:

```python
urlpatterns = [
    # ... existing patterns ...
    
    # OIDC Provider endpoints (minimal exposure)
    # We only need the token endpoint for client_credentials
    path('o/', include('oidc_provider.urls', namespace='oidc_provider')),
]
```

**Note**: We expose the standard OIDC endpoints but will primarily use our custom delegated token endpoint (Phase 06).

### Task 2.7: Create Bot Auth App Structure

Create the new app for bot authentication:

```bash
mkdir -p apps/botauth
touch apps/botauth/__init__.py
touch apps/botauth/apps.py
touch apps/botauth/models.py
touch apps/botauth/claims.py
touch apps/botauth/admin.py
```

Create `apps/botauth/apps.py`:

```python
from django.apps import AppConfig


class BotauthConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.botauth'
    verbose_name = 'Bot Authentication'
```

Create placeholder `apps/botauth/claims.py`:

```python
"""
Custom OIDC claims for EQMD.

This module will be expanded in later phases to include
physician and delegation information in tokens.
"""

from oidc_provider.lib.claims import ScopeClaims


class EqmdScopeClaims(ScopeClaims):
    """Custom scope claims for EQMD delegation tokens."""
    
    # Will be implemented in Phase 06
    pass
```

Add to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # ... existing apps ...
    "apps.botauth.apps.BotauthConfig",
    "oidc_provider",
]
```

### Task 2.8: Verify No Regression

Run all authentication-related tests:

```bash
# All existing tests must pass
uv run pytest apps/accounts/tests/ -v
uv run pytest apps/core/tests/test_permissions/ -v

# Verify allauth still works (manual or with test)
uv run python manage.py runserver
# Navigate to /accounts/login/ - should work normally
```

## Files to Create

1. `apps/botauth/__init__.py`
2. `apps/botauth/apps.py`
3. `apps/botauth/models.py` (empty placeholder)
4. `apps/botauth/claims.py`
5. `apps/botauth/admin.py` (empty placeholder)

## Files to Modify

1. `pyproject.toml` - Add dependencies
2. `config/settings.py` - Add INSTALLED_APPS and OIDC settings
3. `config/urls.py` - Add OIDC URLs

## Acceptance Criteria

- [ ] `django-oidc-provider` installed and in pyproject.toml
- [ ] `pyjwt` installed and in pyproject.toml
- [ ] `oidc_provider` in INSTALLED_APPS
- [ ] `apps.botauth` app created and in INSTALLED_APPS
- [ ] OIDC migrations applied successfully
- [ ] RSA key generated (`creatersakey` command)
- [ ] OIDC_PROVIDER settings configured
- [ ] OIDC URLs mounted at `/o/`
- [ ] All existing authentication tests pass
- [ ] Manual login via allauth still works
- [ ] No new endpoints are publicly accessible without authentication

## Verification Commands

```bash
# Verify dependencies installed
uv run python -c "import oidc_provider; print(oidc_provider.__version__)"
uv run python -c "import jwt; print(jwt.__version__)"

# Verify migrations applied
uv run python manage.py showmigrations oidc_provider
# Expected: All [X] checked

# Verify RSA key exists
uv run python manage.py shell -c "from oidc_provider.models import RSAKey; print(RSAKey.objects.count())"
# Expected: 1 or more

# Verify settings loaded
uv run python manage.py shell -c "from django.conf import settings; print(settings.OIDC_PROVIDER)"
# Expected: Dict with our configuration

# Verify no regression
uv run pytest apps/accounts/tests/ apps/core/tests/test_permissions/ -v
# Expected: All tests pass
```

## Security Notes

- The OIDC provider endpoints are now available but require authentication
- No clients are registered yet, so no tokens can be issued
- The `/o/.well-known/openid-configuration` endpoint will be public (standard OIDC)
- This is acceptable as it only exposes metadata, not credentials
