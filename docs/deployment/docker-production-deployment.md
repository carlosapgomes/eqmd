# Docker Production Deployment Guide

**Complete guide for registry-based EquipeMed production deployment**

⚠️ **This guide has been updated for registry-based deployment**

- Faster deployments (pull vs rebuild)
- Improved static file handling with named volumes
- Automated user management with UID conflict resolution
- Built-in rollback procedures and health checks

📖 **See also:**

- [Registry Setup Guide](registry-setup.md) - Container registry configuration
- [User Management Guide](user-management.md) - UID conflict resolution
- [Rollback Procedures](rollback-procedures.md) - Emergency rollback guide

## Prerequisites

- Docker and Docker Compose installed
- Git installed
- Domain name configured (for production use)
- SSL certificate (recommended)

## Multi-Deployment Configuration

The deployment system supports multiple EquipeMed instances on the same server through configurable container prefixes and ports. This enables scenarios like:

- **Hospital with staging**: `hospital_prod` and `hospital_staging`
- **Multi-hospital server**: `hospital_a` and `hospital_b`
- **Version testing**: `current` and `testing`

### Configuration Variables

Set these in your `.env` file:

```bash
# Multi-deployment configuration
CONTAINER_PREFIX=eqmd              # Unique identifier for this deployment
HOST_PORT=8778                     # Host port for this instance
DEV_PORT=8779                     # Development port (HOST_PORT + 1)

# Registry configuration
REGISTRY=ghcr.io                  # Container registry
EQMD_IMAGE=ghcr.io/yourorg/eqmd:latest  # Full image path
```

### Example Multi-Deployment Scenarios

#### Hospital with Staging Environment

**Production (.env.prod)**:

```bash
CONTAINER_PREFIX=hospital_prod
HOST_PORT=8778
EQMD_IMAGE=ghcr.io/yourorg/eqmd:latest
```

**Staging (.env.staging)**:

```bash
CONTAINER_PREFIX=hospital_staging
HOST_PORT=8779
EQMD_IMAGE=ghcr.io/yourorg/eqmd:staging
```

#### Multi-Hospital Server

**Hospital A (.env.hospital_a)**:

```bash
CONTAINER_PREFIX=hospital_a
HOST_PORT=8778
EQMD_IMAGE=ghcr.io/yourorg/eqmd:latest
```

**Hospital B (.env.hospital_b)**:

```bash
CONTAINER_PREFIX=hospital_b
HOST_PORT=8780
EQMD_IMAGE=ghcr.io/yourorg/eqmd:latest
```

## Production Deployment Steps

### 1. Checkout Project

```bash
git clone https://github.com/carlosapgomes/eqmd.git
cd eqmd
```

### 2. Create eqmd System User

```bash
# Create dedicated system user for EquipeMed (no login shell)
sudo useradd --system --no-create-home --shell /usr/sbin/nologin eqmd

# Verify user was created with correct UID
id eqmd
# Should show: uid=1001(eqmd) gid=1001(eqmd) groups=1001(eqmd)
```

### 3. Create Required Directories and Fix Permissions

```bash
mkdir -p media staticfiles
chmod 755 media staticfiles

# Fix ownership for Docker compatibility
sudo chown -R eqmd:eqmd .
sudo chown -R eqmd:eqmd /var/www/equipemed/
```

### 4. Set Production Environment Variables

```bash
# Create environment file
cat > .env.prod << EOF
DEBUG=False
SECRET_KEY=your-super-secret-production-key-here
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
HOSPITAL_NAME=Your Hospital Name
HOSPITAL_ADDRESS=Your Hospital Address
HOSPITAL_PHONE=+1-555-123-4567
HOSPITAL_EMAIL=contact@yourhospital.com
HOSPITAL_PDF_FORMS_ENABLED=true
EOF
```

**Important**: Replace the values above with your actual production settings.

### 5. Build the Docker Image

```bash
# Set eqmd user IDs for permission compatibility
export USER_ID=$(id -u eqmd)
export GROUP_ID=$(id -g eqmd)

# Build with matching user IDs
docker compose build eqmd
```

### 6. Run Database Migrations

```bash
docker compose run --rm eqmd python manage.py migrate
```

### 7. Create Superuser

```bash
docker compose run --rm eqmd python manage.py createsuperuser
```

### 8. Load Sample Data (Optional)

```bash
docker compose run --rm eqmd python manage.py create_sample_tags
docker compose run --rm eqmd python manage.py create_sample_wards
docker compose run --rm eqmd python manage.py create_sample_content
docker compose run --rm eqmd python manage.py create_sample_pdf_forms
```

