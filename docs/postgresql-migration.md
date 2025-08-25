# PostgreSQL Migration Guide

## Overview

This guide covers migrating EquipeMed from SQLite to PostgreSQL for improved performance, concurrency, and scalability. PostgreSQL is recommended for production medical environments with multiple concurrent users.

## Performance Benefits

### Before (SQLite)

- Single writer limitation causes bottlenecks
- Complex dashboard queries cause CPU spikes
- Limited concurrent access for medical team
- Write locks block all operations

### After (PostgreSQL)

- Unlimited concurrent read/write operations
- 3-5x faster complex queries and JOINs
- Better performance for 10-50+ concurrent users
- Advanced indexing and query optimization

## Prerequisites

- Existing EquipeMed installation with SQLite
- Docker and Docker Compose
- Backup of existing data (automatic via export process)

## Migration Options

### Option 1: Fresh Installation (Recommended for Greenfield)

If you're starting fresh or can recreate data easily:

**Step 1: Update Docker Compose Configuration**

Add PostgreSQL service to your `docker-compose.yml`:

```yaml
version: "3.8"

services:
  eqmd:
    # ... existing configuration ...
    depends_on:
      - postgres
    environment:
      - DATABASE_URL=postgresql://eqmd_user:${POSTGRES_PASSWORD}@postgres:5432/eqmd_db

  postgres:
    image: postgres:15-alpine
    container_name: ${CONTAINER_PREFIX:-eqmd}_postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: eqmd_db
      POSTGRES_USER: eqmd_user
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_INITDB_ARGS: "--encoding=UTF-8 --lc-collate=C --lc-ctype=C"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "127.0.0.1:${POSTGRES_PORT:-5432}:5432" # Optional: for external access
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U eqmd_user -d eqmd_db"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
    driver: local
  # ... other existing volumes ...
```

**Step 2: Update Environment Configuration**

Add to your `.env` file:

```bash
# PostgreSQL Configuration
POSTGRES_PASSWORD=your_secure_password_here_at_least_32_chars
POSTGRES_PORT=5432

# Database Configuration (replaces SQLite DATABASE_NAME)
DATABASE_URL=postgresql://eqmd_user:${POSTGRES_PASSWORD}@postgres:5432/eqmd_db

# Optional: External access port (for development/administration)
# Remove or comment out for production
POSTGRES_EXTERNAL_PORT=5432
```

**Step 3: Install PostgreSQL Dependencies**

Update your `requirements.txt` or ensure the container image includes:

```txt
psycopg2-binary>=2.9.5
```

**Step 4: Deploy and Initialize**

```bash
# Stop existing services
docker compose down

# Remove SQLite data (if starting fresh)
docker volume rm eqmd_database_data 2>/dev/null || true

# Start PostgreSQL
docker compose up -d postgres

# Wait for PostgreSQL to be ready
docker compose logs -f postgres
# Wait for "database system is ready to accept connections"

# Run migrations to create schema
docker compose run --rm eqmd python manage.py migrate

# Create superuser
docker compose run --rm eqmd python manage.py createsuperuser

# Load sample data (if desired)
docker compose run --rm eqmd python manage.py populate_sample_data

# Set up permissions
docker compose run --rm eqmd python manage.py setup_groups

# Start main application
docker compose up -d eqmd
```

### Option 2: Migration with Data Preservation

If you have existing data to preserve:

**Step 1: Export Existing SQLite Data**

```bash
# Export all data from SQLite
docker compose exec eqmd python manage.py dumpdata \
    --natural-foreign --natural-primary \
    --exclude auth.permission \
    --exclude contenttypes \
    --exclude sessions \
    > eqmd_backup.json

# Copy backup from container
docker cp $(docker compose ps -q eqmd):/app/eqmd_backup.json ./eqmd_backup.json
```

**Step 2: Add PostgreSQL Service**

Follow Step 1-2 from Option 1 to update `docker-compose.yml` and `.env`.

**Step 3: Run Migration**

