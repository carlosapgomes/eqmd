# Registry-Based Docker Deployment Migration Plan

**Comprehensive plan to migrate from rebuild-based to registry-based deployment**

## Overview

This plan migrates the current Docker deployment strategy from rebuilding images on production servers to a registry-based approach with optimized static file serving using named volumes and multi-stage builds.

## Current Issues Being Addressed

1. **Inefficient rebuilds** - Complete image rebuild for every update
2. **Complex permission management** - Manual static file copying with permission fixes
3. **Deployment downtime** - Service interruption during rebuild process
4. **Error-prone static files** - Manual copying between container and nginx

## New Architecture

### Registry-Based Workflow

```
Development → CI/CD Pipeline → Container Registry → Production Deployment
     ↓              ↓                    ↓                    ↓
  Code Push    Build & Test         Tagged Images      Pull & Deploy
```

### Static Files Strategy

- **Multi-stage Docker build** with separate static asset compilation
- **Named volumes** for sharing static files between containers
- **Pre-set ownership** to www-data (UID 33) during build
- **Nginx direct serving** from shared volume for optimal performance

## User Management Strategy

### Dedicated User Approach

The application runs as a dedicated `eqmd` user for security isolation. This section covers how to handle UID/GID conflicts and user creation.

### Default UID/GID Assignment

- **Default**: UID=1001, GID=1001
- **Rationale**: Avoids conflicts with system users (0-999) and common service users
- **Configurable**: Can be changed if conflicts exist

### Handling UID Conflicts

#### 1. Check for Existing UID 1001

```bash
# Check if UID 1001 is already in use
if getent passwd 1001 >/dev/null; then
    echo "UID 1001 is already in use by: $(getent passwd 1001 | cut -d: -f1)"
    echo "Choose alternative UID or remove conflicting user"
fi

# Check available UIDs in range 1001-1099
for uid in {1001..1099}; do
    if ! getent passwd $uid >/dev/null; then
        echo "Available UID: $uid"
        break
    fi
done
```

#### 2. Resolution Options

**Option A: Use Alternative UID**

```bash
# Find next available UID
AVAILABLE_UID=$(python3 -c "
import pwd
used_uids = {u.pw_uid for u in pwd.getpwall()}
for uid in range(1001, 1100):
    if uid not in used_uids:
        print(uid)
        break
")

# Set environment variables for deployment
export EQMD_UID=$AVAILABLE_UID
export EQMD_GID=$AVAILABLE_UID
```

**Option B: Remove Conflicting User (if safe)**

```bash
# Only if the conflicting user is not system-critical
# Check what the user is used for first
sudo userdel -r conflicting_user_name
```

**Option C: Use Fixed High UID**

```bash
# Use UID in high range to avoid conflicts
export EQMD_UID=5001
export EQMD_GID=5001
```

### Production Deployment User Creation

#### Automated User Creation Script

```bash
#!/bin/bash
# create_eqmd_user.sh

REQUESTED_UID=${1:-1001}
REQUESTED_GID=${2:-1001}

# Function to find available UID
find_available_uid() {
    local start_uid=$1
    for ((uid=start_uid; uid<start_uid+100; uid++)); do
        if ! getent passwd $uid >/dev/null; then
            echo $uid
            return
        fi
    done
    echo "ERROR: No available UID found in range $start_uid-$((start_uid+99))" >&2
    exit 1
}

# Check if eqmd user already exists
if getent passwd eqmd >/dev/null; then
    EXISTING_UID=$(id -u eqmd)
    EXISTING_GID=$(id -g eqmd)
    echo "eqmd user already exists with UID:$EXISTING_UID GID:$EXISTING_GID"
    export EQMD_UID=$EXISTING_UID
    export EQMD_GID=$EXISTING_GID
    exit 0
fi

# Check if requested UID is available
if getent passwd $REQUESTED_UID >/dev/null; then
    CONFLICTING_USER=$(getent passwd $REQUESTED_UID | cut -d: -f1)
    echo "WARNING: UID $REQUESTED_UID is already used by: $CONFLICTING_USER"

    # Find alternative
    AVAILABLE_UID=$(find_available_uid $REQUESTED_UID)
    echo "Using alternative UID: $AVAILABLE_UID"
    REQUESTED_UID=$AVAILABLE_UID
    REQUESTED_GID=$AVAILABLE_UID
fi

# Create user and group
groupadd -r -g $REQUESTED_GID eqmd
useradd -r -u $REQUESTED_UID -g eqmd -s /usr/sbin/nologin -d /nonexistent eqmd

echo "Created eqmd user with UID:$REQUESTED_UID GID:$REQUESTED_GID"
export EQMD_UID=$REQUESTED_UID
export EQMD_GID=$REQUESTED_GID
```