### 9. Start Production Services

```bash
docker compose up -d eqmd

# Fix static files permissions for nginx
sudo chown -R www-data:www-data /var/www/equipemed/
sudo chmod -R 755 /var/www/equipemed/
```

### 10. Verify Deployment

```bash
# Check container status
docker compose ps

# Check logs
docker compose logs eqmd

# Test application
curl http://localhost:8778
```

### 11. Setup Reverse Proxy (Recommended)

Configure nginx to handle SSL and static files. The deployment scripts automatically create a unique static files directory based on your container prefix and image name to avoid conflicts in multi-deployment scenarios.

#### Step 1: Download nginx configuration template

```bash
# Download the nginx configuration template
curl -fsSL -o /etc/nginx/sites-available/eqmd https://raw.githubusercontent.com/yourorg/eqmd/main/nginx.conf.example

# Or copy the example file if you have the repository
cp nginx.conf.example /etc/nginx/sites-available/eqmd
```

#### Step 2: Find your static files path

The installation script shows your static files path. You can also determine it manually:

```bash
# Method 1: Check your .env file
source .env
CONTAINER_PREFIX=${CONTAINER_PREFIX:-eqmd}
INSTANCE_ID="${EQMD_IMAGE//[^a-zA-Z0-9]/_}"
echo "Your static files path: /var/www/${CONTAINER_PREFIX}_static_${INSTANCE_ID}/"

# Method 2: Look for it in your file system
ls -la /var/www/${CONTAINER_PREFIX}_static_*/
```

#### Step 3: Update nginx configuration

```bash
# Replace the placeholder with your actual path
CONTAINER_PREFIX=${CONTAINER_PREFIX:-eqmd}
INSTANCE_ID="${EQMD_IMAGE//[^a-zA-Z0-9]/_}"
STATIC_PATH="/var/www/${CONTAINER_PREFIX}_static_${INSTANCE_ID}/"
sed -i "s|/var/www/eqmd_static_YOUR_INSTANCE_ID/|$STATIC_PATH|g" /etc/nginx/sites-available/eqmd

# Update server name
sed -i 's/yourdomain.com/your-actual-domain.com/g' /etc/nginx/sites-available/eqmd
```

#### Step 4: Enable and test configuration

```bash
# Enable the site
ln -s /etc/nginx/sites-available/eqmd /etc/nginx/sites-enabled/

# Test configuration
nginx -t

# Reload nginx
systemctl reload nginx
```

#### Example nginx configuration

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:8778;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        # Replace with your actual static files path shown during installation
        # Examples: /var/www/hospital_a_static_ghcr_io_yourorg_eqmd_latest/
        #           /var/www/eqmd_static_ghcr_io_yourorg_eqmd_latest/
        alias /var/www/eqmd_static_YOUR_INSTANCE_ID/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Media files are served by Django application for security/permissions
    # No separate nginx location needed - handled by proxy_pass above
}
```

**Static Files Strategy**:

- Each deployment gets a unique directory: `/var/www/${CONTAINER_PREFIX}_static_${INSTANCE_ID}/`
- Directory name is based on container prefix + sanitized image name
- Nginx owns the directory (www-data:www-data) for optimal performance
- Updates copy fresh files without permission conflicts
- Supports multiple hospital deployments on same server
- Container prefix enables flexible deployment scenarios (staging, multi-hospital, version testing)

**Note**: Media files (`/media/`) are served by the Django application to enforce proper authentication and permissions. Only static files are served directly by nginx for performance.

## Maintenance Commands

### Update Application

```bash
# Use the upgrade script for automated updates
sudo ./upgrade.sh
```

**Manual update process:**

```bash
# Pull updated image or build locally
docker pull your-registry/eqmd:latest
# OR: docker compose build eqmd

# Start updated container
docker compose up -d eqmd

# Update static files to unique directory
CONTAINER_PREFIX=${CONTAINER_PREFIX:-eqmd}
INSTANCE_ID="${EQMD_IMAGE//[^a-zA-Z0-9]/_}"
STATIC_FILES_PATH="/var/www/${CONTAINER_PREFIX}_static_${INSTANCE_ID}"

# Collect and copy static files
docker compose run --rm --user root eqmd python manage.py collectstatic --noinput
TEMP_CONTAINER_ID=$(docker compose run --rm -d eqmd sleep 30)
sudo docker cp "${TEMP_CONTAINER_ID}:/app/staticfiles/." "$STATIC_FILES_PATH/"
docker stop "$TEMP_CONTAINER_ID" && docker rm "$TEMP_CONTAINER_ID"

