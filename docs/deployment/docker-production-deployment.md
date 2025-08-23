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

Configure nginx to handle SSL and static files. The deployment scripts automatically create a unique static files directory based on your image name to avoid conflicts in multi-hospital deployments.

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
INSTANCE_ID="${EQMD_IMAGE//[^a-zA-Z0-9]/_}"
echo "Your static files path: /var/www/eqmd_static_${INSTANCE_ID}/"

# Method 2: Look for it in your file system
ls -la /var/www/eqmd_static_*/
```

#### Step 3: Update nginx configuration

```bash
# Replace the placeholder with your actual path
STATIC_PATH="/var/www/eqmd_static_${INSTANCE_ID}/"
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

#### Example nginx configuration:

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
        # Example: /var/www/eqmd_static_ghcr_io_yourorg_eqmd_latest/
        alias /var/www/eqmd_static_YOUR_INSTANCE_ID/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Media files are served by Django application for security/permissions
    # No separate nginx location needed - handled by proxy_pass above
}
```

**Static Files Strategy**: 
- Each deployment gets a unique directory: `/var/www/eqmd_static_${INSTANCE_ID}/`
- Directory name is based on the container image name (sanitized)
- Nginx owns the directory (www-data:www-data) for optimal performance
- Updates copy fresh files without permission conflicts
- Supports multiple hospital deployments on same server

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
INSTANCE_ID="${EQMD_IMAGE//[^a-zA-Z0-9]/_}"
STATIC_FILES_PATH="/var/www/eqmd_static_${INSTANCE_ID}"

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
INSTANCE_ID="${EQMD_IMAGE//[^a-zA-Z0-9]/_}"
STATIC_FILES_PATH="/var/www/eqmd_static_${INSTANCE_ID}"

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
INSTANCE_ID="${EQMD_IMAGE//[^a-zA-Z0-9]/_}"
echo "Static files path: /var/www/eqmd_static_${INSTANCE_ID}/"
```

### Nginx Configuration Commands

```bash
# Download and configure nginx template
curl -fsSL -o /etc/nginx/sites-available/eqmd https://raw.githubusercontent.com/yourorg/eqmd/main/nginx.conf.example
STATIC_PATH="/var/www/eqmd_static_${INSTANCE_ID}/"
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

