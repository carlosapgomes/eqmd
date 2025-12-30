# Docker Volumes Implementation Plan

## Overview

Convert EquipeMed deployment from host-mounted volumes to Docker named volumes for improved security, reliability, and compliance with medical data standards.

## Current State Analysis

### Current docker-compose.yml Configuration

```yaml
services:
  eqmd:
    volumes:
      - ./media:/app/media # Host-mounted
      - ./db.sqlite3:/app/database # Host-mounted
      - static_files:/app/staticfiles # Named volume ✓
```

### Issues with Current Approach

- **Security**: Medical images accessible from host filesystem
- **Permissions**: eqmd user vs host user conflicts
- **Reliability**: Files can be accidentally deleted/modified
- **Compliance**: Less audit control over medical data

## Target Architecture

### New docker-compose.yml Configuration

```yaml
services:
  eqmd:
    volumes:
      - media_files:/app/media
      - database:/app/database
      - static_files:/app/staticfiles

volumes:
  database:
    driver: local
  media_files:
    driver: local
  static_files:
    driver: local
```

## Implementation Steps

### Phase 1: Update docker-compose.yml (Greenfield)

1. **Stop current containers**

   ```bash
   docker-compose down
   ```

2. **Update docker-compose.yml** with new volume configuration

3. **Remove any existing volumes (test environment)**

   ```bash
   docker volume rm $(docker volume ls -q --filter name=eqmd) 2>/dev/null || true
   ```

### Phase 2: Initialize Fresh Volumes

1. **Create named volumes**

   ```bash
   docker volume create eqmd_database
   docker volume create eqmd_media_files
   docker volume create eqmd_static_files
   ```

2. **Start containers with clean volumes**

   ```bash
   docker-compose up -d
   ```

3. **Initialize database**

   ```bash
   docker-compose exec eqmd uv run python manage.py migrate
   docker-compose exec eqmd uv run python manage.py createsuperuser
   ```

### Phase 3: Create Backup/Restore Scripts

#### backup-database.sh

```bash
#!/bin/bash
BACKUP_DIR="backups/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

docker run --rm \
  -v eqmd_database:/data \
  -v $(pwd)/$BACKUP_DIR:/backup \
  alpine tar czf /backup/database-$(date +%Y%m%d_%H%M%S).tar.gz -C /data .

echo "Database backed up to $BACKUP_DIR/"
```

#### backup-media.sh

```bash
#!/bin/bash
BACKUP_DIR="backups/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

docker run --rm \
  -v eqmd_media_files:/data \
  -v $(pwd)/$BACKUP_DIR:/backup \
  alpine tar czf /backup/media-$(date +%Y%m%d_%H%M%S).tar.gz -C /data .

echo "Media files backed up to $BACKUP_DIR/"
```

#### restore-database.sh

```bash
#!/bin/bash
if [ -z "$1" ]; then
  echo "Usage: $0 <backup-file.tar.gz>"
  exit 1
fi

docker run --rm \
  -v eqmd_database:/data \
  -v $(pwd):/backup \
  alpine sh -c "rm -rf /data/* && tar xzf /backup/$1 -C /data"

echo "Database restored from $1"
```

#### restore-media.sh

```bash
#!/bin/bash
if [ -z "$1" ]; then
  echo "Usage: $0 <backup-file.tar.gz>"
  exit 1
fi

docker run --rm \
  -v eqmd_media_files:/data \
  -v $(pwd):/backup \
  alpine sh -c "rm -rf /data/* && tar xzf /backup/$1 -C /data"

echo "Media files restored from $1"
```

### Phase 4: Volume Management Tools

#### volume-info.sh

