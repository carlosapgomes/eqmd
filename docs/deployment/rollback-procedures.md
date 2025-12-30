# Deployment Rollback Procedures

**Comprehensive guide for rolling back EquipeMed deployments safely and quickly**

## Overview

This guide covers rollback procedures for the registry-based deployment system, including emergency rollbacks, version-specific rollbacks, and database recovery procedures.

## Rollback Strategy

### Backup System

Every upgrade automatically creates:

- **Docker image backup** with timestamp tag
- **Environment snapshot** of current deployment
- **Static files backup** in named volume
- **Database backup** (manual, recommended before upgrades)

### Rollback Types

1. **Emergency Rollback** - Immediate rollback to previous version
2. **Version-Specific Rollback** - Rollback to specific tagged version
3. **Partial Rollback** - Rollback only static files or database
4. **Full System Recovery** - Complete system restoration

## Quick Emergency Rollback

### Immediate Rollback (< 1 minute)

```bash
#!/bin/bash
# emergency_rollback.sh

# Use the most recent backup created by upgrade.sh
LATEST_BACKUP=$(docker images --format "table {{.Repository}}:{{.Tag}}" | grep "eqmd:backup-" | head -1 | cut -d':' -f2)

if [ -n "$LATEST_BACKUP" ]; then
    echo "🚨 Emergency rollback to $LATEST_BACKUP"
    
    # Tag backup as current
    docker tag "eqmd:$LATEST_BACKUP" eqmd:latest
    
    # Restart with backup image
    docker compose up -d eqmd
    
    echo "✅ Rollback completed"
    echo "🔍 Check logs: docker compose logs -f eqmd"
else
    echo "❌ No backup images found"
    exit 1
fi
```

### Manual Emergency Rollback

```bash
# Stop current container
docker compose stop eqmd

# Find latest backup
docker images | grep "eqmd.*backup-"

# Tag backup as current (replace TIMESTAMP with actual backup)
docker tag eqmd:backup-20241219-143022 eqmd:latest

# Restart service
docker compose up -d eqmd

# Verify rollback
curl -f http://localhost:8778/health/
```

## Version-Specific Rollback

### Rollback to Specific Registry Version

```bash
#!/bin/bash
# rollback_to_version.sh

TARGET_VERSION=${1:-"latest"}
REGISTRY=${REGISTRY:-"ghcr.io/yourorg/eqmd"}

echo "🔄 Rolling back to version: $TARGET_VERSION"

# Pull specific version
docker pull "$REGISTRY:$TARGET_VERSION"

# Update environment
export EQMD_IMAGE="$REGISTRY:$TARGET_VERSION"

# Deploy specific version
docker compose up -d eqmd

# Verify health
for i in {1..30}; do
    if curl -f -s http://localhost:8778/health/ >/dev/null; then
        echo "✅ Health check passed for version $TARGET_VERSION"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Health check failed for version $TARGET_VERSION"
        exit 1
    fi
    sleep 2
done

echo "🎉 Rollback to $TARGET_VERSION completed successfully"
```

### Usage Examples

```bash
# Rollback to latest stable
./rollback_to_version.sh latest

# Rollback to specific version
./rollback_to_version.sh v1.2.0

# Rollback to previous SHA
./rollback_to_version.sh sha-abc123

# Rollback to development version
./rollback_to_version.sh dev
```

## Database Rollback

### Pre-Upgrade Database Backup

**Always create backup before upgrades:**

```bash
#!/bin/bash
# backup_database.sh

BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# SQLite backup (default)
if [ -f "db.sqlite3" ]; then
    cp db.sqlite3 "$BACKUP_DIR/db.sqlite3"
    echo "✅ SQLite database backed up to $BACKUP_DIR/db.sqlite3"
fi

# PostgreSQL backup (if using PostgreSQL)
if [ "$DATABASE_ENGINE" = "django.db.backends.postgresql" ] && [ -n "$DATABASE_HOST" ]; then
    PGPASSWORD="$DATABASE_PASSWORD" pg_dump -h "$DATABASE_HOST" -p "$DATABASE_PORT" -U "$DATABASE_USER" -d "$DATABASE_NAME" > "$BACKUP_DIR/database.sql"
    echo "✅ PostgreSQL database backed up to $BACKUP_DIR/database.sql"
fi

# Create backup manifest
cat > "$BACKUP_DIR/manifest.txt" << EOF
Backup created: $(date)
Database type: $(if [ -f "db.sqlite3" ]; then echo "SQLite"; else echo "PostgreSQL"; fi)
Application version: $(docker inspect eqmd-eqmd-1 --format='{{.Config.Image}}' 2>/dev/null || echo "unknown")
Git commit: $(git rev-parse HEAD 2>/dev/null || echo "unknown")
EOF

echo "📋 Backup manifest created at $BACKUP_DIR/manifest.txt"
echo "💾 Total backup size: $(du -sh "$BACKUP_DIR" | cut -f1)"
```

