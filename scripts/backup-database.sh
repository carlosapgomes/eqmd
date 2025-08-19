#!/bin/bash
# EquipeMed Database Backup Script
# Backs up the database volume to compressed archive

set -e

BACKUP_DIR="backups/$(date +%Y%m%d)"
BACKUP_FILE="database-$(date +%Y%m%d_%H%M%S).tar.gz"

echo "Creating backup directory: $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"

echo "Backing up database volume..."
docker run --rm \
  -v eqmd_database:/data \
  -v $(pwd)/$BACKUP_DIR:/backup \
  alpine tar czf /backup/$BACKUP_FILE -C /data .

echo "✓ Database backed up to $BACKUP_DIR/$BACKUP_FILE"
echo "Backup size: $(ls -lh $BACKUP_DIR/$BACKUP_FILE | awk '{print $5}')"