# Fix permissions for nginx
sudo chown -R www-data:www-data "$STATIC_FILES_PATH"
sudo chmod -R 755 "$STATIC_FILES_PATH"
```

**Benefits of this approach:**

- No permission conflicts during updates
- Nginx always has read access to static files
- Multiple hospital deployments can coexist
- Updates are more reliable and predictable

### Stop Services

```bash
# Stop the service
docker-compose stop eqmd

# Stop and remove containers
docker-compose down

# Stop and remove containers with volumes (⚠️ removes all data)
docker-compose down -v
```

### Remove Services and Clean Up

```bash
# Remove stopped containers
docker-compose rm eqmd

# Remove containers and networks
docker-compose down

# Remove everything including images (complete cleanup)
docker-compose down --rmi all

# Remove unused Docker resources
docker system prune -a
```

### Backup Database

```bash
cp db.sqlite3 db.sqlite3.backup.$(date +%Y%m%d)
```

### View Logs

```bash
# Follow logs in real-time
docker-compose logs -f eqmd

# View recent logs
docker-compose logs --tail=100 eqmd
```

### Access Container Shell

```bash
docker-compose exec eqmd bash
```

### Run Management Commands

```bash
# Run any Django management command
docker-compose run --rm eqmd python manage.py <command>

# Examples:
docker-compose run --rm eqmd python manage.py collectstatic --noinput
docker-compose run --rm eqmd python manage.py setup_groups
docker-compose run --rm eqmd python manage.py permission_audit --action=report
```

## Security Considerations

1. **Environment Variables**: Never commit `.env.prod` to version control
2. **Secret Key**: Generate a strong, unique secret key for production
3. **HTTPS**: Always use SSL/TLS in production
4. **Firewall**: Restrict access to port 8778, use reverse proxy instead
5. **Updates**: Regularly update Docker images and dependencies
6. **Backups**: Schedule regular database backups
7. **Monitoring**: Set up application and container monitoring

## Troubleshooting

### Container Won't Start

```bash
# Check detailed logs
docker-compose logs eqmd

# Check container status
docker-compose ps

# Rebuild image
docker-compose build --no-cache eqmd
```

### Database Issues

```bash
# Reset database (⚠️ DESTRUCTIVE)
docker-compose run --rm eqmd python manage.py flush --noinput
docker-compose run --rm eqmd python manage.py migrate
```

### Permission Issues

```bash
# Fix media directory permissions (for container access)
sudo chown -R $(whoami):$(whoami) media
chmod 755 media

# Fix static files permissions (for nginx access)
# First determine your static files path:
CONTAINER_PREFIX=${CONTAINER_PREFIX:-eqmd}
INSTANCE_ID="${EQMD_IMAGE//[^a-zA-Z0-9]/_}"
STATIC_FILES_PATH="/var/www/${CONTAINER_PREFIX}_static_${INSTANCE_ID}"

sudo chown -R www-data:www-data "$STATIC_FILES_PATH"
sudo chmod -R 755 "$STATIC_FILES_PATH"

# If static files are not updating, check container logs
docker compose logs eqmd | grep -i "operation not permitted"

# Verify static files directory exists and has correct permissions
ls -la "$STATIC_FILES_PATH"
```

### Nginx Configuration Issues

```bash
# Check if nginx can access static files directory
sudo -u www-data test -r "$STATIC_FILES_PATH" && echo "✓ Nginx can read static files" || echo "✗ Permission issue"

# Test static file serving
curl -I http://localhost/static/admin/css/base.css

# Check nginx error logs
tail -f /var/log/nginx/error.log

# Verify nginx configuration includes your site
nginx -T | grep -A 10 -B 5 "eqmd_static"

# Test nginx configuration syntax
nginx -t
```

### Performance Issues

```bash
# Check resource usage
docker stats