#### Usage Examples

```bash
# Use default UID 1001
sudo ./create_eqmd_user.sh

# Specify alternative UID
sudo ./create_eqmd_user.sh 1002

# Use high UID to avoid conflicts
sudo ./create_eqmd_user.sh 5001
```

### Integration with Docker Build

#### Docker Compose with Dynamic UID

```yaml
services:
  eqmd:
    build:
      context: .
      dockerfile: Dockerfile
      args:
        USER_ID: ${EQMD_UID:-1001}
        GROUP_ID: ${EQMD_GID:-1001}
    environment:
      - EQMD_UID=${EQMD_UID:-1001}
      - EQMD_GID=${EQMD_GID:-1001}
```

#### Build Command

```bash
# Build with detected UID/GID
docker compose build --build-arg USER_ID=$EQMD_UID --build-arg GROUP_ID=$EQMD_GID eqmd
```

## Implementation Plan

### Phase 1: Update Dockerfile for Multi-Stage Build

**File:** `Dockerfile`

```dockerfile
# Stage 1: Node.js build for static assets
FROM node:18-alpine AS static-builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY assets/ ./assets/
COPY webpack.config.js ./
RUN npm run build

# Stage 2: Python application
FROM python:3.11-slim
WORKDIR /app

# Create app user with configurable UID/GID
ARG USER_ID=1001
ARG GROUP_ID=1001
RUN groupadd -r -g ${GROUP_ID} eqmd && \
    useradd -r -u ${USER_ID} -g eqmd eqmd

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .
RUN chown -R eqmd:eqmd /app

# Copy static files from build stage and set www-data ownership
COPY --from=static-builder --chown=33:33 /app/static /app/staticfiles
RUN chmod -R 755 /app/staticfiles

# Django collectstatic (ensures all static files are gathered)
USER eqmd
RUN python manage.py collectstatic --noinput

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Expose port
EXPOSE 8000

# Start application
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "config.wsgi:application"]
```

### Phase 2: Update docker-compose.yml

**File:** `docker-compose.yml`

```yaml
version: "3.8"

services:
  eqmd:
    image: ${EQMD_IMAGE:-eqmd:latest}
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8778:8000"
    env_file:
      - .env
    volumes:
      - ./media:/app/media
      - ./db.sqlite3:/app/db.sqlite3
      - static_files:/app/staticfiles
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # Static file initialization container
  static-init:
    image: ${EQMD_IMAGE:-eqmd:latest}
    volumes:
      - static_files:/shared/static
    command: |
      sh -c "
        echo 'Copying static files to shared volume...' &&
        cp -r /app/staticfiles/* /shared/static/ 2>/dev/null || true &&
        echo 'Static files copied successfully'
      "
    profiles: ["init"]

volumes:
  static_files:
    driver: local
```

### Phase 3: Registry Integration

**File:** `.github/workflows/build-and-push.yml` (if using GitHub Actions)

```yaml
name: Build and Push Docker Image

on:
  push:
    branches: [main, dev]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=sha
            type=raw,value=latest,enable={{is_default_branch}}

      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
```

### Phase 4: Update Nginx Configuration

