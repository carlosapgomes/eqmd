# Phase 1: Infrastructure Setup

## Overview
Set up the Docker infrastructure, PostgreSQL database, and basic networking for Matrix Synapse integration.

## Prerequisites
- Existing EquipeMed deployment running
- Access to modify `docker-compose.yml`
- PostgreSQL container running
- SSL certificates configured (verify with provided commands)

## Step 1: PostgreSQL Database Setup

### 1.1 Create Matrix Database
```bash
# Connect to PostgreSQL container
docker compose exec postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB}

# Create matrix database and user
CREATE DATABASE matrix_db;
CREATE USER matrix_user WITH PASSWORD 'matrix_secure_password_123';
GRANT ALL PRIVILEGES ON DATABASE matrix_db TO matrix_user;

# Exit PostgreSQL
\q
```

### 1.2 Update Environment Variables
Add to your `.env` file:
```bash
# Matrix Synapse Configuration
MATRIX_SERVER_NAME=matrix.yourhospital.com
MATRIX_DATABASE_PASSWORD=matrix_secure_password_123
MATRIX_REGISTRATION_SHARED_SECRET=your_matrix_registration_secret_here_32_chars_min
SYNAPSE_LOG_LEVEL=INFO

# Element Configuration  
ELEMENT_SERVER_NAME=chat.yourhospital.com
```

## Step 2: Docker Compose Configuration

### 2.1 Add Matrix Services to docker-compose.yml

Add these services to your existing `docker-compose.yml`:

```yaml
  # Matrix Synapse Homeserver
  matrix-synapse:
    image: matrixdotorg/synapse:latest
    container_name: ${CONTAINER_PREFIX:-eqmd}_matrix_synapse
    restart: unless-stopped
    volumes:
      - matrix_data:/data
      - matrix_media_files:/data/media_store
      - ./matrix/homeserver.yaml:/data/homeserver.yaml:ro
      - ./matrix/log_config.yaml:/data/log_config.yaml:ro
    environment:
      - SYNAPSE_SERVER_NAME=${MATRIX_SERVER_NAME}
      - SYNAPSE_REPORT_STATS=no
    ports:
      - "127.0.0.1:8008:8008"  # Internal access only
    depends_on:
      - postgres
    networks:
      - matrix-network
      - default
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8008/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M

  # Element Web Client
  element-web:
    image: vectorim/element-web:latest
    container_name: ${CONTAINER_PREFIX:-eqmd}_element_web
    restart: unless-stopped
    volumes:
      - ./element/config.json:/app/config.json:ro
    ports:
      - "127.0.0.1:8080:80"  # Internal access only
    networks:
      - matrix-network
    depends_on:
      - matrix-synapse
    deploy:
      resources:
        limits:
          memory: 128M
        reservations:
          memory: 64M

# Add to volumes section
volumes:
  # ... existing volumes ...
  matrix_data:
    name: ${CONTAINER_PREFIX:-eqmd}_matrix_data
    driver: local
  matrix_media_files:
    name: ${CONTAINER_PREFIX:-eqmd}_matrix_media_files
    driver: local
    driver_opts:
      type: none
      o: bind,size=50G

# Add networks section (if not exists)
networks:
  matrix-network:
    driver: bridge
    name: ${CONTAINER_PREFIX:-eqmd}_matrix_network
```

### 2.2 Create Matrix Configuration Directory Structure
```bash
# Create directories for Matrix configuration
mkdir -p matrix
mkdir -p element
mkdir -p nginx/matrix
```

## Step 3: Basic Configuration Files

### 3.1 Create Matrix Log Configuration
Create `matrix/log_config.yaml`:
```yaml
version: 1

formatters:
    precise:
        format: '%(asctime)s - %(name)s - %(lineno)d - %(levelname)s - %(request)s - %(message)s'

handlers:
    console:
        class: logging.StreamHandler
        formatter: precise
        stream: ext://sys.stdout

loggers:
    synapse:
        level: INFO
    synapse.storage.SQL:
        level: INFO

root:
    level: INFO
    handlers: [console]

disable_existing_loggers: false
```