```bash
# Stop services
docker compose down

# Start PostgreSQL only
docker compose up -d postgres

# Wait for PostgreSQL to be ready
sleep 30

# Create schema with migrations
docker compose run --rm eqmd python manage.py migrate

# Load data from backup
docker cp ./eqmd_backup.json $(docker compose run -d eqmd sleep 60):/app/
docker compose exec eqmd python manage.py loaddata eqmd_backup.json

# Set up permissions
docker compose run --rm eqmd python manage.py setup_groups

# Start all services
docker compose up -d
```

## Performance Optimization

### Database Configuration

Add to your PostgreSQL configuration (optional performance tuning):

```yaml
# In docker-compose.yml postgres service
postgres:
  # ... existing config ...
  command: >
    postgres
    -c shared_buffers=256MB
    -c effective_cache_size=1GB
    -c maintenance_work_mem=64MB
    -c checkpoint_completion_target=0.9
    -c wal_buffers=16MB
    -c default_statistics_target=100
    -c random_page_cost=1.1
    -c effective_io_concurrency=200
```

### Cache System Integration

With PostgreSQL, you can optimize your cache system:

**Update Cache Frequency** (in crontab):

```bash
# Reduce frequency since PostgreSQL is faster
# Dashboard stats - every 10 minutes instead of 5
*/10 * * * * cd /path && docker compose exec -T web python manage.py update_dashboard_stats

# Ward mapping - every 10 minutes offset by 5 minutes
5-59/10 * * * * cd /path && docker compose exec -T web python manage.py update_ward_mapping_cache
```

Or keep the 5-minute frequency for maximum responsiveness.

### Database Indexes

PostgreSQL automatically benefits from better indexing. Consider adding these for even better performance:

```python
# In your models.py files, add database indexes
class Patient(models.Model):
    # ... existing fields ...

    class Meta:
        indexes = [
            models.Index(fields=['status', 'ward']),
            models.Index(fields=['name']),  # For search
            models.Index(fields=['created_at']),
        ]

class Event(models.Model):
    # ... existing fields ...

    class Meta:
        indexes = [
            models.Index(fields=['patient', 'event_datetime']),
            models.Index(fields=['event_datetime']),
            models.Index(fields=['event_type', 'patient']),
        ]
```

Then run:

```bash
docker compose exec eqmd python manage.py makemigrations
docker compose exec eqmd python manage.py migrate
```

## Backup and Recovery

### Automated Backups

Create backup script `backup_postgres.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/backup/postgresql"
DATE=$(date +%Y%m%d_%H%M%S)
CONTAINER_PREFIX=${CONTAINER_PREFIX:-eqmd}

mkdir -p "$BACKUP_DIR"

# Create backup
docker compose exec -T postgres pg_dump -U eqmd_user -d eqmd_db \
    --clean --if-exists --no-owner --no-privileges \
    > "$BACKUP_DIR/eqmd_backup_$DATE.sql"

# Compress backup
gzip "$BACKUP_DIR/eqmd_backup_$DATE.sql"

# Keep only last 30 days
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +30 -delete

echo "Backup completed: eqmd_backup_$DATE.sql.gz"
```

Add to crontab for daily backups:

```bash
# Daily backup at 2 AM
0 2 * * * /path/to/backup_postgres.sh >> /var/log/eqmd/backup.log 2>&1
```

### Recovery

```bash
# Restore from backup
gunzip -c /backup/postgresql/eqmd_backup_YYYYMMDD_HHMMSS.sql.gz | \
docker compose exec -T postgres psql -U eqmd_user -d eqmd_db
```

## Monitoring and Maintenance

### Health Checks

Add PostgreSQL monitoring to your health check command:

```bash
# Check PostgreSQL health
docker compose exec postgres pg_isready -U eqmd_user -d eqmd_db

# Check database size
docker compose exec postgres psql -U eqmd_user -d eqmd_db -c "\l+"

# Check connection count
docker compose exec postgres psql -U eqmd_user -d eqmd_db -c "SELECT count(*) FROM pg_stat_activity;"
```

### Performance Monitoring

