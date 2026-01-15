# Phase 3: Matrix Synapse Configuration

## Overview
Configure Matrix Synapse homeserver with OIDC authentication, security policies, and restrictions for medical team use.

## Prerequisites
- Phase 1 infrastructure completed
- Phase 2 Django OIDC provider configured
- Matrix container ready to start
- OIDC endpoints accessible

## Step 1: Generate Synapse Configuration

### 1.1 Generate Initial Configuration
```bash
# Generate base configuration
docker run -it --rm \
    -v $(pwd)/matrix:/data \
    matrixdotorg/synapse:latest generate

# This creates a basic homeserver.yaml in ./matrix/
# We'll customize it in the next steps
```

### 1.2 Create Signing Keys
```bash
# Generate signing keys for Synapse
mkdir -p matrix/keys
docker run -it --rm \
    -v $(pwd)/matrix:/data \
    matrixdotorg/synapse:latest \
    python -m synapse.app.homeserver \
    --generate-keys \
    --config-path=/data/homeserver.yaml

# Set proper permissions
chmod 600 matrix/*.signing.key
```

## Step 2: Configure homeserver.yaml

Create `matrix/homeserver.yaml`:

```yaml
# Matrix Synapse Configuration for EquipeMed
# Non-federated medical team collaboration server

server_name: "matrix.yourhospital.com"
pid_file: /data/homeserver.pid
web_client: false
soft_file_limit: 0

listeners:
  - port: 8008
    tls: false
    bind_addresses: ['::']
    type: http
    x_forwarded: true

    resources:
      - names: [client, federation]
        compress: false

# ================================================================================
# DATABASE CONFIGURATION
# ================================================================================

database:
  name: psycopg2
  args:
    user: matrix_user
    password: matrix_secure_password_123
    database: matrix_db
    host: postgres
    port: 5432
    cp_min: 5
    cp_max: 10

# ================================================================================
# LOGGING CONFIGURATION
# ================================================================================

log_config: "/data/log_config.yaml"

# ================================================================================
# MEDIA REPOSITORY
# ================================================================================

media_store_path: /data/media_store
max_upload_size: 50M
max_image_pixels: 32M

# Allowed media types for medical use
allowed_avatar_mimetypes: ["image/png", "image/jpeg", "image/gif"]
allowed_local_3pids:
  - medium: email
    pattern: ".*"

# Media retention (optional)
media_retention:
  local_media_lifetime: 365d
  remote_media_lifetime: 90d

# ================================================================================
# REGISTRATION AND ACCOUNT MANAGEMENT
# ================================================================================

# Disable registration - OIDC only
enable_registration: false
enable_registration_without_verification: false

# Disable guest access
allow_guest_access: false

# Registration shared secret for admin use only
registration_shared_secret: "your_matrix_registration_secret_here_32_chars_min"

# ================================================================================
# FEDERATION (DISABLED)
# ================================================================================

# Completely disable federation
federation_domain_whitelist: []
send_federation: false
federation_metrics_domains: []

# Block federation ports
federation_client_minimum_tls_version: 1.3
federation_verify_certificates: true

# ================================================================================
# SECURITY SETTINGS
# ================================================================================

# Prevent abuse
limit_profile_requests_to_users_who_share_rooms: true
include_profile_data_on_invite: false

# Rate limiting
rc_message:
  per_second: 0.2
  burst_count: 10

rc_registration:
  per_second: 0.17
  burst_count: 3

rc_login:
  address:
    per_second: 0.17
    burst_count: 3
  account:
    per_second: 0.17
    burst_count: 3
  failed_attempts:
    per_second: 0.17
    burst_count: 3

# Prevent room flooding
rc_joins:
  local:
    per_second: 0.1
    burst_count: 3
  remote:
    per_second: 0.01
    burst_count: 3

# ================================================================================
# ROOM SETTINGS
# ================================================================================

# Default room settings for medical use
default_room_version: "10"

# Encryption disabled by default
encryption_enabled_by_default_for_room_type: off

# Room creation restrictions
enable_room_list_search: false
alias_creation_rules:
  - user_id: "@*:matrix.yourhospital.com"
    alias: "*"
    action: allow

# ================================================================================
# OIDC AUTHENTICATION
# ================================================================================

oidc_providers:
  - idp_id: equipemed
    idp_name: "EquipeMed Login"
    idp_brand: "equipemed"
    discover: false
    issuer: "https://yourhospital.com"
    client_id: "matrix_synapse_client"
    client_secret: "your_secure_matrix_client_secret_here_32_chars_min"
    client_auth_method: "client_secret_post"
    
    # OIDC endpoints
    authorization_endpoint: "https://yourhospital.com/oauth2/authorize/"
    token_endpoint: "https://yourhospital.com/oauth2/token/"
    userinfo_endpoint: "https://yourhospital.com/oauth2/userinfo/"
    jwks_uri: "https://yourhospital.com/.well-known/jwks.json"
    
    # Scopes to request
    scopes: ["openid", "profile", "email"]
    
    # User mapping
    user_mapping:
      subject_claim: "sub"
      localpart_template: "{{ user.preferred_username }}"
      display_name_template: "{{ user.name }}"
      email_template: "{{ user.email }}"
      extra_attributes:
        role: "{{ user.role }}"
        is_staff: "{{ user.is_staff }}"
        is_superuser: "{{ user.is_superuser }}"
    
    # Attribute requirements for access
    attribute_requirements:
      - attribute: "email_verified"
        value: true
    
    # Enable PKCE for security
    pkce_method: "S256"
    
    # Skip verification for internal OIDC
    skip_verification: true
    
    # Allow display name changes
    allow_existing_users: true
    update_profile_information: true

# ================================================================================
# PRESENCE AND TYPING INDICATORS
# ================================================================================

# Disable presence for better performance and privacy
use_presence: false
presence_enabled: false

# Limit typing notifications
typing_enabled: true

# ================================================================================
# ROOM DIRECTORY
# ================================================================================

# Disable public room directory
enable_room_list_search: false
room_list_publication_rules:
  - user_id: "@*:matrix.yourhospital.com"
    alias: "*"
    action: deny

# ================================================================================
# SECURITY HARDENING
# ================================================================================

# Prevent directory access
enable_3pid_lookup: false

# Disable metrics for external access
enable_metrics: false
report_stats: false

# Content security
allow_public_rooms_without_auth: false
allow_public_rooms_over_federation: false

# Admin contact
admin_contact: "mailto:admin@yourhospital.com"

# ================================================================================
# POWER LEVELS AND PERMISSIONS
# ================================================================================

# Default power levels favor medical staff
default_power_level_content_override:
  ban: 50
  events:
    "m.room.name": 50
    "m.room.avatar": 50
    "m.room.topic": 25
    "m.room.canonical_alias": 50
    "m.room.encryption": 100  # Prevent encryption changes
    "m.room.history_visibility": 50
    "m.room.power_levels": 50
    "m.room.tombstone": 100
  events_default: 0
  invite: 25
  kick: 50
  redact: 25
  state_default: 25
  users_default: 0

# Room creation restricted to admins and bots
room_creation_rules:
  - user_id: "@*:matrix.yourhospital.com"
    action: deny
  - user_id: "@bot_*:matrix.yourhospital.com"
    action: allow

# ================================================================================
# WORKER CONFIGURATION (Single Process)
# ================================================================================

# Run in single process mode for simplicity
worker_app: synapse.app.homeserver
worker_replication_http_port: 9093

# ================================================================================
# CACHES AND PERFORMANCE
# ================================================================================

# Conservative caching for limited memory
caches:
  global_factor: 0.5
  per_cache_factors:
    get_users_who_share_room_with_user: 2.0
    
# Event cache size
event_cache_size: 10K
  
# ================================================================================
# CLEANUP AND MAINTENANCE
# ================================================================================

# Cleanup settings
cleanup_extremities_with_dummy_events: true

# Retention policies
retention:
  enabled: true
  default_policy:
    min_lifetime: 7d
    max_lifetime: 365d
  allowed_lifetime_min: 1d
  allowed_lifetime_max: 3653d  # 10 years for medical records

# Automatic cleanup
auto_join_rooms: []

# ================================================================================
# TRUSTED KEY SERVERS (Empty for non-federated)
# ================================================================================

trusted_key_servers: []
suppress_key_server_warning: true

# ================================================================================
# ADDITIONAL SECURITY
# ================================================================================

# Prevent password changes (OIDC only)
password_config:
  enabled: false
  
# Session configuration
session_lifetime: 24h
refresh_token_lifetime: 7d
refresh_access_token_lifetime: 24h
refresh_refresh_token_lifetime: 7d

# User directory
user_directory:
  enabled: true
  search_all_users: false
  prefer_local_users: true

# ================================================================================
# EXPERIMENTAL FEATURES
# ================================================================================

experimental_features:
  # Disable all experimental features for stability
  msc2716_enabled: false
  msc3026_enabled: false
```

