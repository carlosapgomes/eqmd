# User Management and UID Conflicts

**Complete guide for handling user creation and UID conflicts in Docker-based deployments**

## Overview

EquipeMed runs as a dedicated `eqmd` system user for security isolation. This approach prevents the application from running with unnecessary privileges while maintaining proper file permissions for static assets served by nginx.

## Security Model

### Dedicated User Benefits

- **Isolation**: Application runs with minimal privileges
- **Security**: Separate from web server (nginx) and other services
- **Auditing**: Clear ownership of processes and files
- **Containment**: Limits impact of potential security breaches

### User Specifications

- **Username**: `eqmd`
- **Type**: System user (not for interactive login)
- **Shell**: `/usr/sbin/nologin` (no shell access)
- **Home Directory**: `/nonexistent` (no home directory)
- **Default UID/GID**: 1001/1001

## UID Conflict Resolution

### Why UID Conflicts Occur

UID conflicts happen when:

1. **Another service** already uses UID 1001
2. **Previous installations** left conflicting users
3. **System users** occupy the desired UID range
4. **Multiple applications** compete for the same UID

### Detection Methods

#### Check for Existing UID

```bash
# Check if UID 1001 is already in use
if getent passwd 1001 >/dev/null; then
    echo "UID 1001 is already in use by: $(getent passwd 1001 | cut -d: -f1)"
else
    echo "UID 1001 is available"
fi

# Check what the user is used for
ps -u 1001 --no-headers 2>/dev/null | wc -l
```

#### Find Available UIDs

```bash
# Check available UIDs in range 1001-1099
for uid in {1001..1099}; do
    if ! getent passwd $uid >/dev/null; then
        echo "Available UID: $uid"
        break
    fi
done

# Python script to find available UID
python3 -c "
import pwd
used_uids = {u.pw_uid for u in pwd.getpwall()}
for uid in range(1001, 1100):
    if uid not in used_uids:
        print(f'Available UID: {uid}')
        break
"
```

## Automated User Creation

### Using create_eqmd_user.sh Script

The repository includes an automated script that handles UID conflicts:

```bash
# Basic usage (uses default UID 1001)
sudo ./create_eqmd_user.sh

# Specify custom UID
sudo ./create_eqmd_user.sh 1002

# Specify both UID and GID
sudo ./create_eqmd_user.sh 1002 1003

# Use high UID to avoid conflicts
sudo ./create_eqmd_user.sh 5001

# Get help
./create_eqmd_user.sh --help
```

### Script Features

The `create_eqmd_user.sh` script:

- **Detects existing eqmd user** and reuses if present
- **Handles UID conflicts** by finding alternatives automatically
- **Creates system user** with proper security settings
- **Exports environment variables** for Docker integration
- **Provides detailed feedback** and troubleshooting info
- **Validates user creation** before proceeding

### Manual User Creation

If you need to create the user manually:

```bash
# Find available UID
AVAILABLE_UID=$(python3 -c "
import pwd
used_uids = {u.pw_uid for u in pwd.getpwall()}
for uid in range(1001, 1100):
    if uid not in used_uids:
        print(uid)
        break
")

# Create group
sudo groupadd -r -g $AVAILABLE_UID eqmd

# Create user
sudo useradd -r -u $AVAILABLE_UID -g eqmd -s /usr/sbin/nologin -d /nonexistent eqmd

# Verify creation
id eqmd

# Export for Docker
export EQMD_UID=$AVAILABLE_UID
export EQMD_GID=$AVAILABLE_UID
```

## Docker Integration

### Dockerfile User Mapping

The Dockerfile uses build arguments to match host user:

```dockerfile
# Create app user with configurable UID/GID
ARG USER_ID=1001
ARG GROUP_ID=1001
RUN groupadd -r -g ${GROUP_ID} eqmd && \
    useradd -r -u ${USER_ID} -g eqmd eqmd
```

### Docker Compose Configuration

The docker-compose.yml file uses environment variables:

```yaml
services:
  eqmd:
    build:
      args:
        USER_ID: ${EQMD_UID:-1001}
        GROUP_ID: ${EQMD_GID:-1001}
```

### Build Process