**File:** Example nginx configuration update

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    # Static files served directly by nginx from shared volume
    location /static/ {
        alias /var/lib/docker/volumes/eqmd_static_files/_data/;
        expires 1y;
        add_header Cache-Control "public, immutable";
        add_header X-Served-By "nginx-static";
    }

    # Application requests proxied to container
    location / {
        proxy_pass http://localhost:8778;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Media files still served by Django for security
    # No separate nginx location needed
}
```

### Phase 5: Updated install.sh Script

**Major changes:**

- Remove Docker build step (pull from registry instead)
- Simplify static file handling (use init container)
- Add registry authentication
- Update environment variable handling

**Key sections:**

```bash
# Create eqmd user with conflict resolution
print_info "Setting up eqmd user..."
source ./create_eqmd_user.sh
print_status "eqmd user configured with UID:$EQMD_UID GID:$EQMD_GID"

# Registry configuration
print_info "Configuring container registry..."
if [ -n "$REGISTRY_TOKEN" ]; then
    echo "$REGISTRY_TOKEN" | docker login ghcr.io -u "$REGISTRY_USER" --password-stdin
    print_status "Registry authentication configured"
fi

# Pull image instead of building
print_info "Pulling latest Docker image..."
EQMD_IMAGE="${REGISTRY:-ghcr.io/yourorg/eqmd}:${TAG:-latest}"
docker pull "$EQMD_IMAGE"
export EQMD_IMAGE
print_status "Docker image pulled successfully"

# Initialize static files
print_info "Initializing static files..."
docker compose --profile init run --rm static-init
print_status "Static files initialized"

# Start services
print_info "Starting production services..."
docker compose up -d eqmd
```

### Phase 6: Updated upgrade.sh Script

**Major changes:**

- Replace build with pull
- Simplify static file management
- Add rollback capability
- Health check validation

**Key sections:**

```bash
# Backup current deployment
print_info "Creating deployment backup..."
BACKUP_TAG="backup-$(date +%Y%m%d-%H%M%S)"
CURRENT_IMAGE=$(docker inspect eqmd_eqmd_1 --format='{{.Config.Image}}' 2>/dev/null || echo "unknown")
if [ "$CURRENT_IMAGE" != "unknown" ]; then
    docker tag "$CURRENT_IMAGE" "eqmd:$BACKUP_TAG"
    print_status "Current image backed up as eqmd:$BACKUP_TAG"
fi

# Pull new image
print_info "Pulling updated Docker image..."
NEW_IMAGE="${REGISTRY:-ghcr.io/yourorg/eqmd}:${TAG:-latest}"
docker pull "$NEW_IMAGE"
export EQMD_IMAGE="$NEW_IMAGE"

# Graceful update with health check
print_info "Performing graceful update..."
docker compose up -d eqmd

# Wait and verify health
print_info "Waiting for health check..."
for i in {1..30}; do
    if curl -f -s http://localhost:8778/health/ >/dev/null; then
        print_status "Health check passed"
        break
    fi
    if [ $i -eq 30 ]; then
        print_error "Health check failed - rolling back"
        docker tag "eqmd:$BACKUP_TAG" eqmd:latest
        docker compose up -d eqmd
        exit 1
    fi
    sleep 2
done