## Step 3: Configure Room Creation Policies

### 3.1 Create Room Templates
Create `matrix/room_templates/`:

```bash
mkdir -p matrix/room_templates
```

Create `matrix/room_templates/medical_dm.json`:
```json
{
  "preset": "trusted_private_chat",
  "initial_state": [
    {
      "type": "m.room.encryption",
      "content": {
        "algorithm": "m.megolm.v1.aes-sha2"
      }
    }
  ],
  "power_level_content_override": {
    "ban": 50,
    "events": {
      "m.room.encryption": 100,
      "m.room.name": 50,
      "m.room.power_levels": 50
    },
    "events_default": 0,
    "invite": 0,
    "kick": 50,
    "redact": 25,
    "state_default": 25,
    "users_default": 0
  }
}
```

### 3.2 Create Admin User Creation Script
Create `matrix/scripts/create_admin_user.py`:
```python
#!/usr/bin/env python3
"""Script to create Matrix admin user for EquipeMed superusers."""

import asyncio
import aiohttp
import json
import sys
import os

async def create_admin_user(username, is_admin=True):
    """Create or update admin user via Synapse Admin API."""
    
    # Matrix admin API configuration
    homeserver_url = "http://localhost:8008"
    admin_token = os.getenv("SYNAPSE_ADMIN_TOKEN")
    
    if not admin_token:
        print("Error: SYNAPSE_ADMIN_TOKEN environment variable not set")
        return False
    
    async with aiohttp.ClientSession() as session:
        # Create/update user
        user_data = {
            "admin": is_admin,
            "deactivated": False,
            "user_type": None
        }
        
        headers = {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
        
        user_id = f"@{username}:matrix.yourhospital.com"
        url = f"{homeserver_url}/_synapse/admin/v2/users/{user_id}"
        
        try:
            async with session.put(url, json=user_data, headers=headers) as response:
                if response.status in [200, 201]:
                    result = await response.json()
                    print(f"Successfully created/updated admin user: {user_id}")
                    return True
                else:
                    error = await response.text()
                    print(f"Failed to create user. Status: {response.status}, Error: {error}")
                    return False
                    
        except Exception as e:
            print(f"Error creating admin user: {e}")
            return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python create_admin_user.py <username>")
        sys.exit(1)
    
    username = sys.argv[1]
    asyncio.run(create_admin_user(username))
```

