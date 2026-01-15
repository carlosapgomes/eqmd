# Matrix Synapse Phase 1: Infrastructure Setup Guide

This guide provides step-by-step instructions to set up the Matrix Synapse infrastructure for EquipeMed integration.

## Overview

Phase 1 focuses on setting up the basic infrastructure without OIDC integration:
- Docker services (Synapse + Element Web)
- PostgreSQL database setup
- Configuration generation system
- Nginx reverse proxy templates
- Federation disabled for security

## Prerequisites

- Docker and Docker Compose installed
- PostgreSQL container running (from existing EquipeMed setup)
- Python with `uv` package manager
- Sudo access for database operations

## Step-by-Step Setup

### 1. Environment Configuration

First, update your `.env` file with Matrix-specific variables:

```bash
# Matrix Synapse Configuration
EQMD_DOMAIN=yourhospital.com
MATRIX_FQDN=matrix.yourhospital.com
CHAT_FQDN=chat.yourhospital.com
MATRIX_PUBLIC_BASEURL=https://matrix.yourhospital.com/
OIDC_ISSUER=https://yourhospital.com/o

# Matrix Database (separate from main EquipeMed database)
MATRIX_DATABASE_PASSWORD=change_this_matrix_password_in_production_123

# Matrix Service Versions (pin for reproducible deployments)
SYNAPSE_VERSION=v1.99.0
ELEMENT_VERSION=v1.11.58

# Matrix Service Ports (localhost-only, proxied by nginx)
MATRIX_SYNAPSE_PORT=8008
MATRIX_ELEMENT_PORT=8080

# Docker User Configuration (for development)
EQMD_UID=1000
EQMD_GID=1000
```

**Important:** Replace `yourhospital.com` with your actual domain name.

### 2. Generate Matrix Configurations

Generate the Matrix and Element Web configuration files:

```bash
uv run python scripts/generate_matrix_configs.py
```

Expected output:
```
INFO: Matrix Configuration Generator
INFO: ==============================
INFO: ✓ matrix/homeserver.yaml created
INFO: ✓ element/config.json created
INFO: ✓ nginx/matrix.conf created
INFO: ✓ nginx/element.conf created
INFO: ✓ Successfully processed 4/4 templates
```

### 3. Start PostgreSQL

Ensure PostgreSQL is running:

```bash
docker compose up -d postgres
```

Wait for PostgreSQL to be ready:
```bash
docker compose logs postgres
```

### 4. Bootstrap Matrix Database

Create the Matrix database and user with proper permissions:

```bash
POSTGRES_HOST=localhost \
POSTGRES_PORT=5432 \
POSTGRES_USER=eqmd_user \
POSTGRES_PASSWORD=eqmd_dev_password_123 \
POSTGRES_DB=eqmd_dev \
MATRIX_DATABASE_PASSWORD=change_this_matrix_password_in_production_123 \
uv run python scripts/bootstrap_matrix_db.py
```

Expected output:
```
INFO: ✓ Matrix database bootstrap completed successfully
INFO: ✓ Matrix database connection test successful
```

### 5. Generate Synapse Signing Keys

Generate the cryptographic signing keys for Synapse:

```bash
docker run --rm \
  -v $(pwd)/matrix:/data \
  -u 1000:1000 \
  -e SYNAPSE_SERVER_NAME=matrix.yourdomain.com \
  -e SYNAPSE_REPORT_STATS=no \
  matrixdotorg/synapse:v1.99.0 generate
```

### 6. Start Matrix Services

Start the Matrix services:

```bash
docker compose up -d matrix-synapse element-web
```

### 7. Verify Services

Check that services are running:

```bash
docker compose ps
```

Test the Synapse API:
```bash
curl http://localhost:8008/_matrix/client/versions
```

Expected response:
```json
{
  "versions": [
    "r0.0.1",
    "r0.1.0",
    "r0.2.0",
    ...
  ]
}
```

Test Element Web:
```bash
curl http://localhost:8080
```

Should return HTML content.

### 8. Check Logs

Monitor the services for any issues:

```bash
# View Synapse logs
docker compose logs matrix-synapse

# View Element Web logs  
docker compose logs element-web

# Follow logs in real-time
docker compose logs -f matrix-synapse element-web
```

## File Structure Created

After completing the setup, you should have:

```
matrix/
├── homeserver.yaml.template      # Synapse config template
├── homeserver.yaml              # Generated Synapse config
├── log_config.yaml              # Logging configuration
├── signing.key                  # Synapse signing key (auto-generated)
├── logs/                        # Log directory
└── media_store/                 # Media files storage

element/
├── config.json.template         # Element Web config template
└── config.json                 # Generated Element Web config

nginx/
├── matrix.conf.template         # Synapse nginx template
├── matrix.conf                 # Generated nginx config for Synapse
├── element.conf.template        # Element Web nginx template
├── element.conf                # Generated nginx config for Element
└── README.md                   # Nginx setup instructions

scripts/
├── bootstrap_matrix_db.py       # Database bootstrap script
├── generate_matrix_configs.py   # Configuration generator
└── setup_matrix_permissions.sh  # Permissions setup helper
```

## Configuration Details

### Matrix Synapse Configuration

Key security settings applied:

- **Federation disabled**: `federation_enabled: false`
- **Registration disabled**: Only admin/bot can create users
- **E2EE disabled**: Enforced server-side
- **OIDC ready**: Configuration commented out for Phase 1
- **Rate limiting**: Conservative limits applied
- **Room creation restricted**: Only admin/bot can create rooms

### Element Web Configuration

- **Single server**: Points to your Matrix homeserver only
- **Simplified UI**: Experimental features disabled
- **SSO ready**: Configured for OIDC integration
- **Branding**: "EquipeMed Chat"

### Docker Services

- **matrix-synapse**: Runs on port 8008 (localhost only)
- **element-web**: Runs on port 8080 (localhost only)  
- **Network isolation**: Services communicate via Docker network
- **User mapping**: Runs as your development user (UID/GID 1000)

## Production Deployment

### Nginx Configuration

1. **Copy nginx configs to your nginx sites**:
   ```bash
   sudo cp nginx/matrix.conf /etc/nginx/sites-available/matrix-yourdomain.com
   sudo cp nginx/element.conf /etc/nginx/sites-available/element-yourdomain.com
   ```

2. **Enable the sites**:
   ```bash
   sudo ln -sf /etc/nginx/sites-available/matrix-yourdomain.com /etc/nginx/sites-enabled/
   sudo ln -sf /etc/nginx/sites-available/element-yourdomain.com /etc/nginx/sites-enabled/
   ```

3. **Update SSL certificate paths** in the config files.

4. **Test and reload nginx**:
   ```bash
   sudo nginx -t
   sudo systemctl reload nginx
   ```

### Environment Variables for Production

Update your production `.env` with actual values:

```bash
EQMD_DOMAIN=youractualDomain.com
MATRIX_FQDN=matrix.youractualDomain.com  
CHAT_FQDN=chat.youractualDomain.com
MATRIX_DATABASE_PASSWORD=strong_secure_password_here
```

Then regenerate configs:
```bash
uv run python scripts/generate_matrix_configs.py
```

## Troubleshooting

### Common Issues

#### 1. Permission Denied Errors
```
PermissionError: [Errno 13] Permission denied: '/data/signing.key'
```

**Solution:** Fix permissions with the setup script:
```bash
sudo ./scripts/setup_matrix_permissions.sh
```

#### 2. Database Connection Failed
```
password authentication failed for user "matrix_user"
```

**Solution:** Re-run the database bootstrap:
```bash
POSTGRES_HOST=localhost POSTGRES_PORT=5432 POSTGRES_USER=eqmd_user \
POSTGRES_PASSWORD=eqmd_dev_password_123 POSTGRES_DB=eqmd_dev \
MATRIX_DATABASE_PASSWORD=your_password \
uv run python scripts/bootstrap_matrix_db.py
```

#### 3. Schema Permission Denied
```
psycopg2.errors.InsufficientPrivilege: permission denied for schema public
```

**Solution:** The bootstrap script automatically fixes this. If it persists, run:
```bash
uv run python scripts/bootstrap_matrix_db.py --verbose
```

#### 4. Configuration Errors
```
Config is missing macaroon_secret_key
```

**Solution:** Synapse auto-generates this on first startup. Just restart:
```bash
docker compose restart matrix-synapse
```

#### 5. OIDC Connection Refused
```
ConnectionRefusedError: Connection was refused by other side
```

**Solution:** This is expected in Phase 1. OIDC is disabled until Phase 2.

### Validation Commands

Verify everything is working:

```bash
# Check services are running
docker compose ps

# Test Synapse API
curl http://localhost:8008/_matrix/client/versions

# Test Element Web  
curl -I http://localhost:8080

# Check database connection
POSTGRES_HOST=localhost POSTGRES_PORT=5432 POSTGRES_USER=matrix_user \
POSTGRES_PASSWORD=change_this_matrix_password_in_production_123 \
POSTGRES_DB=matrix_db \
psql -h localhost -U matrix_user -d matrix_db -c "SELECT version();"

# Verify configuration
uv run python scripts/generate_matrix_configs.py --check
```

## What's Next

After completing Phase 1, you're ready for:

- **Phase 2**: OIDC Provider configuration in EquipeMed Django
- **Phase 3**: Synapse OIDC client configuration  
- **Phase 4**: Element Web well-known setup
- **Phase 5**: Policy bot and lifecycle management
- **Phase 6**: Testing and deployment

## Security Notes

### Federation Isolation

This setup completely disables Matrix federation:
- `federation_enabled: false` in Synapse config
- No federation listeners exposed  
- Nginx blocks `/_matrix/federation/*` endpoints
- No federation ports (8448) exposed

### Access Control

- Only localhost access to Synapse (port 8008) and Element (port 8080)
- Production access only through nginx reverse proxy
- Database access restricted to `matrix_user` with minimal permissions
- No registration allowed (admin/bot controlled)

### Data Isolation  

- Separate PostgreSQL database (`matrix_db`) for Matrix data
- Separate Docker volumes for Matrix media storage
- No shared data with EquipeMed application database

## Support

If you encounter issues:

1. Check the logs: `docker compose logs matrix-synapse element-web`
2. Verify configurations: `uv run python scripts/generate_matrix_configs.py --check`
3. Test database connectivity with the bootstrap script
4. Review this documentation for common troubleshooting steps

For Phase 2 (OIDC integration), see: `docs/matrix/phase2-oidc-provider.md`