# Update static files
print_info "Updating static files..."
docker compose --profile init run --rm static-init
```

## Migration Steps

### Step 1: Prepare Registry

1. Choose registry (GitHub Container Registry, Docker Hub, or private)
2. Configure authentication credentials
3. Set up CI/CD pipeline for automated builds

### Step 2: Update Docker Configuration

1. Replace current Dockerfile with multi-stage version
2. Update docker-compose.yml with named volumes
3. Test locally to ensure static files work correctly

### Step 3: Update Deployment Scripts

1. Modify install.sh to pull instead of build
2. Update upgrade.sh with registry-based workflow
3. Add rollback capabilities

### Step 4: Update Documentation

#### Required Documentation Updates

**1. Main Project README.md**

- Add registry-based deployment quickstart
- Update development setup instructions
- Add Docker Hub/registry links
- Update contribution guidelines for Docker workflow

**2. docs/deployment/docker-production-deployment.md**

- Replace rebuild sections with registry workflow
- Add user management documentation
- Update nginx configuration examples
- Add troubleshooting section for registry issues

**3. New Documentation Files**

- `docs/deployment/registry-setup.md` - Container registry setup
- `docs/deployment/user-management.md` - UID conflict resolution
- `docs/deployment/rollback-procedures.md` - Deployment rollback guide
- `docs/development/docker-development.md` - Local development with registry images

**4. Installation Scripts Documentation**

- Update install.sh and upgrade.sh inline documentation
- Create man-page style help for scripts
- Add troubleshooting section in each script

**5. Docker Compose Documentation**

- Comment docker-compose.yml extensively
- Create docker-compose.prod.yml with production-specific settings
- Document environment variable requirements

#### Documentation Migration Checklist

**Phase 1: Core Documentation**

- [x] Update main README.md with registry quickstart
- [x] Migrate docker-production-deployment.md to registry-based
- [x] Create registry-setup.md
- [x] Create user-management.md

**Phase 2: Operational Documentation**

- [x] Create rollback-procedures.md
- [x] Update troubleshooting sections
- [x] Create docker-development.md
- [x] Add monitoring and health check guides

**Phase 3: Script Documentation**

- [x] Add comprehensive help to install.sh
- [x] Add help and error handling to upgrade.sh
- [x] Create create_eqmd_user.sh script
- [x] Document all environment variables

**Phase 4: Examples and Templates**

- [x] Create docker-compose.prod.yml template
- [x] Create .env.example with registry variables
- [x] Add nginx configuration templates
- [x] Create CI/CD workflow examples

### Step 5: Test Migration

1. Test full deployment on staging environment
2. Verify static file serving works correctly
3. Test upgrade and rollback procedures
4. Performance testing for static file serving

### Step 6: Production Migration

1. Build and push current version to registry
2. Update production environment variables
3. Execute migration during maintenance window
4. Monitor and validate deployment

## Deployment Options

### Option 1: Minimal Registry-Only Deployment

```bash
# Download compose file and scripts
wget https://raw.githubusercontent.com/yourorg/eqmd/main/docker-compose.prod.yml
wget https://raw.githubusercontent.com/yourorg/eqmd/main/install-minimal.sh
chmod +x install-minimal.sh

# Configure and deploy
./install-minimal.sh
```

### Option 2: Full Clone (For Customization)

```bash
# Clone repository for customization
git clone https://github.com/yourorg/eqmd.git
cd eqmd
./install.sh
```

## Benefits After Migration

### Performance Improvements

- **Faster deployments** - Pull vs rebuild (30s vs 5+ minutes)
- **Optimal static serving** - nginx direct file serving
- **Reduced downtime** - Faster container startup

### Operational Benefits

- **Consistent environments** - Same image dev to prod
- **Easy rollbacks** - Tagged image versions
- **Simplified permissions** - No runtime permission fixes
- **Better monitoring** - Health checks and container status

### Development Benefits

- **CI/CD integration** - Automated builds and testing
- **Version control** - Tagged releases with history
- **Environment parity** - Identical images across environments

## Risk Mitigation

### Rollback Plan

1. Keep previous image tagged as backup
2. Quick rollback command: `docker tag eqmd:backup eqmd:latest && docker compose up -d`
3. Database backup before major upgrades

### Testing Strategy

1. Staging environment validation
2. Health check verification
3. Static file serving confirmation
4. Performance baseline comparison

### Monitoring

1. Container health checks
2. Static file availability monitoring
3. Application performance metrics
4. Deployment success/failure tracking

## Timeline

- **Week 1:** Update Dockerfile and docker-compose.yml, local testing
- **Week 2:** Set up registry and CI/CD pipeline
- **Week 3:** Update deployment scripts and documentation
- **Week 4:** Staging environment testing and validation
- **Week 5:** Production migration during scheduled maintenance

## Success Criteria

1. **Deployment time** reduced by 80%+ (from ~5min to <1min)
2. **Static file serving** performance equivalent or better than current
3. **Zero-downtime deployments** achieved
4. **Rollback capability** tested and functional
5. **Documentation** updated and validated by team

This plan provides a comprehensive migration path that addresses all current deployment inefficiencies while maintaining reliability and adding new capabilities for better operational management.
