# Docker Production Deployment Guide

**Step-by-step guide for deploying EquipeMed in production using Docker**

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

Configure nginx to handle SSL and static files. The Docker setup automatically copies static files to `/var/www/equipemed/static/`:

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
        alias /var/www/equipemed/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Media files are served by Django application for security/permissions
    # No separate nginx location needed - handled by proxy_pass above
}
```

**Note**: Media files (`/media/`) are served by the Django application to enforce proper authentication and permissions. Only static files are served directly by nginx for performance.

## Maintenance Commands

### Update Application

```bash
# Use the upgrade script for automated updates
sudo ./upgrade.sh
```

**Manual update process:**
```bash
# Copy updated code to server first
docker compose build eqmd

# Fix permissions BEFORE starting container to allow file copy
sudo chown -R eqmd:eqmd /var/www/equipemed/
docker compose up -d eqmd

# Wait for container to start, then manually copy static files
sleep 10
CONTAINER_ID=$(docker compose ps -q eqmd)
docker exec $CONTAINER_ID sh -c "cp -rv /app/staticfiles/* /var/www/equipemed/static/"

# Fix static files permissions for nginx AFTER copy
sudo chown -R www-data:www-data /var/www/equipemed/
sudo chmod -R 755 /var/www/equipemed/
```

**Note**: The automatic copy during container startup may fail silently due to permission issues. The manual copy step ensures all static files (including PWA files) are properly deployed.

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
sudo chown -R www-data:www-data /var/www/equipemed/
sudo chmod -R 755 /var/www/equipemed/

# If static files are not updating, check container logs
docker-compose logs eqmd | grep -i "operation not permitted"
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
- [ ] Firewall rules applied
- [ ] Monitoring set up
- [ ] Log rotation configured
- [ ] Backup strategy implemented
- [ ] Update procedure documented

