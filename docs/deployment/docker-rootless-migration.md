# Docker Rootless Migration Guide

**Complete guide for migrating EquipeMed production deployment to Docker Rootless**

## Overview

Docker Rootless provides enhanced security by running Docker daemon and containers without root privileges. This guide shows how to migrate from regular Docker to Docker Rootless while maintaining all existing functionality.

## Benefits of Docker Rootless

### Security Advantages
- **No root access**: Docker daemon runs as regular user
- **Container isolation**: Container root (uid=0) maps to host user (no system root access)
- **Privilege containment**: No access to privileged operations or system resources
- **Attack surface reduction**: Eliminates container escape to host root

### Operational Benefits  
- **Simplified permissions**: No need for user mapping or complex ownership management
- **Cleaner architecture**: Container processes appear as host user processes
- **Better compliance**: Meets security requirements for regulated environments

## Prerequisites

- Existing EquipeMed Docker deployment
- User account with appropriate permissions
- Docker version 20.10 or later
- systemd support (for service management)

## Migration Strategy

### Current vs. Rootless Architecture

**Current Architecture:**
```
Host Root → Docker Daemon (root) → Container User (eqmd:1001)
                                 → Volume Ownership Issues
                                 → Complex Permission Management
```

**Rootless Architecture:**
```
Host User (eqmd) → Docker Daemon (eqmd) → Container Root → Host User (eqmd)
                                        → Automatic Permission Mapping
                                        → Simplified Management
```

## Step-by-Step Migration

### Phase 1: Preparation

#### 1. Create Dedicated eqmd User

```bash
# Create system user for EquipeMed (if not exists)
sudo useradd --create-home --shell /bin/bash eqmd

# Add user to docker group (for current Docker access)
sudo usermod -aG docker eqmd

# Create application directory
sudo mkdir -p /home/eqmd/eqmd-app
sudo chown -R eqmd:eqmd /home/eqmd/
```

#### 2. Backup Current Deployment

```bash
# Stop current services
docker compose down

# Backup volumes
docker run --rm -v eqmd_database:/source -v /home/eqmd/backup:/backup alpine \
  tar czf /backup/database-$(date +%Y%m%d).tar.gz -C /source .

docker run --rm -v eqmd_media_files:/source -v /home/eqmd/backup:/backup alpine \
  tar czf /backup/media-$(date +%Y%m%d).tar.gz -C /source .

# Backup configuration
cp -r /path/to/current/deployment /home/eqmd/eqmd-app/
```

#### 3. Document Current Configuration

```bash
# Record current UIDs
echo "Current Docker setup:" > /home/eqmd/migration-notes.txt
docker compose exec eqmd id >> /home/eqmd/migration-notes.txt

# Record volume locations
docker volume ls | grep eqmd >> /home/eqmd/migration-notes.txt

# Record current ports and settings
docker compose ps >> /home/eqmd/migration-notes.txt
```

### Phase 2: Install Docker Rootless

#### 1. Install Rootless Docker as eqmd User

```bash
# Switch to eqmd user
sudo -u eqmd -i

# Install rootless Docker
curl -fsSL https://get.docker.com/rootless | sh

# Add paths to shell profile
echo 'export PATH=$HOME/bin:$PATH' >> ~/.bashrc
echo 'export DOCKER_HOST=unix://$XDG_RUNTIME_DIR/docker.sock' >> ~/.bashrc
source ~/.bashrc
```

#### 2. Configure Systemd Services

```bash
# Still as eqmd user
# Enable Docker daemon to start automatically
systemctl --user enable docker.socket
systemctl --user start docker.socket

# Enable lingering (allows services to start without login)
sudo loginctl enable-linger eqmd

# Verify rootless Docker is working
docker version
```

#### 3. Configure Resource Limits (Optional)

```bash
# Increase resource limits for rootless containers
echo 'eqmd:100000:65536' | sudo tee -a /etc/subuid
echo 'eqmd:100000:65536' | sudo tee -a /etc/subgid

# Restart Docker daemon to apply changes
systemctl --user restart docker
```

### Phase 3: Update Application Configuration

#### 1. Modify docker-compose.yml

Remove user-related directives since rootless Docker handles user mapping automatically:

```yaml
# REMOVE these lines from docker-compose.yml:
# user: "${EQMD_UID:-1001}:${EQMD_GID:-1001}"
# USER_ID: ${EQMD_UID:-1001}
# GROUP_ID: ${EQMD_GID:-1001}
```

**Before (Regular Docker):**
```yaml
services:
  eqmd:
    build:
      args:
        USER_ID: ${EQMD_UID:-1001}
        GROUP_ID: ${EQMD_GID:-1001}
    user: "${EQMD_UID:-1001}:${EQMD_GID:-1001}"
    # ... rest of configuration
```

