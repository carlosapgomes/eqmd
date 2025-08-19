#!/bin/bash
# EquipeMed Media Files Backup Script
# Backs up the media files volume to compressed archive

set -e

BACKUP_DIR="backups/$(date +%Y%m%d)"
BACKUP_FILE="media-$(date +%Y%m%d_%H%M%S).tar.gz"

echo "Creating backup directory: $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"

echo "Backing up media files volume..."
docker run --rm \
  -v eqmd_media_files:/data \
  -v $(pwd)/$BACKUP_DIR:/backup \
  alpine tar czf /backup/$BACKUP_FILE -C /data .

echo "✓ Media files backed up to $BACKUP_DIR/$BACKUP_FILE"
echo "Backup size: $(ls -lh $BACKUP_DIR/$BACKUP_FILE | awk '{print $5}')"