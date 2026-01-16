# Matrix Synapse Phase 2: OIDC Provider Setup Guide

This guide covers configuring EquipeMed as an OIDC provider for Matrix Synapse SSO integration.

## Overview

Phase 2 enables EquipeMed to act as an OIDC identity provider for Matrix Synapse, allowing users to sign into Matrix using their EquipeMed credentials with proper access control and user identity mapping.

## Implementation Summary

### Components Implemented

1. **OIDC Provider Configuration**: Extended existing django-oidc-provider setup
2. **Claims Mapping**: Custom claims for stable user identity
3. **Access Control**: Inactive user authorization blocking
4. **Client Registration**: Automated Synapse OIDC client setup
5. **User Identity Mapping**: Secure user ID mapping using UserProfile.public_id

### Key Features

- **Authorization Code Grant**: Secure OAuth 2.0 flow for Synapse SSO
- **Stable User Identity**: Uses UserProfile.public_id for consistent Matrix user mapping
- **Professional Role Mapping**: Maps EquipeMed profession types to Matrix user roles
- **Access Control**: Prevents inactive users from completing OIDC authorization
- **Idempotent Client Setup**: Management command for safe Synapse client registration

## Configuration Details

### OIDC Provider Settings

Updated `config/settings.py` with:

```python
OIDC_PROVIDER = {
    # Grant types for both bot delegation and Synapse SSO
    'OIDC_GRANT_TYPE_SUPPORTED': [
        'client_credentials',  # For bot authentication
        'authorization_code',  # For Synapse SSO
    ],
    
    # Response types (code preferred for security)
    'OIDC_RESPONSE_TYPES_SUPPORTED': [
        'code',  # For authorization_code grant (preferred)
        'token',  # Keep for existing bot usage if needed
    ],
    
    # Custom authorization view for access control
    'OIDC_AUTHORIZE_VIEW': 'apps.botauth.views.AuthorizeView',
    
    # Custom claims implementation
    'OIDC_EXTRA_SCOPE_CLAIMS': 'apps.botauth.claims.EqmdScopeClaims',
    
    # Other existing settings...
}
```

### Claims Mapping

Implemented in `apps/botauth/claims.py`:

```python
class EqmdScopeClaims(ScopeClaims):
    """Custom scope claims for EQMD delegation tokens and Synapse SSO."""
    
    info_openid = [
        'sub',
        'name', 
        'preferred_username',
        'eqmd_active',
        'eqmd_role',
    ]

    def scope_openid(self):
        """OpenID Connect standard claims for user identity."""
        user = self.user
        
        # Use UserProfile.public_id for stable identity
        profile = user.profile
        public_id = str(profile.public_id)
        
        # Build full name with fallbacks
        full_name = user.get_full_name()
        if not full_name.strip():
            full_name = user.email or user.username
        
        # Map profession type to stable ASCII slugs
        profession_mapping = {
            user.MEDICAL_DOCTOR: 'medical_doctor',
            user.RESIDENT: 'resident', 
            user.NURSE: 'nurse',
            user.PHYSIOTERAPIST: 'physiotherapist',
            user.STUDENT: 'student',
        }
        
        eqmd_role = profession_mapping.get(user.profession_type, 'unknown') if user.profession_type is not None else 'unknown'
        
        return {
            'sub': public_id,
            'name': full_name,
            'preferred_username': user.email or user.username,
            'eqmd_active': user.is_active,
            'eqmd_role': eqmd_role,
        }
```

### Access Control Implementation

Custom authorization view in `apps/botauth/views.py`:

```python
@method_decorator(login_required, name='dispatch')
class AuthorizeView(BaseAuthorizeView):
    """
    Custom OIDC authorization view with access control.
    
    Ensures that only active users can complete OIDC authorization flows.
    This prevents inactive users from accessing Matrix Synapse via SSO.
    """
    
    def get(self, request, *args, **kwargs):
        """Handle GET requests to authorization endpoint."""
        if not request.user.is_authenticated:
            return super().get(request, *args, **kwargs)
            
        if not request.user.is_active:
            # User account is inactive, deny authorization
            context = {
                'error': 'access_denied',
                'error_description': 'Your account is currently inactive. Please contact your administrator.',
                'user': request.user,
            }
            return render(request, 'oidc_provider/error.html', context, status=403)
        
        # User is active, proceed with normal authorization flow
        return super().get(request, *args, **kwargs)
```

## Client Registration

### Management Command

Created `apps/botauth/management/commands/setup_synapse_oidc_client.py`:

```bash
# Register Synapse OIDC client
uv run python manage.py setup_synapse_oidc_client

# With custom settings
uv run python manage.py setup_synapse_oidc_client \
  --client-id custom-synapse-client \
  --matrix-fqdn matrix.yourdomain.com \
  --force-new-secret
```

### Generated Configuration

The command outputs ready-to-use Synapse configuration:

```yaml
oidc_providers:
  - idp_id: "${SYNAPSE_OIDC_PROVIDER_ID}"
    idp_name: EquipeMed
    issuer: "https://app.sispep.com/o"
    client_id: "synapse-matrix"
    client_secret: "generated_secret_here"
    scopes: ["openid", "profile"]
    allow_existing_users: true
    allow_new_users: false
    user_mapping_provider:
      config:
        subject_claim: "sub"
        localpart_template: "u_{{ user.sub }}"
        display_name_template: "{{ user.name }}"
```

## Environment Variables

Added to `.env`:

```bash
# Matrix Synapse OIDC Integration
SYNAPSE_OIDC_CLIENT_SECRET=generated_secret_here
SYNAPSE_OIDC_PROVIDER_ID=equipemed
```

## Security Features

### User Identity Mapping

- **Stable Identity**: Uses `UserProfile.public_id` (UUID) for the OIDC `sub`
- **Admin-Managed MXID**: Matrix localpart is stored on the user profile and set by admins
- **External ID Linking**: Synapse matches users via `external_ids` using the profile UUID

### Access Control

- **Active Users Only**: Only `is_active=True` users can complete authorization
- **Graceful Denial**: Inactive users see proper error message
- **No Session Bypass**: Validation occurs on every authorization request

### Provisioning Requirement

Synapse is configured to allow only existing users. Provision Matrix accounts in Django admin
before users attempt OIDC login so the `external_ids` link exists.

### Professional Role Mapping (OIDC Claim)

| EquipeMed Profession | Matrix Role Slug |
|---------------------|------------------|
| Medical Doctor | `medical_doctor` |
| Resident | `resident` |
| Nurse | `nurse` |
| Physiotherapist | `physiotherapist` |
| Student | `student` |
| Unknown/Null | `unknown` |

## OIDC Endpoints

Available endpoints for Synapse configuration:

- **Discovery**: `https://app.sispep.com/o/.well-known/openid-configuration`
- **Authorization**: `https://app.sispep.com/o/authorize/`
- **Token**: `https://app.sispep.com/o/token/`
- **UserInfo**: `https://app.sispep.com/o/userinfo/`
- **JWKS**: `https://app.sispep.com/o/jwks/`

## Testing

### Verify OIDC Client Registration

```bash
# Check registered clients
uv run python manage.py shell -c "
from oidc_provider.models import Client
for client in Client.objects.all():
    print(f'{client.name}: {client.client_id} ({client.client_type})')
"
```

### Test Claims Generation

```bash
# Test claims for a specific user
uv run python manage.py shell -c "
from apps.botauth.claims import EqmdScopeClaims
from apps.accounts.models import EqmdCustomUser

user = EqmdCustomUser.objects.first()
claims = EqmdScopeClaims(user=user, scope=['openid'])
print('Claims:', claims.scope_openid())
"
```

### Verify OIDC Discovery

```bash
curl -s https://app.sispep.com/o/.well-known/openid-configuration | jq .
```

## Integration with Phase 3

Phase 2 provides the foundation for Phase 3 (Synapse OIDC client configuration). The generated client credentials and endpoints will be used to configure Synapse's homeserver.yaml.

## Docker Deployment Note

**Known Issue**: The current Django Docker container may fail to start due to a psycopg2 import error. This is being addressed by:

1. Updating Dockerfile to use Python 3.12 (to match pyproject.toml requirement)  
2. Ensuring proper psycopg2-binary installation via uv

For immediate testing, use local development with `DATABASE_HOST=localhost` while the Docker image is being fixed.

## Troubleshooting

### Common Issues

#### Claims AttributeError
```
AttributeError: 'EqmdCustomUser' object has no attribute 'profile'
```
**Solution**: Ensure all users have UserProfile objects. Create them if missing:

```python
from apps.accounts.models import EqmdCustomUser, UserProfile
for user in EqmdCustomUser.objects.all():
    UserProfile.objects.get_or_create(user=user)
```

#### OIDC Authorization Errors
```
access_denied: Your account is currently inactive
```
**Expected**: This is the access control working. Inactive users cannot access Matrix.

#### Missing Client Secret
```
KeyError: 'client_secret'
```
**Solution**: Re-run the setup command:
```bash
uv run python manage.py setup_synapse_oidc_client --force-new-secret
```

## Security Considerations

### Access Control
- Only active EquipeMed users can complete OIDC authorization
- User lifecycle management automatically blocks Matrix access for inactive accounts
- No bypass mechanisms - validation occurs on every login attempt

### Identity Stability
- Uses UUID-based public_id for stable user identity
- Profession-based localpart prevents username collisions
- Display name updates automatically reflect EquipeMed changes

### Token Security
- Authorization code flow provides secure token exchange
- Client credentials use confidential client type
- No implicit grant types enabled for enhanced security

## What's Next

After completing Phase 2, proceed to:
- **Phase 3**: Configure Synapse OIDC client integration
- **Phase 4**: Set up Element Web well-known endpoints  
- **Phase 5**: Implement policy bot and room management
- **Phase 6**: Production deployment and testing

The OIDC provider is now ready to authenticate Matrix Synapse users with proper access control and identity mapping.