## Step 4: Security and Performance Tuning

### 4.1 Create Rate Limiting Configuration
Add to `matrix/homeserver.yaml` (already included above but documenting separately):

```yaml
# Additional rate limiting for medical environment
rc_invites:
  per_room:
    per_second: 0.3
    burst_count: 10
  per_user:
    per_second: 0.003
    burst_count: 5

rc_3pid_validation:
  per_second: 0.003
  burst_count: 5

rc_federation:
  window_size: 1000
  sleep_limit: 10
  sleep_delay: 500
  reject_limit: 50
  concurrent: 3
```

### 4.2 Create Monitoring Configuration
Create `matrix/monitoring.yaml`:
```yaml
# Basic monitoring for Matrix Synapse
metrics:
  enabled: false  # Disable for security
  
logging:
  version: 1
  formatters:
    precise:
      format: '%(asctime)s - %(name)s - %(lineno)d - %(levelname)s - %(message)s'
  
  handlers:
    file:
      class: logging.handlers.TimedRotatingFileHandler
      formatter: precise
      filename: /data/logs/homeserver.log
      when: midnight
      backupCount: 5
      encoding: utf8
    
    console:
      class: logging.StreamHandler
      formatter: precise
      stream: ext://sys.stdout
  
  loggers:
    synapse:
      level: INFO
    synapse.access.http:
      level: INFO
    synapse.storage.SQL:
      level: WARNING
    
  root:
    level: INFO
    handlers: [file, console]
  
  disable_existing_loggers: false
```