# Scale workers (modify docker-compose.yml)
# Change: --workers 3 to --workers 5
```

## Production Checklist

- [ ] Domain name configured
- [ ] SSL certificate installed
- [ ] Environment variables set
- [ ] Database backed up
- [ ] Reverse proxy configured
- [ ] Nginx static files path updated
- [ ] Static files permissions verified
- [ ] Firewall rules applied
- [ ] Monitoring set up
- [ ] Log rotation configured
- [ ] Backup strategy implemented
- [ ] Update procedure documented

## Quick Reference

### Static Files Path Determination

```bash
# Get your static files path
source .env
CONTAINER_PREFIX=${CONTAINER_PREFIX:-eqmd}
INSTANCE_ID="${EQMD_IMAGE//[^a-zA-Z0-9]/_}"
echo "Static files path: /var/www/${CONTAINER_PREFIX}_static_${INSTANCE_ID}/"
```

### Nginx Configuration Commands

```bash
# Download and configure nginx template
curl -fsSL -o /etc/nginx/sites-available/eqmd https://raw.githubusercontent.com/yourorg/eqmd/main/nginx.conf.example
CONTAINER_PREFIX=${CONTAINER_PREFIX:-eqmd}
INSTANCE_ID="${EQMD_IMAGE//[^a-zA-Z0-9]/_}"
STATIC_PATH="/var/www/${CONTAINER_PREFIX}_static_${INSTANCE_ID}/"
sed -i "s|/var/www/eqmd_static_YOUR_INSTANCE_ID/|$STATIC_PATH|g" /etc/nginx/sites-available/eqmd
sed -i 's/yourdomain.com/your-actual-domain.com/g' /etc/nginx/sites-available/eqmd
ln -s /etc/nginx/sites-available/eqmd /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

### Static Files Update (Manual)

```bash
# After container update, refresh static files
docker compose run --rm --user root eqmd python manage.py collectstatic --noinput
TEMP_CONTAINER_ID=$(docker compose run --rm -d eqmd sleep 30)
sudo docker cp "${TEMP_CONTAINER_ID}:/app/staticfiles/." "$STATIC_PATH/"
docker stop "$TEMP_CONTAINER_ID" && docker rm "$TEMP_CONTAINER_ID"
sudo chown -R www-data:www-data "$STATIC_PATH"
sudo chmod -R 755 "$STATIC_PATH"
```

## Multi-Deployment Management

### Managing Multiple Deployments

When running multiple EquipeMed instances, each deployment creates its own:

- Container name: `${CONTAINER_PREFIX}_app`
- Database volume: `${CONTAINER_PREFIX}_database`
- Media volume: `${CONTAINER_PREFIX}_media_files`
- Static volume: `${CONTAINER_PREFIX}_static_files`
- Static directory: `/var/www/${CONTAINER_PREFIX}_static_${INSTANCE_ID}/`
- Host port: `${HOST_PORT}`

### Example: Managing Hospital with Staging

**Production Environment**:

```bash
cd /path/to/hospital-prod
source .env  # CONTAINER_PREFIX=hospital_prod, HOST_PORT=8778
docker compose ps
docker compose logs -f eqmd
```

**Staging Environment**:

```bash
cd /path/to/hospital-staging
source .env  # CONTAINER_PREFIX=hospital_staging, HOST_PORT=8779
docker compose ps
docker compose logs -f eqmd
```

### Multi-Deployment Nginx Configuration

For multiple deployments, create separate nginx configuration files:

**Production nginx config** (`/etc/nginx/sites-available/hospital-prod`):