```bash
# View active queries
docker compose exec postgres psql -U eqmd_user -d eqmd_db -c "SELECT pid, usename, application_name, state, query FROM pg_stat_activity WHERE state = 'active';"

# View database statistics
docker compose exec postgres psql -U eqmd_user -d eqmd_db -c "SELECT schemaname, tablename, n_tup_ins, n_tup_upd, n_tup_del FROM pg_stat_user_tables;"
```

## Security Considerations

### Production Security

**1. Network Security**

```yaml
# Remove external port exposure for production
postgres:
  # Comment out or remove this line in production:
  # ports:
  #   - "127.0.0.1:5432:5432"
```

**2. Password Security**

- Use strong passwords (32+ characters)
- Store in secure environment variables
- Consider using Docker secrets for sensitive data

**3. Connection Security**

```bash
# Add to .env for SSL connections (if needed)
DATABASE_URL=postgresql://eqmd_user:password@postgres:5432/eqmd_db?sslmode=require
```

## Troubleshooting

### Common Issues

**1. Connection Refused**

```bash
# Check PostgreSQL is running
docker compose ps postgres

# Check logs
docker compose logs postgres

# Verify health check
docker compose exec postgres pg_isready -U eqmd_user -d eqmd_db
```

**2. Permission Denied**

```bash
# Check user permissions
docker compose exec postgres psql -U eqmd_user -d eqmd_db -c "\du"

# Reset permissions if needed
docker compose exec postgres psql -U postgres -c "ALTER USER eqmd_user CREATEDB;"
```

**3. Migration Issues**

```bash
# Check Django can connect
docker compose exec eqmd python manage.py dbshell

# Run migrations with verbosity
docker compose exec eqmd python manage.py migrate --verbosity=2

# Check migration status
docker compose exec eqmd python manage.py showmigrations
```

**4. Performance Issues**

```bash
# Check query performance
docker compose exec postgres psql -U eqmd_user -d eqmd_db -c "SELECT query, calls, mean_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"

# Analyze table statistics
docker compose exec eqmd python manage.py dbshell -c "ANALYZE;"
```

## Integration with install-minimal.sh

To integrate PostgreSQL with your installation script, add a prompt:

```bash
# Add to install-minimal.sh after cache setup
echo ""
print_prompt "Do you want to use PostgreSQL instead of SQLite? Recommended for production. (y/N): "
read -r USE_POSTGRES

if [[ $USE_POSTGRES =~ ^[Yy]$ ]]; then
    print_info "Configuring PostgreSQL database..."

    # Generate secure password
    POSTGRES_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

    # Add to .env
    cat >> .env << EOF

# PostgreSQL Configuration (added by install-minimal.sh)
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
DATABASE_URL=postgresql://eqmd_user:$POSTGRES_PASSWORD@postgres:5432/eqmd_db
EOF

    print_status "PostgreSQL configuration added to .env"
    print_info "PostgreSQL will be automatically started with the application"
else
    print_info "Using SQLite database (default)"
fi
```

## Expected Performance Results

After migration to PostgreSQL:

- **Dashboard loads**: ~100-200ms (vs 200-500ms with SQLite + cache)
- **Complex queries**: 3-5x faster execution
- **Concurrent users**: Support for 20-50+ simultaneous users
- **Cache refresh**: ~5-15 seconds (vs 10-30 seconds with SQLite)
- **Write operations**: No blocking, immediate response
- **System reliability**: Enterprise-grade durability and consistency

## Migration Checklist

- [ ] Update docker-compose.yml with PostgreSQL service
- [ ] Add PostgreSQL configuration to .env
- [ ] Export existing SQLite data (if preserving)
- [ ] Test PostgreSQL connectivity
- [ ] Run Django migrations
- [ ] Import data (if applicable)
- [ ] Update cache system frequency (optional)
- [ ] Set up automated backups
- [ ] Configure monitoring
- [ ] Update documentation and runbooks
- [ ] Train team on PostgreSQL-specific operations

This migration will significantly improve EquipeMed's performance and scalability for medical team collaboration.