## Step 5: Test Matrix Configuration

### 5.1 Validate Configuration
```bash
# Test configuration syntax
docker run -it --rm \
    -v $(pwd)/matrix:/data \
    matrixdotorg/synapse:latest \
    python -m synapse.config.homeserver \
    --config-path=/data/homeserver.yaml \
    --generate-keys

# Check for configuration errors
docker run -it --rm \
    -v $(pwd)/matrix:/data \
    matrixdotorg/synapse:latest \
    python -m synapse.app.homeserver \
    --config-path=/data/homeserver.yaml \
    --generate-missing-configs
```

### 5.2 Start Matrix Synapse (Test Mode)
```bash
# Start in test mode (check logs for errors)
docker compose up matrix-synapse

# Check logs
docker compose logs matrix-synapse

# Stop after verification
docker compose stop matrix-synapse
```

### 5.3 Test Database Connection
```bash
# Verify Matrix can connect to database
docker compose exec postgres psql -U matrix_user -d matrix_db -c "
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;
"
```

## Step 6: OIDC Integration Testing

### 6.1 Test OIDC Discovery
```bash
# Test OIDC endpoints from Matrix perspective
curl -k "https://yourhospital.com/.well-known/openid_configuration"

# Test JWKS endpoint
curl -k "https://yourhospital.com/.well-known/jwks.json"
```

### 6.2 Create Test OIDC Flow Script
Create `matrix/scripts/test_oidc.py`:
```python
#!/usr/bin/env python3
"""Test OIDC flow between Matrix and EquipeMed."""

import requests
import json
from urllib.parse import urlencode, parse_qs

def test_oidc_discovery():
    """Test OIDC discovery endpoint."""
    print("Testing OIDC discovery...")
    
    try:
        response = requests.get("https://yourhospital.com/.well-known/openid_configuration")
        if response.status_code == 200:
            config = response.json()
            print("✓ OIDC discovery successful")
            print(f"  Issuer: {config.get('issuer')}")
            print(f"  Authorization endpoint: {config.get('authorization_endpoint')}")
            print(f"  Token endpoint: {config.get('token_endpoint')}")
            return True
        else:
            print(f"✗ OIDC discovery failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ OIDC discovery error: {e}")
        return False

def test_jwks_endpoint():
    """Test JWKS endpoint."""
    print("\nTesting JWKS endpoint...")
    
    try:
        response = requests.get("https://yourhospital.com/.well-known/jwks.json")
        if response.status_code == 200:
            jwks = response.json()
            keys = jwks.get('keys', [])
            print(f"✓ JWKS endpoint successful ({len(keys)} keys found)")
            for key in keys:
                print(f"  Key ID: {key.get('kid', 'unknown')}")
            return True
        else:
            print(f"✗ JWKS endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ JWKS endpoint error: {e}")
        return False

if __name__ == "__main__":
    print("Matrix OIDC Integration Test")
    print("=" * 40)
    
    discovery_ok = test_oidc_discovery()
    jwks_ok = test_jwks_endpoint()
    
    print("\n" + "=" * 40)
    if discovery_ok and jwks_ok:
        print("✓ All OIDC tests passed! Matrix can be started.")
    else:
        print("✗ Some OIDC tests failed. Check configuration.")
```

## Step 7: Admin User Management