**After (Rootless Docker):**
```yaml
services:
  eqmd:
    build:
      context: .
      dockerfile: Dockerfile
    # user directive removed - handled by rootless Docker
    # ... rest of configuration unchanged
```

#### 2. Simplify Dockerfile

Remove user creation since container runs as root but maps to host user:

```dockerfile
# REMOVE these lines from Dockerfile:
# ARG USER_ID=1001
# ARG GROUP_ID=1001
# RUN groupadd -r -g ${GROUP_ID} eqmd && \
#     useradd -r -u ${USER_ID} -g eqmd eqmd
# USER eqmd
```

**Simplified Dockerfile sections:**
```dockerfile
# Before: Complex user management
ARG USER_ID=1001
ARG GROUP_ID=1001
RUN groupadd -r -g ${GROUP_ID} eqmd && \
    useradd -r -u ${USER_ID} -g eqmd eqmd
# ... install dependencies
USER eqmd

# After: Simple rootless approach
# ... install dependencies directly
# No user creation needed - rootless handles it
```

#### 3. Update Environment Variables

```bash
# Remove UID/GID variables from .env
sed -i '/EQMD_UID/d' .env
sed -i '/EQMD_GID/d' .env

# Verify clean environment
grep -E "(EQMD_UID|EQMD_GID)" .env || echo "✓ UID/GID variables removed"
```

### Phase 4: Migration Execution

#### 1. Build New Images

```bash
# As eqmd user, in /home/eqmd/eqmd-app/
cd /home/eqmd/eqmd-app/

# Build with simplified configuration
docker compose build --no-cache

# Verify image builds correctly
docker compose run --rm eqmd python manage.py --version
```

#### 2. Migrate Data

```bash
# Create new volumes
docker volume create eqmd_database_rootless
docker volume create eqmd_media_files_rootless
docker volume create eqmd_static_files_rootless

# Restore data to new volumes
docker run --rm -v /home/eqmd/backup:/backup -v eqmd_database_rootless:/target alpine \
  tar xzf /backup/database-$(date +%Y%m%d).tar.gz -C /target

docker run --rm -v /home/eqmd/backup:/backup -v eqmd_media_files_rootless:/target alpine \
  tar xzf /backup/media-$(date +%Y%m%d).tar.gz -C /target
```

#### 3. Update Volume References

```yaml
# Update docker-compose.yml volume names
volumes:
  eqmd_database_rootless:
    name: eqmd_database_rootless
  eqmd_media_files_rootless:
    name: eqmd_media_files_rootless
  eqmd_static_files_rootless:
    name: eqmd_static_files_rootless

# Update service volume mounts
services:
  eqmd:
    volumes:
      - eqmd_media_files_rootless:/app/media
      - eqmd_database_rootless:/app/database
      - eqmd_static_files_rootless:/app/staticfiles
```

### Phase 5: Testing and Verification

#### 1. Start Services

```bash
# Start database first
docker compose up -d postgres

# Run migrations
docker compose run --rm eqmd python manage.py migrate

# Start application
docker compose up -d eqmd
```

#### 2. Verify Rootless Operation

```bash
# Check container user mapping
docker compose exec eqmd id
# Should show: uid=0(root) gid=0(root) - but maps to host eqmd user

# Check host process ownership
ps aux | grep python | grep manage.py
# Should show eqmd user running the processes

# Verify file permissions
docker compose exec eqmd ls -la /app/media/
# Files should be accessible without permission issues
```

#### 3. Test Application Functionality

```bash
# Check application health
curl -f http://localhost:8778/health/ || echo "Health check failed"

# Test file uploads (if accessible)
# Try uploading a PDF form template through admin interface

# Verify database operations
docker compose exec eqmd python manage.py dbshell -c "SELECT COUNT(*) FROM django_migrations;"

# Check logs for errors
docker compose logs eqmd | grep -i error
```

### Phase 6: Production Cutover

#### 1. Update Nginx Configuration

No changes needed for nginx configuration since the application still runs on the same port.

#### 2. Update Systemd Services (if used)

```bash
# Create systemd service for rootless Docker
sudo tee /etc/systemd/system/eqmd-rootless.service > /dev/null << 'EOF'
[Unit]
Description=EquipeMed Rootless Docker Service
After=network.target

[Service]
Type=oneshot
RemainAfterExit=yes
User=eqmd
Group=eqmd
WorkingDirectory=/home/eqmd/eqmd-app
Environment=PATH=/home/eqmd/bin:/usr/local/bin:/usr/bin:/bin
Environment=DOCKER_HOST=unix:///run/user/1001/docker.sock
ExecStart=/home/eqmd/bin/docker-compose up -d
ExecStop=/home/eqmd/bin/docker-compose down
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl enable eqmd-rootless
sudo systemctl start eqmd-rootless
```

