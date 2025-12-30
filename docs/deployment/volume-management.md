# Docker Volume Management

## Overview

EquipeMed uses Docker named volumes to securely store persistent data with improved isolation, security, and reliability compared to host-mounted volumes.

## Volume Structure

### Named Volumes

- **`eqmd_database`**: SQLite database files
- **`eqmd_media_files`**: Patient photos, videos, and medical images
- **`eqmd_static_files`**: Compiled CSS, JavaScript, and static assets

### Security Benefits

- **Isolation**: Medical data protected from host filesystem access
- **Permissions**: No host/container user conflicts
- **Compliance**: Better audit trail and access control
- **Reliability**: Consistent behavior across environments

## Volume Operations

### Information and Status

```bash
# Check volume status and sizes
./scripts/volume-info.sh
```

### Backup Operations

```bash
# Backup database
./scripts/backup-database.sh

# Backup media files  
./scripts/backup-media.sh
```

Backups are stored in `backups/YYYYMMDD/` with timestamps.

### Restore Operations

```bash
# Restore database from backup
./scripts/restore-database.sh backups/20250819/database-20250819_143052.tar.gz

# Restore media files from backup
./scripts/restore-media.sh backups/20250819/media-20250819_143052.tar.gz
```

⚠️ **Warning**: Restore operations replace ALL existing data and require confirmation.

### Volume Cleanup

```bash
# Remove all volumes (DESTRUCTIVE)
./scripts/cleanup-volumes.sh
```

⚠️ **Danger**: This permanently deletes all data and requires explicit confirmation.

## Production Deployment

### Initial Setup

1. **Deploy configuration**:

   ```bash
   docker-compose up -d
   ```

2. **Initialize database**:

   ```bash
   docker-compose exec eqmd uv run python manage.py migrate
   docker-compose exec eqmd uv run python manage.py createsuperuser
   ```

3. **Verify volumes**:

   ```bash
   ./scripts/volume-info.sh
   ```

### Maintenance Schedule

#### Daily (Automated via cron)

```bash
# Add to crontab
0 2 * * * cd /path/to/eqmd && ./scripts/backup-database.sh
0 3 * * * cd /path/to/eqmd && ./scripts/backup-media.sh
```

#### Weekly

- Volume health checks with `./scripts/volume-info.sh`
- Backup integrity verification
- Disk space monitoring

#### Monthly

- Test restore procedures on development copy
- Review backup retention policies
- Update backup rotation

## Backup Strategy

### Retention Policy

- **Daily backups**: Keep for 30 days
- **Weekly backups**: Keep for 12 weeks
- **Monthly backups**: Keep for 12 months

### Storage Recommendations

- Store backups on separate physical storage
- Consider off-site backup storage for compliance
- Encrypt backup archives for medical data security

### Example Backup Rotation

```bash
#!/bin/bash
# backup-rotation.sh
find backups/ -name "database-*.tar.gz" -mtime +30 -delete
find backups/ -name "media-*.tar.gz" -mtime +30 -delete
```

## Troubleshooting

### Volume Issues

If volumes are corrupted or inaccessible:

1. **Check volume status**:

   ```bash
   docker volume ls
   docker volume inspect eqmd_database
   ```

2. **Recreate volumes if needed**:

   ```bash
   ./scripts/cleanup-volumes.sh
   docker-compose up -d
   ```

3. **Restore from backup**:

   ```bash
   ./scripts/restore-database.sh <backup-file>
   ./scripts/restore-media.sh <backup-file>
   ```

### Permission Issues

If containers can't access volumes:

1. **Check volume mounts**:

   ```bash
   docker-compose logs eqmd
   ```

2. **Verify volume configuration**:

   ```bash
   docker-compose config
   ```

3. **Restart services**:

   ```bash
   docker-compose restart
   ```

### Disk Space Issues

Monitor volume sizes regularly:

```bash
./scripts/volume-info.sh
df -h /var/lib/docker/volumes/
```

## Migration from Host Volumes

If migrating from host-mounted volumes:

1. **Backup existing data**:

   ```bash
   cp db.sqlite3 migration-backup/
   tar czf migration-backup/media.tar.gz media/
   ```

2. **Update docker-compose.yml** to use named volumes

3. **Migrate data**:

   ```bash
   # Create volumes
   docker volume create eqmd_database
   docker volume create eqmd_media_files
   
   # Copy data to volumes
   docker run --rm -v ./db.sqlite3:/source \
     -v eqmd_database:/target \
     alpine cp /source /target/
     
   docker run --rm -v ./media:/source \
     -v eqmd_media_files:/target \
     alpine sh -c "cp -r /source/* /target/"
   ```

4. **Test and verify**:

   ```bash
   docker-compose up -d
   ./scripts/volume-info.sh
   ```

## Security Considerations

### Access Control

- Volumes are only accessible to authorized containers
- No direct host filesystem access
- Docker daemon manages all volume operations

### Audit Trail

- All volume operations logged via Docker
- Backup operations logged with timestamps
- Restore operations require explicit confirmation

### Encryption

- Consider Docker volume encryption for sensitive environments
- Encrypt backup archives before off-site storage
- Use encrypted transport for backup transfers

## Monitoring

### Health Checks

```bash
# Check volume accessibility
docker run --rm -v eqmd_database:/test alpine ls -la /test

# Check volume sizes
./scripts/volume-info.sh

# Check container logs for volume issues
docker-compose logs eqmd | grep -i volume
```

### Alerts

Configure monitoring for:

- Volume disk space usage (> 80%)
- Failed backup operations
- Volume mount failures
- Abnormal volume growth rates

## Recovery Procedures

### Complete System Recovery

1. **Install Docker and docker-compose**
2. **Clone repository and configure environment**
3. **Create volumes**: `docker volume create eqmd_database eqmd_media_files eqmd_static_files`
4. **Restore from backups**: Use restore scripts
5. **Start services**: `docker-compose up -d`
6. **Verify functionality**: Run health checks

### Partial Recovery

- **Database only**: Use `./scripts/restore-database.sh`
- **Media files only**: Use `./scripts/restore-media.sh`
- **Fresh start**: Use `./scripts/cleanup-volumes.sh` then redeploy