```nginx
server {
    listen 80;
    server_name prod.yourhospital.com;

    location /static/ {
        alias /var/www/hospital_prod_static_ghcr_io_yourorg_eqmd_latest/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    location / {
        proxy_pass http://localhost:8778;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Staging nginx config** (`/etc/nginx/sites-available/hospital-staging`):

```nginx
server {
    listen 80;
    server_name staging.yourhospital.com;

    location /static/ {
        alias /var/www/hospital_staging_static_ghcr_io_yourorg_eqmd_staging/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    location / {
        proxy_pass http://localhost:8779;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Multi-Deployment Commands

```bash
# List all EquipeMed containers
docker ps --filter name="_app"

# List all EquipeMed volumes
docker volume ls --filter name="_database"
docker volume ls --filter name="_media_files"

# List all static directories
ls -la /var/www/*_static_*/

# Cleanup unused multi-deployment resources
docker volume prune
docker system prune
```

## PWA (Progressive Web App) Deployment

**EquipeMed includes PWA functionality that requires special nginx configuration in production.**

### PWA Issue: Shows "Open" Instead of "Install"

**Problem**: In development, the PWA shows "Install to Home Screen" option, but in production it only shows "Open EquipeMed".

**Root Cause**: The issue occurs because:
1. **Manifest served incorrectly**: nginx serves static files directly, but the manifest is now dynamic (`/manifest.json`)
2. **Service Worker caching fails**: nginx doesn't set the correct `Content-Type` headers for PWA files
3. **HTTPS requirements**: PWAs require HTTPS in production (except localhost)

### PWA Nginx Configuration Fix

Add these location blocks to your nginx configuration **BEFORE** the general `location /` block:

```nginx
# PWA Manifest - must be served by Django with correct Content-Type
location = /manifest.json {
    proxy_pass http://localhost:8778;  # Adjust port for your deployment
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # Prevent caching of manifest in nginx
    add_header Cache-Control "no-cache, must-revalidate";
    expires off;
}

# Service Worker - needs special headers for PWA
location = /static/sw.js {
    alias /var/www/eqmd_static_YOUR_INSTANCE_ID/sw.js;  # Replace with your path
    
    # Service Worker specific headers
    add_header Content-Type "text/javascript; charset=utf-8";
    add_header Cache-Control "no-cache, must-revalidate";
    add_header Service-Worker-Allowed "/";
    expires off;
}
```

### Complete PWA-Compatible Nginx Configuration

Here's a complete nginx server block with PWA support:

```nginx
server {
    listen 443 ssl http2;  # HTTPS required for PWA
    server_name yourdomain.com www.yourdomain.com;
    
    # SSL configuration (required for PWA installation)
    ssl_certificate /path/to/your/certificate.crt;
    ssl_certificate_key /path/to/your/private.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    
    # PWA Manifest - served by Django
    location = /manifest.json {
        proxy_pass http://localhost:8778;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        add_header Cache-Control "no-cache, must-revalidate";
        expires off;
    }
    
    # Service Worker - special handling
    location = /static/sw.js {
        alias /var/www/eqmd_static_YOUR_INSTANCE_ID/sw.js;
        add_header Content-Type "text/javascript; charset=utf-8";
        add_header Cache-Control "no-cache, must-revalidate";
        add_header Service-Worker-Allowed "/";
        expires off;
    }
    
    # Regular static files
    location /static/ {
        alias /var/www/eqmd_static_YOUR_INSTANCE_ID/;
        expires 1y;
        add_header Cache-Control "public, immutable";
        add_header X-Served-By "nginx-static";
        
        gzip on;
        gzip_vary on;
        gzip_types
            text/css
            text/javascript
            application/javascript
            application/json;
    }
    
    # Application requests
    location / {
        proxy_pass http://localhost:8778;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    # Security headers for PWA
    add_header X-Frame-Options SAMEORIGIN always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
}

# Redirect HTTP to HTTPS (required for PWA)
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

### PWA Requirements Checklist

✅ **HTTPS**: Required for PWA installation (except localhost)  
✅ **Manifest**: Must be served with `application/manifest+json` Content-Type  
✅ **Service Worker**: Must be served with correct headers and scope  
✅ **Icons**: Multiple sizes (192x192 and 512x512 minimum) must be accessible  
✅ **Scope**: Service worker scope must cover the app's start URL  

### PWA Troubleshooting

#### Check PWA Status in Browser DevTools

1. **Open DevTools** → **Application** tab
2. **Manifest section**: Verify manifest loads without errors
3. **Service Workers section**: Verify service worker registers successfully
4. **Install prompt**: Check if installability criteria are met

#### Common Issues and Solutions

**"Open" instead of "Install"**:
- ❌ **Issue**: Browser thinks PWA is already installed or criteria not met
- ✅ **Fix**: Clear browser data, check HTTPS, verify manifest Content-Type

**Service Worker fails to register**:
- ❌ **Issue**: nginx serving service worker with wrong Content-Type
- ✅ **Fix**: Add service worker location block with correct headers

**Manifest not loading**:
- ❌ **Issue**: nginx serves `/static/manifest.json` but app requests `/manifest.json`
- ✅ **Fix**: Use dynamic manifest served by Django with proper Content-Type

#### Testing PWA Installation

```bash
# Test manifest endpoint
curl -I https://yourdomain.com/manifest.json
# Should return: Content-Type: application/manifest+json

# Test service worker
curl -I https://yourdomain.com/static/sw.js
# Should return: Content-Type: text/javascript

# Test PWA icons
curl -I https://yourdomain.com/static/images/pwa/icon-192x192.png
# Should return: Content-Type: image/png
```

### Alternative: Django-Only Static Files

If nginx configuration is complex, you can disable nginx static file serving and let Django handle everything:

```nginx
# Remove /static/ location block and let Django handle all static files
location / {
    proxy_pass http://localhost:8778;
    # ... proxy headers
}
```

This is less efficient but simpler for PWA compatibility.