### 7.1 Create Admin Management Script
Create `matrix/scripts/manage_admins.py`:
```python
#!/usr/bin/env python3
"""Manage Matrix admin users based on EquipeMed superusers."""

import os
import sys
import django
import asyncio
import aiohttp
import json

# Setup Django environment
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from matrix_integration.models import MatrixUser

User = get_user_model()

async def sync_admin_users():
    """Sync EquipeMed superusers as Matrix admins."""
    
    homeserver_url = "http://matrix-synapse:8008"
    admin_token = os.getenv("SYNAPSE_ADMIN_TOKEN")
    
    if not admin_token:
        print("Error: SYNAPSE_ADMIN_TOKEN not set")
        return
    
    superusers = User.objects.filter(is_superuser=True, is_active=True)
    
    async with aiohttp.ClientSession() as session:
        for user in superusers:
            await create_matrix_admin(session, homeserver_url, admin_token, user)

async def create_matrix_admin(session, homeserver_url, admin_token, user):
    """Create or update a Matrix admin user."""
    
    matrix_user_id = f"@{user.username}:matrix.yourhospital.com"
    
    user_data = {
        "admin": True,
        "deactivated": False,
        "displayname": user.get_full_name() or user.username,
        "user_type": None
    }
    
    headers = {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }
    
    url = f"{homeserver_url}/_synapse/admin/v2/users/{matrix_user_id}"
    
    try:
        async with session.put(url, json=user_data, headers=headers) as response:
            if response.status in [200, 201]:
                print(f"✓ Created/updated admin: {matrix_user_id}")
                
                # Update MatrixUser record
                matrix_user, created = MatrixUser.objects.get_or_create(
                    user=user,
                    defaults={
                        'matrix_user_id': matrix_user_id,
                        'matrix_localpart': user.username,
                        'is_active': True
                    }
                )
                if not created:
                    matrix_user.is_active = True
                    matrix_user.save()
                    
            else:
                error = await response.text()
                print(f"✗ Failed to create admin {matrix_user_id}: {error}")
                
    except Exception as e:
        print(f"✗ Error creating admin {matrix_user_id}: {e}")

if __name__ == "__main__":
    asyncio.run(sync_admin_users())
```

## Verification Commands

### Test Configuration Validity
```bash
# Check Synapse configuration
docker run -it --rm \
    -v $(pwd)/matrix:/data \
    matrixdotorg/synapse:latest \
    python -c "
from synapse.config.homeserver import HomeServerConfig
try:
    config = HomeServerConfig.load_config('homeserver.yaml', ['/data/homeserver.yaml'])
    print('✓ Configuration is valid')
except Exception as e:
    print(f'✗ Configuration error: {e}')
"
```

### Test Database Schema
```bash
# Check if Matrix database is properly initialized
docker compose exec postgres psql -U matrix_user -d matrix_db -c "
SELECT COUNT(*) as table_count 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name LIKE '%matrix%' 
  OR table_name LIKE '%synapse%';
"
```

### Test OIDC Configuration
```bash
# Run OIDC test script
cd matrix/scripts
python3 test_oidc.py
```

## File Structure Check

After Phase 3, you should have:
```
├── matrix/
│   ├── homeserver.yaml         # Main Synapse configuration
│   ├── log_config.yaml         # Updated logging configuration
│   ├── monitoring.yaml         # Monitoring configuration
│   ├── *.signing.key          # Synapse signing keys (generated)
│   ├── room_templates/        # Room configuration templates
│   │   └── medical_dm.json    # DM room template
│   └── scripts/               # Admin scripts
│       ├── create_admin_user.py
│       ├── test_oidc.py
│       └── manage_admins.py
└── .env                       # Updated with Matrix secrets
```

## Next Steps

1. ✅ **Complete Phase 3** Matrix Synapse configuration
2. ➡️ **Proceed to Phase 4** for Element web client setup
3. 🔐 **Secure admin tokens** - keep SYNAPSE_ADMIN_TOKEN safe
4. 📊 **Test OIDC flow** before starting full deployment

## Troubleshooting

### Common Configuration Issues
- **Database connection**: Verify PostgreSQL credentials and network access
- **OIDC discovery**: Ensure EquipeMed endpoints are accessible from Matrix container
- **Permission denied**: Check file permissions on signing keys

### Debug Commands
```bash
# Check Synapse logs for OIDC issues
docker compose logs matrix-synapse | grep -i oidc

# Test database connectivity
docker compose exec matrix-synapse python -c "
import psycopg2
try:
    conn = psycopg2.connect('host=postgres user=matrix_user password=matrix_secure_password_123 dbname=matrix_db')
    print('✓ Database connection successful')
    conn.close()
except Exception as e:
    print(f'✗ Database connection failed: {e}')
"

# Validate OIDC provider configuration
docker compose exec matrix-synapse python -c "
from synapse.config.oidc import OidcConfig
print('OIDC configuration validated successfully')
"
```

---

**Status**: Matrix Synapse configured with OIDC authentication and ready for Element integration