### 3.2 Create Basic Element Configuration
Create `element/config.json`:
```json
{
    "default_server_config": {
        "m.homeserver": {
            "base_url": "https://matrix.yourhospital.com",
            "server_name": "matrix.yourhospital.com"
        }
    },
    "brand": "EquipeMed Chat",
    "integrations_ui_url": "",
    "integrations_rest_url": "",
    "integrations_widgets_urls": [],
    "bug_report_endpoint_url": "",
    "defaultCountryCode": "BR",
    "showLabsSettings": false,
    "features": {
        "feature_pinning": "disable",
        "feature_custom_status": "disable",
        "feature_custom_tags": "disable",
        "feature_state_counters": "disable"
    },
    "default_federate": false,
    "default_theme": "light",
    "roomDirectory": {
        "servers": ["matrix.yourhospital.com"]
    },
    "enable_presence_by_hs_url": {
        "https://matrix.yourhospital.com": false
    },
    "setting_defaults": {
        "breadcrumbs": false
    },
    "jitsi": {
        "preferredDomain": ""
    }
}
```

### 3.3 Create Basic Nginx Configuration Template
Create `nginx/matrix/matrix.conf.template`:
```nginx
# Matrix Synapse server block
server {
    listen 80;
    server_name matrix.yourhospital.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name matrix.yourhospital.com;

    # SSL configuration (update paths as needed)
    ssl_certificate /path/to/your/certificate.pem;
    ssl_private_key /path/to/your/private-key.pem;

    # Matrix client-server API
    location ~ ^(\/_matrix|\/_synapse\/client) {
        proxy_pass http://127.0.0.1:8008;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Host $host;
        client_max_body_size 50M;
        proxy_read_timeout 60s;
        proxy_send_timeout 60s;
    }

    # Well-known files for Matrix federation (disabled but required)
    location /.well-known/matrix/server {
        return 200 '{"m.server": "matrix.yourhospital.com:443"}';
        default_type application/json;
        add_header Access-Control-Allow-Origin *;
    }

    location /.well-known/matrix/client {
        return 200 '{
            "m.homeserver": {"base_url": "https://matrix.yourhospital.com"},
            "io.element.e2ee": {"force_disable": true}
        }';
        default_type application/json;
        add_header Access-Control-Allow-Origin *;
    }
}

# Element Web client server block
server {
    listen 80;
    server_name chat.yourhospital.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name chat.yourhospital.com;

    # SSL configuration (same as matrix server)
    ssl_certificate /path/to/your/certificate.pem;
    ssl_private_key /path/to/your/private-key.pem;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Host $host;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## Step 4: Initial Deployment Test

### 4.1 Start Only Infrastructure Services
```bash
# Start PostgreSQL if not running
docker compose up -d postgres

# Create matrix database (if not done in Step 1.1)
# Run the database creation commands from Step 1.1

# Pull Matrix images (don't start yet)
docker compose pull matrix-synapse element-web
```

### 4.2 Verify Network Creation
```bash
# Check networks
docker network ls | grep matrix

# Verify PostgreSQL accessibility
docker compose exec postgres pg_isready -U matrix_user -d matrix_db
```

## Step 5: File Structure Check

After completing Phase 1, you should have:
```
├── docker-compose.yml          # Updated with Matrix services
├── .env                        # Updated with Matrix variables
├── matrix/
│   ├── log_config.yaml         # Matrix logging configuration
│   └── homeserver.yaml         # (Created in Phase 3)
├── element/
│   └── config.json             # Element web configuration
└── nginx/
    └── matrix/
        └── matrix.conf.template # Nginx configuration template
```

## Verification Commands

### Check Docker Services Status
```bash
# List all services
docker compose config --services

# Verify Matrix network
docker network inspect ${CONTAINER_PREFIX:-eqmd}_matrix_network
```

### Check PostgreSQL Matrix Database
```bash
# Connect and verify matrix_db
docker compose exec postgres psql -U matrix_user -d matrix_db -c "SELECT current_database();"
```

### Check Volume Creation
```bash
# List Matrix-related volumes
docker volume ls | grep matrix
```

## Next Steps

1. ✅ **Complete Phase 1** infrastructure setup
2. ➡️ **Proceed to Phase 2** for Django OIDC provider configuration
3. 🔄 **Do not start Matrix services yet** - wait for complete configuration

## Troubleshooting

### Common Issues
- **Network conflicts**: Ensure no port conflicts with existing services
- **Volume permissions**: Check Docker daemon can create volumes
- **PostgreSQL access**: Verify matrix_user has proper permissions

### Logs to Check
```bash
# PostgreSQL logs
docker compose logs postgres

# Network connectivity
docker network inspect ${CONTAINER_PREFIX:-eqmd}_matrix_network
```

---

**Status**: Infrastructure ready for Matrix configuration in Phase 2