### Database Restoration

```bash
#!/bin/bash
# restore_database.sh

BACKUP_PATH=${1:-"./backups/latest"}

if [ ! -d "$BACKUP_PATH" ]; then
    echo "❌ Backup directory not found: $BACKUP_PATH"
    exit 1
fi

echo "🔄 Restoring database from $BACKUP_PATH"

# Stop application
docker compose stop eqmd

# SQLite restore
if [ -f "$BACKUP_PATH/db.sqlite3" ]; then
    cp "$BACKUP_PATH/db.sqlite3" ./db.sqlite3
    echo "✅ SQLite database restored"
fi

# PostgreSQL restore
if [ -f "$BACKUP_PATH/database.sql" ]; then
    if [ "$DATABASE_ENGINE" = "django.db.backends.postgresql" ] && [ -n "$DATABASE_HOST" ]; then
        PGPASSWORD="$DATABASE_PASSWORD" psql -h "$DATABASE_HOST" -p "$DATABASE_PORT" -U "$DATABASE_USER" -d "$DATABASE_NAME" < "$BACKUP_PATH/database.sql"
        echo "✅ PostgreSQL database restored"
    else
        echo "❌ DATABASE_* variables not configured for PostgreSQL restore"
        exit 1
    fi
fi

# Restart application
docker compose up -d eqmd

echo "🎉 Database restoration completed"
```

## Static Files Rollback

### Static Files Backup

Static files are automatically managed by the named volume system, but you can create manual backups:

```bash
#!/bin/bash
# backup_static_files.sh

BACKUP_DIR="./static_backups/$(date +%Y%m%d_%H%M%S)"
VOLUME_PATH="/var/lib/docker/volumes/eqmd_static_files/_data"

mkdir -p "$BACKUP_DIR"

if [ -d "$VOLUME_PATH" ]; then
    cp -r "$VOLUME_PATH"/* "$BACKUP_DIR/"
    echo "✅ Static files backed up to $BACKUP_DIR"
    echo "📁 Files backed up: $(find "$BACKUP_DIR" -type f | wc -l)"
else
    echo "❌ Static files volume not found at $VOLUME_PATH"
    exit 1
fi
```

### Static Files Restoration

```bash
#!/bin/bash
# restore_static_files.sh

BACKUP_PATH=${1:-"./static_backups/latest"}
VOLUME_PATH="/var/lib/docker/volumes/eqmd_static_files/_data"

if [ ! -d "$BACKUP_PATH" ]; then
    echo "❌ Backup directory not found: $BACKUP_PATH"
    exit 1
fi

echo "🔄 Restoring static files from $BACKUP_PATH"

# Stop application to avoid conflicts
docker compose stop eqmd

# Clear current static files
rm -rf "$VOLUME_PATH"/*

# Restore from backup
cp -r "$BACKUP_PATH"/* "$VOLUME_PATH/"

# Set proper permissions
chown -R 33:33 "$VOLUME_PATH"
chmod -R 755 "$VOLUME_PATH"

# Restart application
docker compose up -d eqmd

echo "✅ Static files restored from $BACKUP_PATH"
echo "📁 Files restored: $(find "$VOLUME_PATH" -type f | wc -l)"
```

## Automated Rollback Scripts

### Complete System Rollback

