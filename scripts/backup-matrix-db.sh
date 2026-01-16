#!/bin/bash
# Matrix database backup script (pg_dump)

set -e

BACKUP_DIR="backups/$(date +%Y%m%d)"
BACKUP_FILE="matrix_db-$(date +%Y%m%d_%H%M%S).sql.gz"

echo "Creating backup directory: $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"

echo "Backing up Matrix database..."
docker compose exec -T postgres sh -lc 'pg_dump -U "$POSTGRES_USER" matrix_db' | gzip > "$BACKUP_DIR/$BACKUP_FILE"

echo "Matrix database backed up to $BACKUP_DIR/$BACKUP_FILE"
echo "Backup size: $(ls -lh "$BACKUP_DIR/$BACKUP_FILE" | awk '{print $5}')"