```bash
#!/bin/bash
echo "=== EQMD Docker Volumes Status ==="
echo
echo "Database Volume:"
docker volume inspect eqmd_database | jq '.[0].Mountpoint'
docker run --rm -v eqmd_database:/data alpine du -sh /data

echo
echo "Media Files Volume:"
docker volume inspect eqmd_media_files | jq '.[0].Mountpoint'
docker run --rm -v eqmd_media_files:/data alpine du -sh /data

echo
echo "Static Files Volume:"
docker volume inspect eqmd_static_files | jq '.[0].Mountpoint'
docker run --rm -v eqmd_static_files:/data alpine du -sh /data
```

#### cleanup-volumes.sh

```bash
#!/bin/bash
read -p "Are you sure you want to delete ALL EQMD volumes? (yes/no): " confirm
if [ "$confirm" = "yes" ]; then
  docker-compose down
  docker volume rm eqmd_database eqmd_media_files eqmd_static_files
  echo "All volumes deleted"
else
  echo "Cancelled"
fi
```

### Phase 5: Testing and Validation

1. **Start containers with new configuration**

   ```bash
   docker-compose up -d
   ```

2. **Verify data integrity**

   - Check database connectivity
   - Verify media files are accessible
   - Test file uploads
   - Verify static files serving

3. **Test backup/restore procedures**

   ```bash
   ./backup-database.sh
   ./backup-media.sh
   # Test restoration on development copy
   ```

## Security Benefits

### Before (Host-mounted)

- Medical images accessible from host filesystem
- Permission conflicts between host and container users
- Risk of accidental deletion/modification
- Platform-specific security issues

### After (Docker Volumes)

- Medical data isolated within Docker-managed volumes
- Consistent permissions across environments
- Protection from accidental host-level access
- Better audit trail through Docker layer

## Operational Benefits

### Backup Strategy

- **Automated**: Scripts for regular backups
- **Consistent**: Same procedure across all environments
- **Reliable**: Docker-managed volume consistency
- **Secure**: No direct host filesystem access required

### Monitoring

- Volume health checks via Docker API
- Disk usage monitoring per volume
- Backup verification procedures
- Restoration testing protocols

## Rollback Plan

If issues arise during implementation:

1. **Stop new containers**

   ```bash
   docker-compose down
   ```

2. **Restore old docker-compose.yml**

   ```bash
   git checkout HEAD~1 docker-compose.yml
   ```

3. **Remove problematic volumes**

   ```bash
   docker volume rm eqmd_database eqmd_media_files eqmd_static_files
   ```

4. **Restart with host-mounted configuration**

   ```bash
   docker-compose up -d
   ```

## Maintenance Schedule

### Daily

- Automated backups via cron job

### Weekly

- Volume health checks
- Backup integrity verification

### Monthly

- Test restore procedures
- Review volume usage trends
- Update backup retention policies

## Files to Create

1. `docker-compose.yml` (updated)
2. `scripts/backup-database.sh`
3. `scripts/backup-media.sh`
4. `scripts/restore-database.sh`
5. `scripts/restore-media.sh`
6. `scripts/volume-info.sh`
7. `scripts/cleanup-volumes.sh`
8. `docs/deployment/volume-management.md`

## Success Criteria

- [x] All containers start successfully with named volumes
- [x] Database operations work correctly
- [x] Media file uploads/downloads function
- [x] Static files serve properly
- [x] Backup scripts execute without errors
- [x] Restore procedures validated
- [x] No data loss during migration
- [x] Improved security posture confirmed
- [x] Documentation updated

## Timeline

- **Phase 1**: 15 minutes (configuration update)
- **Phase 2**: 15 minutes (volume initialization)  
- **Phase 3**: 2 hours (script creation + testing)
- **Phase 4**: 1 hour (management tools)
- **Phase 5**: 1 hour (testing + validation)

**Total Estimated Time**: 4-5 hours

## Risk Mitigation

- Clean volumes eliminate migration complexity
- Test implementation in isolated environment
- Have rollback plan ready (revert docker-compose.yml)
- Create comprehensive backup/restore procedures for production use
- Document all changes for audit trail