```bash
#!/bin/bash
# complete_rollback.sh

BACKUP_TIMESTAMP=${1:-$(ls -1 ./backups/ | tail -1)}

echo "🚨 Performing complete system rollback to $BACKUP_TIMESTAMP"

# Rollback database
echo "📄 Rolling back database..."
./restore_database.sh "./backups/$BACKUP_TIMESTAMP"

# Rollback static files
echo "📁 Rolling back static files..."
./restore_static_files.sh "./static_backups/$BACKUP_TIMESTAMP"

# Rollback application
echo "🐳 Rolling back application..."
BACKUP_TAG="backup-$(echo $BACKUP_TIMESTAMP | tr '_' '-')"
docker tag "eqmd:$BACKUP_TAG" eqmd:latest 2>/dev/null || {
    echo "⚠️  Application backup not found, using emergency rollback"
    ./emergency_rollback.sh
}

# Start services
docker compose up -d eqmd

# Verify system
echo "🔍 Verifying rollback..."
sleep 10
if curl -f -s http://localhost:8778/health/ >/dev/null; then
    echo "✅ Complete rollback successful"
else
    echo "❌ Rollback verification failed"
    exit 1
fi

echo "🎉 Complete system rollback to $BACKUP_TIMESTAMP completed"
```

## Rollback Verification

### Health Checks

```bash
#!/bin/bash
# verify_rollback.sh

echo "🔍 Verifying rollback health..."

# Application health
if curl -f -s http://localhost:8778/health/ >/dev/null; then
    echo "✅ Application health check passed"
else
    echo "❌ Application health check failed"
    exit 1
fi

# Database connectivity
if docker exec eqmd-eqmd-1 python manage.py check --database default >/dev/null 2>&1; then
    echo "✅ Database connectivity verified"
else
    echo "❌ Database connectivity failed"
    exit 1
fi

# Static files availability
VOLUME_PATH="/var/lib/docker/volumes/eqmd_static_files/_data"
if [ -f "$VOLUME_PATH/manifest.json" ] && [ -f "$VOLUME_PATH/sw.js" ]; then
    echo "✅ Static files verified"
else
    echo "⚠️  Some static files missing"
fi

# Container status
if docker compose ps | grep -q "Up"; then
    echo "✅ Container running properly"
else
    echo "❌ Container not running"
    exit 1
fi

echo "🎉 Rollback verification completed successfully"
```

## Rollback Checklist

### Before Rollback

- [ ] **Identify the issue** - Document what went wrong
- [ ] **Check recent backups** - Verify backup availability
- [ ] **Notify stakeholders** - Inform about planned rollback
- [ ] **Prepare monitoring** - Set up monitoring for rollback verification

### During Rollback

- [ ] **Stop current services** - Cleanly shut down current deployment
- [ ] **Restore from backup** - Apply appropriate rollback method
- [ ] **Verify restoration** - Run health checks and verification
- [ ] **Monitor logs** - Watch for errors during rollback

### After Rollback

- [ ] **Confirm functionality** - Test critical application features
- [ ] **Update monitoring** - Ensure monitoring reflects rollback
- [ ] **Document incident** - Record what happened and why
- [ ] **Plan fix** - Prepare proper fix for next deployment

## Prevention Strategies

### Automated Testing

```bash
# Add to upgrade.sh before deployment
echo "🧪 Running pre-deployment tests..."
docker run --rm $EQMD_IMAGE python manage.py check --deploy

# Add smoke tests after deployment
echo "🧪 Running post-deployment tests..."
curl -f http://localhost:8778/health/
# Add more application-specific tests
```

### Gradual Rollout

```bash
# Blue-green deployment approach
# Keep old version running while testing new version

# Deploy to alternate port first
docker compose -f docker-compose.staging.yml up -d eqmd

# Test on staging port
curl -f http://localhost:8779/health/

# Switch traffic only after verification
docker compose up -d eqmd
```

### Monitoring Integration

```bash
# Add alerting for failed deployments
# Monitor key metrics after deployment
# Set up automated rollback triggers for critical failures
```

## Emergency Contacts

In case of deployment emergencies:

1. **Check application logs**: `docker compose logs -f eqmd`
2. **Check system health**: `./verify_rollback.sh`
3. **Use emergency rollback**: `./emergency_rollback.sh`
4. **Contact system administrator** if rollback fails
5. **Document all actions** taken during emergency

This comprehensive rollback system ensures rapid recovery from deployment issues while maintaining data integrity and system stability.
