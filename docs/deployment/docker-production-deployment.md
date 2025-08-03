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

### 2. Create Required Directories

```bash
mkdir -p media staticfiles
chmod 755 media staticfiles
```

### 3. Set Production Environment Variables

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

### 4. Build the Docker Image

```bash
docker-compose build web
```

### 5. Run Database Migrations

```bash
docker-compose run --rm web python manage.py migrate
```

### 6. Create Superuser

```bash
docker-compose run --rm web python manage.py createsuperuser
```

### 7. Load Sample Data (Optional)

```bash
docker-compose run --rm web python manage.py create_sample_tags
docker-compose run --rm web python manage.py create_sample_wards
docker-compose run --rm web python manage.py create_sample_content
docker-compose run --rm web python manage.py create_sample_pdf_forms
```

### 8. Start Production Services

```bash
docker-compose up -d web
```

### 9. Verify Deployment

```bash
# Check container status
docker-compose ps

# Check logs
docker-compose logs web

# Test application
curl http://localhost:8000
```

### 10. Setup Reverse Proxy (Recommended)

Configure nginx or similar to handle SSL and static files:

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /path/to/eqmd/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /path/to/eqmd/media/;
        expires 1y;
        add_header Cache-Control "public";
    }
}
```

## Maintenance Commands

### Update Application

```bash
git pull
docker-compose build web
docker-compose up -d web
```

### Backup Database

```bash
cp db.sqlite3 db.sqlite3.backup.$(date +%Y%m%d)
```

### View Logs

```bash
# Follow logs in real-time
docker-compose logs -f web

# View recent logs
docker-compose logs --tail=100 web
```

### Access Container Shell

```bash
docker-compose exec web bash
```

### Run Management Commands

```bash
# Run any Django management command
docker-compose run --rm web python manage.py <command>

# Examples:
docker-compose run --rm web python manage.py collectstatic --noinput
docker-compose run --rm web python manage.py setup_groups
docker-compose run --rm web python manage.py permission_audit --action=report
```

## Security Considerations

1. **Environment Variables**: Never commit `.env.prod` to version control
2. **Secret Key**: Generate a strong, unique secret key for production
3. **HTTPS**: Always use SSL/TLS in production
4. **Firewall**: Restrict access to port 8000, use reverse proxy instead
5. **Updates**: Regularly update Docker images and dependencies
6. **Backups**: Schedule regular database backups
7. **Monitoring**: Set up application and container monitoring

## Troubleshooting

### Container Won't Start

```bash
# Check detailed logs
docker-compose logs web

# Check container status
docker-compose ps

# Rebuild image
docker-compose build --no-cache web
```

### Database Issues

```bash
# Reset database (⚠️ DESTRUCTIVE)
docker-compose run --rm web python manage.py flush --noinput
docker-compose run --rm web python manage.py migrate
```

### Permission Issues

```bash
# Fix media directory permissions
sudo chown -R $(whoami):$(whoami) media
chmod 755 media
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