#### 3. Remove Old Docker Installation (Optional)

```bash
# Stop old Docker services
sudo systemctl stop docker
sudo systemctl disable docker

# Keep Docker installed but disable automatic startup
# This allows emergency access if needed
```

## Post-Migration Management

### Daily Operations

```bash
# All commands run as eqmd user
sudo -u eqmd -i

# Standard Docker operations work normally
docker compose ps
docker compose logs -f eqmd
docker compose restart eqmd

# Management commands
docker compose exec eqmd python manage.py collectstatic --noinput
docker compose exec eqmd python manage.py migrate
```

### Monitoring and Troubleshooting

```bash
# Check rootless Docker daemon status
systemctl --user status docker

# Monitor resource usage
docker stats

# Check user namespace mapping
cat /proc/$(pgrep -f "python.*manage.py")/uid_map

# Verify no root processes
ps aux | grep eqmd | grep -v grep
```

## Troubleshooting Common Issues

### Permission Denied Errors

```bash
# Issue: Cannot access Docker socket
# Solution: Check XDG_RUNTIME_DIR and socket path
echo $XDG_RUNTIME_DIR
ls -la $XDG_RUNTIME_DIR/docker.sock

# Issue: Volume mount permission denied
# Solution: Verify volume ownership (should be automatic with rootless)
docker volume inspect eqmd_media_files_rootless
```

### Service Startup Issues

```bash
# Issue: Docker daemon won't start
# Solution: Check user lingering and systemd status
loginctl show-user eqmd | grep Linger
systemctl --user status docker

# Issue: Containers exit immediately
# Solution: Check resource limits and cgroups v2 support
docker info | grep -i cgroup
```

### Network Connectivity Issues

```bash
# Issue: Container networking problems
# Solution: Rootless Docker uses slirp4netns - check configuration
docker network ls
docker compose exec eqmd ping 8.8.8.8

# Issue: Port binding conflicts
# Solution: Rootless Docker can only bind to high ports without privileges
# Ensure HOST_PORT > 1024 or use systemd socket activation
```

## Security Validation

### Verify Enhanced Security

```bash
# Confirm Docker daemon runs as non-root
ps aux | grep dockerd
# Should show eqmd user, not root

# Verify container processes map to host user
docker compose exec eqmd ps aux
# All processes should appear as eqmd user on host

# Test privilege escalation protection
docker compose exec eqmd sudo echo "test" 2>&1 | grep -q "sudo: command not found" && echo "✓ No sudo access"

# Verify file system isolation
docker compose exec eqmd ls /host-root 2>&1 | grep -q "No such file" && echo "✓ No host root access"
```

### Security Monitoring

```bash
# Monitor for unexpected privilege escalations
journalctl --user -u docker -f | grep -i "privilege\|root\|escalat"

# Check for unusual network activity
ss -tlnp | grep $(id -u eqmd)

# Verify container resource limits are enforced
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

## Rollback Procedure

If migration issues occur:

### Emergency Rollback

```bash
# 1. Stop rootless services
sudo -u eqmd docker compose down

# 2. Restore original Docker setup
sudo systemctl start docker
sudo systemctl enable docker

# 3. Restore from backup
# Use backup files created in Phase 1

# 4. Start original deployment
cd /path/to/original/deployment
sudo docker compose up -d
```

### Gradual Rollback

```bash
# 1. Run both systems in parallel (different ports)
# 2. Update nginx to route traffic back to original
# 3. Migrate data back if needed
# 4. Shutdown rootless deployment
```

## Best Practices

### Security
- Run all Docker commands as eqmd user
- Never use sudo with rootless Docker
- Regularly update rootless Docker components
- Monitor for privilege escalation attempts

### Operations  
- Use systemd --user for service management
- Set up proper logging and monitoring
- Document any custom configurations
- Test backup/restore procedures regularly

### Development
- Use same rootless setup in staging/development
- Update CI/CD pipelines for rootless builds
- Train team on rootless Docker differences
- Maintain documentation for troubleshooting

## Conclusion

Docker Rootless migration enhances security while simplifying permission management. The key benefits include:

- ✅ **Enhanced Security**: No root access for Docker daemon or containers
- ✅ **Simplified Permissions**: Automatic user mapping eliminates complex ownership issues  
- ✅ **Better Compliance**: Meets security requirements for regulated environments
- ✅ **Operational Clarity**: Container processes clearly visible as application user
- ✅ **Reduced Attack Surface**: Container escapes cannot gain host root access

After migration, your EquipeMed deployment will be more secure and easier to manage while maintaining all existing functionality.