```bash
# Set environment variables (done by create_eqmd_user.sh)
export EQMD_UID=1002  # Example: conflict resolved to 1002
export EQMD_GID=1002

# Build with matching UIDs
docker compose build --build-arg USER_ID=$EQMD_UID --build-arg GROUP_ID=$EQMD_GID eqmd

# Or let docker-compose handle it automatically
docker compose build eqmd
```

## Static File Permissions

### Permission Strategy

Static files use a dual-ownership approach:

- **Built in container**: Owned by www-data (UID 33) for nginx serving
- **Application files**: Owned by eqmd user for security

### Implementation

```dockerfile
# Copy static files from build stage and set www-data ownership
COPY --from=static-builder --chown=33:33 /app/static /app/staticfiles
RUN chmod -R 755 /app/staticfiles
```

### Volume Permissions

Named volumes maintain proper permissions:

- **Container creates files** with www-data ownership
- **Nginx reads files** directly from volume
- **No runtime permission fixes** needed

## Troubleshooting

### Common Issues

#### UID Already Exists

```bash
# Error: UID 1001 already exists
# Solution: Let create_eqmd_user.sh find alternative
sudo ./create_eqmd_user.sh
# Script will automatically use next available UID
```

#### Permission Denied

```bash
# Error: Permission denied when creating user
# Solution: Run with sudo
sudo ./create_eqmd_user.sh
```

#### Docker Build Fails

```bash
# Error: groupadd: GID 1001 already exists
# Solution: Check environment variables
echo "EQMD_UID: $EQMD_UID"
echo "EQMD_GID: $EQMD_GID"

# Rebuild with correct UIDs
docker compose build --no-cache eqmd
```

### Verification Commands

```bash
# Verify user exists and has correct UID/GID
id eqmd

# Check user is system user
getent passwd eqmd

# Verify no login shell
su - eqmd  # Should fail with "This account is currently not available"

# Check Docker container user
docker run --rm eqmd:latest id

# Verify static file permissions in volume
docker volume inspect eqmd_static_files
ls -la /var/lib/docker/volumes/eqmd_static_files/_data/
```

### Reset User (if needed)

```bash
# Remove existing user (if safe to do so)
sudo userdel eqmd
sudo groupdel eqmd

# Recreate with different UID
sudo ./create_eqmd_user.sh 1002

# Rebuild Docker image
docker compose build --no-cache eqmd
```

## Best Practices

### Development Environment

```bash
# Use consistent UIDs across team
echo "EQMD_UID=1001" >> .env.local
echo "EQMD_GID=1001" >> .env.local

# Document any UID conflicts in team
# Create team-specific create_eqmd_user script if needed
```

### Production Environment

```bash
# Always use create_eqmd_user.sh script
# Never manually hardcode UIDs in production
# Test user creation in staging first
# Document actual UIDs used in deployment logs
```

### CI/CD Integration

```bash
# In CI/CD pipelines
# Use fixed UIDs that don't conflict with common services
export EQMD_UID=5001
export EQMD_GID=5001
docker build --build-arg USER_ID=$EQMD_UID --build-arg GROUP_ID=$EQMD_GID
```

### Security Considerations

1. **Never run as root** - Always use dedicated user
2. **Use system users** - Prevent interactive login
3. **Limit privileges** - No unnecessary group memberships
4. **Audit regularly** - Check user permissions periodically
5. **Monitor processes** - Track what runs as eqmd user

### Monitoring

```bash
# Check processes running as eqmd user
ps -u eqmd

# Monitor file ownership
find /app -not -user eqmd 2>/dev/null

# Verify Docker container user
docker exec eqmd-container id
```

## Recovery Procedures

### Complete User Reset

```bash
#!/bin/bash
# reset_eqmd_user.sh

# Stop services
docker compose down

# Remove user
sudo userdel eqmd 2>/dev/null || true
sudo groupdel eqmd 2>/dev/null || true

# Remove environment variables
unset EQMD_UID EQMD_GID
rm -f /tmp/eqmd_user_env

# Recreate user
sudo ./create_eqmd_user.sh

# Source new environment
source /tmp/eqmd_user_env

# Rebuild and restart
docker compose build --no-cache eqmd
docker compose up -d eqmd
```

This comprehensive user management approach ensures secure, conflict-free deployment while maintaining operational flexibility and security best practices.

